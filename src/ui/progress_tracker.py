"""
Progress tracking system for epub2tts pipelines.

This module provides a thread-safe event-based progress tracking system
that allows multiple pipelines to emit progress events and subscribers
to receive real-time updates.
"""

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from typing import Dict, List, Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor


class EventType(Enum):
    """Types of progress events."""
    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"


class PipelineType(Enum):
    """Types of processing pipelines."""
    TTS = "tts"
    IMAGE = "image"
    EPUB = "epub"
    OVERALL = "overall"


@dataclass
class ProgressEvent:
    """
    Represents a progress event from a pipeline.

    Attributes:
        pipeline: The pipeline that generated this event
        event_type: Type of event (start, progress, complete, error, etc.)
        data: Event-specific data payload
        timestamp: When the event occurred
        event_id: Unique identifier for this event
    """
    pipeline: PipelineType
    event_type: EventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default="")

    def __post_init__(self):
        """Generate event ID if not provided."""
        if not self.event_id:
            self.event_id = f"{self.pipeline.value}_{self.event_type.value}_{int(self.timestamp * 1000)}"


@dataclass
class PipelineStats:
    """
    Current statistics for a pipeline.

    Attributes:
        total_items: Total number of items to process
        completed_items: Number of items completed
        current_item: Currently processing item
        start_time: When processing started
        last_update: Last update timestamp
        errors: Number of errors encountered
        warnings: Number of warnings
        custom_stats: Pipeline-specific statistics
    """
    total_items: int = 0
    completed_items: int = 0
    current_item: str = ""
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    errors: int = 0
    warnings: int = 0
    custom_stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return min(100.0, (self.completed_items / self.total_items) * 100.0)

    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time

    @property
    def items_per_second(self) -> float:
        """Calculate processing rate (items per second)."""
        elapsed = self.elapsed_time
        if elapsed == 0 or self.completed_items == 0:
            return 0.0
        return self.completed_items / elapsed

    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time to completion in seconds."""
        if self.total_items == 0 or self.completed_items == 0:
            return None

        remaining_items = self.total_items - self.completed_items
        if remaining_items <= 0:
            return 0.0

        rate = self.items_per_second
        if rate <= 0:
            return None

        return remaining_items / rate


class ProgressTracker:
    """
    Thread-safe progress tracking system.

    This class manages progress events from multiple pipelines and provides
    real-time statistics and notifications to subscribers.
    """

    def __init__(self):
        """Initialize the progress tracker."""
        self._events: Queue[ProgressEvent] = Queue()
        self._stats: Dict[PipelineType, PipelineStats] = {}
        self._subscribers: List[Callable[[ProgressEvent], None]] = []
        self._lock = threading.Lock()
        self._running = False
        self._event_processor_thread: Optional[threading.Thread] = None
        self._recent_events: Dict[PipelineType, List[ProgressEvent]] = {}
        self._max_recent_events = 10

        # Initialize stats for all pipeline types
        for pipeline_type in PipelineType:
            self._stats[pipeline_type] = PipelineStats()
            self._recent_events[pipeline_type] = []

    def start(self):
        """Start the progress tracker event processing."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._event_processor_thread = threading.Thread(
                target=self._process_events,
                daemon=True
            )
            self._event_processor_thread.start()

    def stop(self):
        """Stop the progress tracker event processing."""
        with self._lock:
            if not self._running:
                return

            self._running = False

        # Add a sentinel event to wake up the processor
        self.emit_event(ProgressEvent(
            pipeline=PipelineType.OVERALL,
            event_type=EventType.INFO,
            data={"action": "shutdown"}
        ))

        if self._event_processor_thread and self._event_processor_thread.is_alive():
            self._event_processor_thread.join(timeout=1.0)

    def emit_event(self, event: ProgressEvent):
        """
        Emit a progress event.

        Args:
            event: The progress event to emit
        """
        if not isinstance(event, ProgressEvent):
            raise TypeError("event must be a ProgressEvent instance")

        self._events.put(event)

    def subscribe(self, callback: Callable[[ProgressEvent], None]):
        """
        Subscribe to progress events.

        Args:
            callback: Function to call when events occur
        """
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[ProgressEvent], None]):
        """
        Unsubscribe from progress events.

        Args:
            callback: Function to remove from subscribers
        """
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def get_stats(self, pipeline: PipelineType) -> PipelineStats:
        """
        Get current statistics for a pipeline.

        Args:
            pipeline: The pipeline to get stats for

        Returns:
            Current pipeline statistics
        """
        with self._lock:
            # Return a copy to avoid external modification
            stats = self._stats[pipeline]
            return PipelineStats(
                total_items=stats.total_items,
                completed_items=stats.completed_items,
                current_item=stats.current_item,
                start_time=stats.start_time,
                last_update=stats.last_update,
                errors=stats.errors,
                warnings=stats.warnings,
                custom_stats=stats.custom_stats.copy()
            )

    def get_recent_events(self, pipeline: PipelineType, limit: int = 5) -> List[ProgressEvent]:
        """
        Get recent events for a pipeline.

        Args:
            pipeline: The pipeline to get events for
            limit: Maximum number of events to return

        Returns:
            List of recent events (most recent first)
        """
        with self._lock:
            events = self._recent_events[pipeline]
            return list(reversed(events[-limit:]))

    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics across all pipelines.

        Returns:
            Dictionary with overall progress information
        """
        with self._lock:
            total_items = 0
            completed_items = 0
            total_errors = 0
            total_warnings = 0
            earliest_start = float('inf')

            for pipeline_type in [PipelineType.TTS, PipelineType.IMAGE, PipelineType.EPUB]:
                stats = self._stats[pipeline_type]
                total_items += stats.total_items
                completed_items += stats.completed_items
                total_errors += stats.errors
                total_warnings += stats.warnings

                if stats.start_time < earliest_start:
                    earliest_start = stats.start_time

            progress_percentage = 0.0
            if total_items > 0:
                progress_percentage = (completed_items / total_items) * 100.0

            elapsed_time = 0.0
            if earliest_start != float('inf'):
                elapsed_time = time.time() - earliest_start

            return {
                'total_items': total_items,
                'completed_items': completed_items,
                'progress_percentage': progress_percentage,
                'elapsed_time': elapsed_time,
                'errors': total_errors,
                'warnings': total_warnings,
                'eta_seconds': self._calculate_overall_eta(),
                'active_pipelines': self._get_active_pipelines()
            }

    def _process_events(self):
        """Process events from the queue (runs in background thread)."""
        while self._running:
            try:
                # Wait for events with timeout to allow clean shutdown
                event = self._events.get(timeout=0.1)

                # Check for shutdown signal
                if (event.pipeline == PipelineType.OVERALL and
                    event.event_type == EventType.INFO and
                    event.data.get("action") == "shutdown"):
                    break

                # Update statistics
                self._update_stats(event)

                # Store recent events
                self._store_recent_event(event)

                # Notify subscribers
                self._notify_subscribers(event)

            except Empty:
                # Timeout occurred, continue checking if still running
                continue
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing progress event: {e}")

    def _update_stats(self, event: ProgressEvent):
        """Update pipeline statistics based on event."""
        with self._lock:
            stats = self._stats[event.pipeline]
            stats.last_update = event.timestamp

            if event.event_type == EventType.START:
                # Initialize or update total items
                if 'total_items' in event.data:
                    stats.total_items = event.data['total_items']
                if 'current_item' in event.data:
                    stats.current_item = event.data['current_item']

            elif event.event_type == EventType.PROGRESS:
                # Update progress information
                if 'completed_items' in event.data:
                    stats.completed_items = event.data['completed_items']
                if 'current_item' in event.data:
                    stats.current_item = event.data['current_item']
                if 'total_items' in event.data:
                    stats.total_items = event.data['total_items']

            elif event.event_type == EventType.COMPLETE:
                # Mark item as completed
                if 'current_item' in event.data:
                    stats.current_item = ""
                stats.completed_items += 1

            elif event.event_type == EventType.ERROR:
                stats.errors += 1

            elif event.event_type == EventType.WARNING:
                stats.warnings += 1

            # Update custom statistics
            if 'custom_stats' in event.data:
                stats.custom_stats.update(event.data['custom_stats'])

    def _store_recent_event(self, event: ProgressEvent):
        """Store event in recent events list."""
        with self._lock:
            recent = self._recent_events[event.pipeline]
            recent.append(event)

            # Keep only the most recent events
            if len(recent) > self._max_recent_events:
                recent.pop(0)

    def _notify_subscribers(self, event: ProgressEvent):
        """Notify all subscribers of the event."""
        with self._lock:
            subscribers = self._subscribers.copy()

        # Notify outside of lock to avoid deadlocks
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in progress event subscriber: {e}")

    def _calculate_overall_eta(self) -> Optional[float]:
        """Calculate overall ETA across all pipelines."""
        etas = []

        for pipeline_type in [PipelineType.TTS, PipelineType.IMAGE, PipelineType.EPUB]:
            stats = self._stats[pipeline_type]
            eta = stats.eta_seconds
            if eta is not None and eta > 0:
                etas.append(eta)

        if not etas:
            return None

        # Return the maximum ETA (conservative estimate)
        return max(etas)

    def _get_active_pipelines(self) -> List[str]:
        """Get list of currently active pipelines."""
        active = []

        for pipeline_type in [PipelineType.TTS, PipelineType.IMAGE, PipelineType.EPUB]:
            stats = self._stats[pipeline_type]
            if (stats.total_items > 0 and
                stats.completed_items < stats.total_items and
                stats.current_item):
                active.append(pipeline_type.value)

        return active


# Convenience functions for common event patterns

def create_start_event(pipeline: PipelineType, total_items: int, current_item: str = "", **kwargs) -> ProgressEvent:
    """Create a start event."""
    data = {
        'total_items': total_items,
        'current_item': current_item,
        **kwargs
    }
    return ProgressEvent(pipeline=pipeline, event_type=EventType.START, data=data)


def create_progress_event(pipeline: PipelineType, completed_items: int, current_item: str = "", **kwargs) -> ProgressEvent:
    """Create a progress event."""
    data = {
        'completed_items': completed_items,
        'current_item': current_item,
        **kwargs
    }
    return ProgressEvent(pipeline=pipeline, event_type=EventType.PROGRESS, data=data)


def create_complete_event(pipeline: PipelineType, current_item: str = "", **kwargs) -> ProgressEvent:
    """Create a completion event."""
    data = {
        'current_item': current_item,
        **kwargs
    }
    return ProgressEvent(pipeline=pipeline, event_type=EventType.COMPLETE, data=data)


def create_error_event(pipeline: PipelineType, error_message: str, current_item: str = "", **kwargs) -> ProgressEvent:
    """Create an error event."""
    data = {
        'error_message': error_message,
        'current_item': current_item,
        **kwargs
    }
    return ProgressEvent(pipeline=pipeline, event_type=EventType.ERROR, data=data)