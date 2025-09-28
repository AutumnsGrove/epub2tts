"""
User interface components for epub2tts.

This package provides terminal UI components including progress tracking
and real-time display systems for the epub2tts processing pipeline.
"""

from .progress_tracker import (
    ProgressTracker,
    ProgressEvent,
    PipelineStats,
    EventType,
    PipelineType,
    create_start_event,
    create_progress_event,
    create_complete_event,
    create_error_event,
)

__all__ = [
    "ProgressTracker",
    "ProgressEvent",
    "PipelineStats",
    "EventType",
    "PipelineType",
    "create_start_event",
    "create_progress_event",
    "create_complete_event",
    "create_error_event",
]