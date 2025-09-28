"""
Terminal UI Manager for epub2tts.

This module provides a sophisticated terminal UI with a fixed-height split-window
layout for real-time progress tracking of audio generation and image processing.
"""

import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TimeElapsedColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    from rich.console import Console
    from rich.align import Align
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .progress_tracker import ProgressTracker, ProgressEvent, PipelineType, EventType

import logging
logger = logging.getLogger(__name__)


@dataclass
class UIConfig:
    """UI configuration settings."""
    mode: str = "classic"  # "classic" or "split-window"
    window_height: int = 20
    update_frequency: float = 0.1  # seconds
    show_stats: bool = True
    show_progress_bars: bool = True
    show_recent_activity: bool = True
    recent_activity_lines: int = 3

    # Color scheme
    colors: Dict[str, str] = None

    def __post_init__(self):
        """Initialize default colors if not provided."""
        if self.colors is None:
            self.colors = {
                'progress_complete': 'green',
                'progress_incomplete': 'white',
                'error': 'red',
                'warning': 'yellow',
                'info': 'blue',
                'success': 'green',
                'processing': 'cyan'
            }


class TerminalUIManager:
    """
    Manages the split-window terminal UI with real-time progress tracking.

    This class provides a fixed-height display that shows progress for both
    TTS and image processing pipelines simultaneously without scrolling.
    """

    def __init__(self, config: UIConfig, progress_tracker: ProgressTracker):
        """
        Initialize Terminal UI Manager.

        Args:
            config: UI configuration
            progress_tracker: Progress tracking system
        """
        self.config = config
        self.tracker = progress_tracker
        self.console = Console()
        self.live_display: Optional[Live] = None
        self.is_running = False
        self.update_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # UI state
        self.tts_recent_events: List[ProgressEvent] = []
        self.image_recent_events: List[ProgressEvent] = []
        self.overall_start_time = time.time()

        # Check Rich availability
        if not RICH_AVAILABLE:
            logger.warning("Rich library not available. Terminal UI disabled.")
            return

        # Create layout
        self.layout = self._create_layout()

        # Subscribe to progress events
        self.tracker.subscribe(self._on_progress_event)

        logger.info("Terminal UI Manager initialized")

    def start(self) -> bool:
        """
        Start the live UI display.

        Returns:
            True if started successfully, False otherwise
        """
        if not RICH_AVAILABLE:
            logger.warning("Cannot start UI: Rich library not available")
            return False

        if self.is_running:
            logger.warning("UI already running")
            return True

        try:
            with self._lock:
                self.is_running = True

                # Start progress tracker if not already running
                self.tracker.start()

                # Create live display
                self.live_display = Live(
                    self.layout,
                    console=self.console,
                    refresh_per_second=1.0 / self.config.update_frequency,
                    auto_refresh=True
                )

                # Start live display
                self.live_display.start()

                # Start update thread
                self.update_thread = threading.Thread(
                    target=self._update_loop,
                    daemon=True
                )
                self.update_thread.start()

            logger.info("Terminal UI started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start Terminal UI: {e}")
            self.is_running = False
            return False

    def stop(self) -> None:
        """Stop the UI and restore terminal."""
        if not self.is_running:
            return

        try:
            with self._lock:
                self.is_running = False

            # Wait for update thread to finish
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=1.0)

            # Stop live display
            if self.live_display:
                self.live_display.stop()
                self.live_display = None

            # Unsubscribe from events
            self.tracker.unsubscribe(self._on_progress_event)

            logger.info("Terminal UI stopped")

        except Exception as e:
            logger.error(f"Error stopping Terminal UI: {e}")

    def _create_layout(self) -> Layout:
        """Create the split-window layout."""
        # Main layout with fixed height
        layout = Layout()

        # Split into main content and status bar
        layout.split_column(
            Layout(name="main", size=self.config.window_height - 2),
            Layout(name="status", size=2)
        )

        # Split main area into two columns for TTS and Image processing
        layout["main"].split_row(
            Layout(name="tts_panel"),
            Layout(name="image_panel")
        )

        # Initialize panels
        layout["tts_panel"].update(self._create_tts_panel())
        layout["image_panel"].update(self._create_image_panel())
        layout["status"].update(self._create_status_panel())

        return layout

    def _create_tts_panel(self) -> Panel:
        """Create the TTS progress panel."""
        # Get TTS statistics
        tts_stats = self.tracker.get_stats(PipelineType.TTS)

        # Create content table
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")

        # Progress information
        if tts_stats.total_items > 0:
            progress_text = f"{tts_stats.completed_items}/{tts_stats.total_items}"
            percentage = tts_stats.progress_percentage

            # Create progress bar
            progress_bar = self._create_progress_bar(percentage)

            table.add_row("Progress:", f"{progress_text} ({percentage:.1f}%)")
            table.add_row("", progress_bar)

            # Current item
            if tts_stats.current_item:
                current_item = tts_stats.current_item
                if len(current_item) > 30:
                    current_item = current_item[:27] + "..."
                table.add_row("Current:", current_item)

            # Performance metrics
            elapsed = tts_stats.elapsed_time
            if elapsed > 0:
                table.add_row("Time:", self._format_duration(elapsed))

                rate = tts_stats.items_per_second
                if rate > 0:
                    table.add_row("Rate:", f"{rate:.2f} items/sec")

                eta = tts_stats.eta_seconds
                if eta:
                    table.add_row("ETA:", self._format_duration(eta))

            # Error counts
            if tts_stats.errors > 0:
                table.add_row("Errors:", f"[red]{tts_stats.errors}[/red]")
            if tts_stats.warnings > 0:
                table.add_row("Warnings:", f"[yellow]{tts_stats.warnings}[/yellow]")

        else:
            table.add_row("Status:", "[dim]Waiting to start...[/dim]")

        # Recent activity
        if self.config.show_recent_activity:
            table.add_row("", "")  # Spacer
            table.add_row("[bold]Recent Activity:[/bold]", "")

            recent_events = self.tracker.get_recent_events(
                PipelineType.TTS,
                self.config.recent_activity_lines
            )

            for event in recent_events:
                activity_text = self._format_event_for_display(event)
                if activity_text:
                    table.add_row("", activity_text)

        return Panel(
            table,
            title="[bold cyan]Audio Generation[/bold cyan]",
            border_style="cyan",
            height=self.config.window_height // 2 - 1
        )

    def _create_image_panel(self) -> Panel:
        """Create the Image processing panel."""
        # Get Image statistics
        image_stats = self.tracker.get_stats(PipelineType.IMAGE)

        # Create content table
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")

        # Progress information
        if image_stats.total_items > 0:
            progress_text = f"{image_stats.completed_items}/{image_stats.total_items}"
            percentage = image_stats.progress_percentage

            # Create progress bar
            progress_bar = self._create_progress_bar(percentage)

            table.add_row("Progress:", f"{progress_text} ({percentage:.1f}%)")
            table.add_row("", progress_bar)

            # Current item
            if image_stats.current_item:
                current_item = image_stats.current_item
                if len(current_item) > 30:
                    current_item = current_item[:27] + "..."
                table.add_row("Current:", current_item)

            # Performance metrics
            elapsed = image_stats.elapsed_time
            if elapsed > 0:
                table.add_row("Time:", self._format_duration(elapsed))

                rate = image_stats.items_per_second
                if rate > 0:
                    table.add_row("Rate:", f"{rate:.2f} img/sec")

                eta = image_stats.eta_seconds
                if eta:
                    table.add_row("ETA:", self._format_duration(eta))

            # Custom stats (from image pipeline)
            custom_stats = image_stats.custom_stats
            if 'cache_hits' in custom_stats:
                table.add_row("Cache Hits:", str(custom_stats['cache_hits']))

            # Error counts
            if image_stats.errors > 0:
                table.add_row("Errors:", f"[red]{image_stats.errors}[/red]")
            if image_stats.warnings > 0:
                table.add_row("Warnings:", f"[yellow]{image_stats.warnings}[/yellow]")

        else:
            table.add_row("Status:", "[dim]Waiting to start...[/dim]")

        # Recent activity
        if self.config.show_recent_activity:
            table.add_row("", "")  # Spacer
            table.add_row("[bold]Recent Activity:[/bold]", "")

            recent_events = self.tracker.get_recent_events(
                PipelineType.IMAGE,
                self.config.recent_activity_lines
            )

            for event in recent_events:
                activity_text = self._format_event_for_display(event)
                if activity_text:
                    table.add_row("", activity_text)

        return Panel(
            table,
            title="[bold magenta]Image Processing[/bold magenta]",
            border_style="magenta",
            height=self.config.window_height // 2 - 1
        )

    def _create_status_panel(self) -> Panel:
        """Create the overall status panel."""
        overall_stats = self.tracker.get_overall_stats()

        # Create status content
        content_parts = []

        # Overall progress
        if overall_stats['total_items'] > 0:
            percentage = overall_stats['progress_percentage']
            progress_bar = self._create_progress_bar(percentage, width=30)
            progress_text = f"Overall Progress: {progress_bar} {percentage:.1f}%"
            content_parts.append(progress_text)

            # ETA
            eta = overall_stats.get('eta_seconds')
            if eta:
                eta_text = f"ETA: {self._format_duration(eta)}"
                content_parts.append(eta_text)
        else:
            content_parts.append("Overall Progress: [dim]Initializing...[/dim]")

        # Active pipelines
        active_pipelines = overall_stats.get('active_pipelines', [])
        if active_pipelines:
            pipeline_text = f"Active: {', '.join(active_pipelines)}"
            content_parts.append(pipeline_text)

        # Errors/Warnings summary
        total_errors = overall_stats.get('errors', 0)
        total_warnings = overall_stats.get('warnings', 0)
        if total_errors > 0 or total_warnings > 0:
            status_parts = []
            if total_errors > 0:
                status_parts.append(f"[red]Errors: {total_errors}[/red]")
            if total_warnings > 0:
                status_parts.append(f"[yellow]Warnings: {total_warnings}[/yellow]")
            content_parts.append(" | ".join(status_parts))

        content = " | ".join(content_parts)

        return Panel(
            Align.center(content),
            style="bold",
            height=2
        )

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a text-based progress bar."""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)

        # Color the bar based on progress
        if percentage >= 100:
            color = self.config.colors['progress_complete']
        elif percentage >= 75:
            color = 'yellow'
        else:
            color = self.config.colors['progress_incomplete']

        return f"[{color}]{bar}[/{color}]"

    def _format_event_for_display(self, event: ProgressEvent) -> str:
        """Format a progress event for display in recent activity."""
        timestamp = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")

        if event.event_type == EventType.START:
            item = event.data.get('current_item', 'item')
            if len(item) > 20:
                item = item[:17] + "..."
            return f"[dim]{timestamp}[/dim] [cyan]⚡[/cyan] Started {item}"

        elif event.event_type == EventType.COMPLETE:
            item = event.data.get('current_item', 'item')
            if len(item) > 20:
                item = item[:17] + "..."
            return f"[dim]{timestamp}[/dim] [green]✓[/green] Completed {item}"

        elif event.event_type == EventType.ERROR:
            error_msg = event.data.get('error_message', 'Unknown error')[:20]
            return f"[dim]{timestamp}[/dim] [red]✗[/red] Error: {error_msg}"

        elif event.event_type == EventType.WARNING:
            warning_msg = event.data.get('warning_message', 'Warning')[:20]
            return f"[dim]{timestamp}[/dim] [yellow]⚠[/yellow] {warning_msg}"

        elif event.event_type == EventType.PROGRESS:
            completed = event.data.get('completed_items', 0)
            total = event.data.get('total_items', 0)
            if total > 0:
                return f"[dim]{timestamp}[/dim] [blue]→[/blue] Progress: {completed}/{total}"

        return ""

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _on_progress_event(self, event: ProgressEvent) -> None:
        """Handle progress events from the tracker."""
        # Events are automatically handled by the tracker
        # UI updates are driven by the update loop
        pass

    def _update_loop(self) -> None:
        """Main update loop for the UI (runs in background thread)."""
        while self.is_running:
            try:
                if self.live_display and self.layout:
                    # Update all panels
                    self.layout["tts_panel"].update(self._create_tts_panel())
                    self.layout["image_panel"].update(self._create_image_panel())
                    self.layout["status"].update(self._create_status_panel())

                # Sleep until next update
                time.sleep(self.config.update_frequency)

            except Exception as e:
                logger.error(f"Error in UI update loop: {e}")
                time.sleep(1.0)  # Longer sleep on error

    def is_available(self) -> bool:
        """Check if the terminal UI is available."""
        return RICH_AVAILABLE

    def get_terminal_size(self) -> tuple:
        """Get current terminal size."""
        if RICH_AVAILABLE:
            return self.console.size
        return (80, 24)  # Default fallback


class ClassicUIManager:
    """
    Classic UI manager that provides traditional logging output.

    This is used as a fallback when Rich is not available or when
    classic mode is specifically requested.
    """

    def __init__(self, progress_tracker: ProgressTracker):
        """Initialize classic UI manager."""
        self.tracker = progress_tracker
        self.last_progress_update = {}

        # Subscribe to progress events for logging
        self.tracker.subscribe(self._on_progress_event)

        logger.info("Classic UI Manager initialized")

    def start(self) -> bool:
        """Start classic UI (just logging)."""
        self.tracker.start()
        logger.info("Classic UI started - using standard logging output")
        return True

    def stop(self) -> None:
        """Stop classic UI."""
        self.tracker.unsubscribe(self._on_progress_event)
        logger.info("Classic UI stopped")

    def _on_progress_event(self, event: ProgressEvent) -> None:
        """Handle progress events with logging."""
        pipeline = event.pipeline.value

        if event.event_type == EventType.START:
            total = event.data.get('total_items', 0)
            current = event.data.get('current_item', '')
            logger.info(f"[{pipeline.upper()}] Starting: {current} (total: {total})")

        elif event.event_type == EventType.PROGRESS:
            completed = event.data.get('completed_items', 0)
            total = event.data.get('total_items', 0)
            current = event.data.get('current_item', '')

            # Throttle progress updates to avoid spam
            last_update = self.last_progress_update.get(pipeline, 0)
            if time.time() - last_update > 5.0:  # Update every 5 seconds
                if total > 0:
                    percentage = (completed / total) * 100
                    logger.info(f"[{pipeline.upper()}] Progress: {completed}/{total} ({percentage:.1f}%) - {current}")
                    self.last_progress_update[pipeline] = time.time()

        elif event.event_type == EventType.COMPLETE:
            current = event.data.get('current_item', '')
            logger.info(f"[{pipeline.upper()}] Completed: {current}")

        elif event.event_type == EventType.ERROR:
            error_msg = event.data.get('error_message', 'Unknown error')
            current = event.data.get('current_item', '')
            logger.error(f"[{pipeline.upper()}] Error processing {current}: {error_msg}")

        elif event.event_type == EventType.WARNING:
            warning_msg = event.data.get('warning_message', 'Warning')
            logger.warning(f"[{pipeline.upper()}] Warning: {warning_msg}")

    def is_available(self) -> bool:
        """Classic UI is always available."""
        return True


def create_ui_manager(config: UIConfig, progress_tracker: ProgressTracker):
    """
    Factory function to create appropriate UI manager.

    Args:
        config: UI configuration
        progress_tracker: Progress tracking system

    Returns:
        UI manager instance (Terminal or Classic)
    """
    if config.mode == "split-window" and RICH_AVAILABLE:
        return TerminalUIManager(config, progress_tracker)
    else:
        if config.mode == "split-window" and not RICH_AVAILABLE:
            logger.warning("Split-window mode requested but Rich not available. Using classic mode.")
        return ClassicUIManager(progress_tracker)