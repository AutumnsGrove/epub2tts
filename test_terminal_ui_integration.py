"""
Integration tests for the Terminal UI system.

This test suite verifies that all UI components work together properly,
including ProgressTracker, UI managers, and the factory function.
"""

import pytest
import time
import sys
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from queue import Queue

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import modules to test
try:
    from ui import (
        create_ui_manager,
        ProgressTracker,
        ProgressEvent,
        PipelineType,
        EventType,
        UIConfig,
        TerminalUIManager,
        create_start_event,
        create_progress_event,
        create_complete_event,
        create_error_event,
    )
    UI_IMPORTS_AVAILABLE = True
except ImportError as e:
    UI_IMPORTS_AVAILABLE = False
    UI_IMPORT_ERROR = str(e)


class TestUIImports:
    """Test that UI components can be imported correctly."""

    def test_ui_imports(self):
        """Test that UI components can be imported correctly."""
        assert UI_IMPORTS_AVAILABLE, f"UI imports failed: {UI_IMPORT_ERROR if not UI_IMPORTS_AVAILABLE else ''}"

        # Verify all required components are available
        assert ProgressTracker is not None
        assert ProgressEvent is not None
        assert PipelineType is not None
        assert EventType is not None
        assert UIConfig is not None
        assert create_ui_manager is not None

        # Verify convenience functions are available
        assert create_start_event is not None
        assert create_progress_event is not None
        assert create_complete_event is not None
        assert create_error_event is not None


class TestProgressTracker:
    """Test ProgressTracker functionality."""

    def test_progress_tracker_creation(self):
        """Test ProgressTracker can be created and emit events."""
        tracker = ProgressTracker()
        assert tracker is not None
        assert not tracker._running
        assert len(tracker._subscribers) == 0

        # Verify initial stats are created for all pipeline types
        for pipeline_type in PipelineType:
            stats = tracker.get_stats(pipeline_type)
            assert stats.total_items == 0
            assert stats.completed_items == 0
            assert stats.errors == 0
            assert stats.warnings == 0

    def test_progress_tracker_event_emission(self):
        """Test that ProgressTracker can emit and process events."""
        tracker = ProgressTracker()
        events_received = []

        def event_callback(event):
            events_received.append(event)

        # Subscribe to events
        tracker.subscribe(event_callback)
        assert len(tracker._subscribers) == 1

        # Start tracker
        tracker.start()
        assert tracker._running

        try:
            # Emit test events
            start_event = create_start_event(PipelineType.TTS, 5, "test_item")
            progress_event = create_progress_event(PipelineType.TTS, 2, "current_item")
            complete_event = create_complete_event(PipelineType.TTS, "completed_item")
            error_event = create_error_event(PipelineType.TTS, "test error", "error_item")

            tracker.emit_event(start_event)
            tracker.emit_event(progress_event)
            tracker.emit_event(complete_event)
            tracker.emit_event(error_event)

            # Give time for events to be processed
            time.sleep(0.2)

            # Verify events were received
            assert len(events_received) >= 4

            # Verify stats were updated
            stats = tracker.get_stats(PipelineType.TTS)
            assert stats.total_items == 5
            assert stats.completed_items == 3  # 2 from progress + 1 from complete
            assert stats.errors == 1

        finally:
            tracker.stop()
            assert not tracker._running

    def test_progress_tracker_lifecycle(self):
        """Test ProgressTracker start/stop lifecycle."""
        tracker = ProgressTracker()

        # Initial state
        assert not tracker._running
        assert tracker._event_processor_thread is None

        # Start
        tracker.start()
        assert tracker._running
        assert tracker._event_processor_thread is not None
        assert tracker._event_processor_thread.is_alive()

        # Multiple starts should be safe
        tracker.start()
        assert tracker._running

        # Stop
        tracker.stop()
        assert not tracker._running

        # Multiple stops should be safe
        tracker.stop()
        assert not tracker._running


class TestUIManagerCreation:
    """Test UI manager creation and configuration."""

    def test_create_ui_manager_classic(self):
        """Test UI manager creation in classic mode."""
        tracker = ProgressTracker()
        config = UIConfig(mode="classic")

        ui_manager = create_ui_manager(config, tracker)
        assert ui_manager is not None
        assert ui_manager.is_available()

        # Should be ClassicUIManager regardless of Rich availability
        from ui.terminal_ui import ClassicUIManager
        assert isinstance(ui_manager, ClassicUIManager)

    @patch('ui.terminal_ui.RICH_AVAILABLE', True)
    def test_create_ui_manager_split_window_with_rich(self):
        """Test UI manager creation in split-window mode with Rich available."""
        tracker = ProgressTracker()
        config = UIConfig(mode="split-window")

        ui_manager = create_ui_manager(config, tracker)
        assert ui_manager is not None
        assert ui_manager.is_available()

        # Should be TerminalUIManager when Rich is available
        assert isinstance(ui_manager, TerminalUIManager)

    @patch('ui.terminal_ui.RICH_AVAILABLE', False)
    def test_create_ui_manager_split_window_without_rich(self):
        """Test UI manager creation in split-window mode without Rich."""
        tracker = ProgressTracker()
        config = UIConfig(mode="split-window")

        ui_manager = create_ui_manager(config, tracker)
        assert ui_manager is not None
        assert ui_manager.is_available()

        # Should fall back to ClassicUIManager when Rich is not available
        from ui.terminal_ui import ClassicUIManager
        assert isinstance(ui_manager, ClassicUIManager)


class TestRichGracefulDegradation:
    """Test UI manager graceful handling of Rich library availability/unavailability."""

    @patch('ui.terminal_ui.RICH_AVAILABLE', False)
    def test_terminal_ui_manager_without_rich(self):
        """Test TerminalUIManager graceful degradation without Rich."""
        tracker = ProgressTracker()
        config = UIConfig(mode="split-window")

        # Create TerminalUIManager directly (bypassing factory)
        with patch('ui.terminal_ui.logger') as mock_logger:
            ui_manager = TerminalUIManager(config, tracker)

            # Should log warning about Rich not being available
            mock_logger.warning.assert_called_with("Rich library not available. Terminal UI disabled.")

            # Should not be able to start
            result = ui_manager.start()
            assert result is False
            assert not ui_manager.is_running

            mock_logger.warning.assert_called_with("Cannot start UI: Rich library not available")

    @patch('ui.terminal_ui.RICH_AVAILABLE', True)
    @patch('ui.terminal_ui.Live')
    @patch('ui.terminal_ui.Console')
    def test_terminal_ui_manager_with_rich_mocked(self, mock_console, mock_live):
        """Test TerminalUIManager functionality with mocked Rich components."""
        tracker = ProgressTracker()
        config = UIConfig(mode="split-window", update_frequency=0.01)

        # Mock Rich components
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        ui_manager = TerminalUIManager(config, tracker)
        assert ui_manager.is_available()

        # Start UI
        result = ui_manager.start()
        assert result is True
        assert ui_manager.is_running

        # Verify Rich components were used
        mock_live.assert_called_once()
        mock_live_instance.start.assert_called_once()

        # Stop UI
        ui_manager.stop()
        assert not ui_manager.is_running
        mock_live_instance.stop.assert_called_once()


class TestProgressEventFlow:
    """Test that progress events flow correctly through the system."""

    def test_progress_event_flow_classic_ui(self):
        """Test progress event flow with ClassicUIManager."""
        tracker = ProgressTracker()
        config = UIConfig(mode="classic")
        ui_manager = create_ui_manager(config, tracker)

        # Capture log messages
        events_logged = []

        def capture_log_event(event):
            events_logged.append(event)

        # Mock the logging to capture events
        with patch('ui.terminal_ui.logger') as mock_logger:
            # Start both tracker and UI
            tracker.start()
            ui_manager.start()

            try:
                # Emit events
                start_event = create_start_event(PipelineType.TTS, 3, "audio_file.mp3")
                tracker.emit_event(start_event)

                progress_event = create_progress_event(PipelineType.TTS, 1, "processing.mp3")
                tracker.emit_event(progress_event)

                complete_event = create_complete_event(PipelineType.TTS, "completed.mp3")
                tracker.emit_event(complete_event)

                error_event = create_error_event(PipelineType.TTS, "Test error message", "failed.mp3")
                tracker.emit_event(error_event)

                # Give time for events to be processed
                time.sleep(0.2)

                # Verify logging calls were made
                assert mock_logger.info.call_count >= 2  # At least start and complete events
                assert mock_logger.error.call_count >= 1  # Error event

                # Verify stats were updated in tracker
                stats = tracker.get_stats(PipelineType.TTS)
                assert stats.total_items == 3
                assert stats.errors == 1

            finally:
                ui_manager.stop()
                tracker.stop()

    @patch('ui.terminal_ui.RICH_AVAILABLE', True)
    @patch('ui.terminal_ui.Live')
    @patch('ui.terminal_ui.Console')
    def test_progress_event_flow_terminal_ui(self, mock_console, mock_live):
        """Test progress event flow with TerminalUIManager."""
        tracker = ProgressTracker()
        config = UIConfig(mode="split-window", update_frequency=0.01)

        # Mock Rich components
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance
        mock_console_instance.size = (80, 24)

        ui_manager = create_ui_manager(config, tracker)

        # Start both tracker and UI
        tracker.start()
        ui_result = ui_manager.start()
        assert ui_result is True

        try:
            # Emit test events for multiple pipelines
            tts_start = create_start_event(PipelineType.TTS, 2, "audio1.mp3")
            image_start = create_start_event(PipelineType.IMAGE, 3, "image1.png")

            tracker.emit_event(tts_start)
            tracker.emit_event(image_start)

            # Progress events
            tts_progress = create_progress_event(PipelineType.TTS, 1, "audio2.mp3")
            image_progress = create_progress_event(PipelineType.IMAGE, 2, "image2.png")

            tracker.emit_event(tts_progress)
            tracker.emit_event(image_progress)

            # Give time for events to be processed and UI to update
            time.sleep(0.1)

            # Verify stats were updated for both pipelines
            tts_stats = tracker.get_stats(PipelineType.TTS)
            image_stats = tracker.get_stats(PipelineType.IMAGE)

            assert tts_stats.total_items == 2
            assert tts_stats.completed_items == 1
            assert image_stats.total_items == 3
            assert image_stats.completed_items == 2

            # Verify overall stats
            overall_stats = tracker.get_overall_stats()
            assert overall_stats['total_items'] == 5  # 2 TTS + 3 Image
            assert overall_stats['completed_items'] == 3  # 1 TTS + 2 Image

        finally:
            ui_manager.stop()
            tracker.stop()


class TestUIManagerLifecycle:
    """Test UI manager start/stop lifecycle."""

    def test_classic_ui_manager_lifecycle(self):
        """Test ClassicUIManager lifecycle operations."""
        tracker = ProgressTracker()
        config = UIConfig(mode="classic")
        ui_manager = create_ui_manager(config, tracker)

        # Initial state
        assert ui_manager.is_available()

        # Start
        result = ui_manager.start()
        assert result is True
        assert tracker._running

        # Multiple starts should be safe
        result = ui_manager.start()
        assert result is True

        # Stop
        ui_manager.stop()

        # Multiple stops should be safe
        ui_manager.stop()

    @patch('ui.terminal_ui.RICH_AVAILABLE', True)
    @patch('ui.terminal_ui.Live')
    @patch('ui.terminal_ui.Console')
    def test_terminal_ui_manager_lifecycle(self, mock_console, mock_live):
        """Test TerminalUIManager lifecycle operations."""
        tracker = ProgressTracker()
        config = UIConfig(mode="split-window")

        # Mock Rich components
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance
        mock_console_instance.size = (80, 24)

        ui_manager = create_ui_manager(config, tracker)

        # Initial state
        assert ui_manager.is_available()
        assert not ui_manager.is_running

        # Start
        result = ui_manager.start()
        assert result is True
        assert ui_manager.is_running
        mock_live_instance.start.assert_called_once()

        # Multiple starts should be safe
        result = ui_manager.start()
        assert result is True
        assert ui_manager.is_running

        # Stop
        ui_manager.stop()
        assert not ui_manager.is_running
        mock_live_instance.stop.assert_called_once()

        # Multiple stops should be safe
        ui_manager.stop()
        assert not ui_manager.is_running


class TestUIConfiguration:
    """Test UI configuration and customization."""

    def test_ui_config_defaults(self):
        """Test UIConfig default values."""
        config = UIConfig()

        assert config.mode == "classic"
        assert config.window_height == 20
        assert config.update_frequency == 0.1
        assert config.show_stats is True
        assert config.show_progress_bars is True
        assert config.show_recent_activity is True
        assert config.recent_activity_lines == 3
        assert config.colors is not None
        assert 'progress_complete' in config.colors

    def test_ui_config_customization(self):
        """Test UIConfig customization."""
        custom_colors = {
            'progress_complete': 'blue',
            'error': 'magenta'
        }

        config = UIConfig(
            mode="split-window",
            window_height=30,
            update_frequency=0.05,
            colors=custom_colors
        )

        assert config.mode == "split-window"
        assert config.window_height == 30
        assert config.update_frequency == 0.05
        assert config.colors == custom_colors


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_event_emission(self):
        """Test error handling for invalid event types."""
        tracker = ProgressTracker()

        # Should raise TypeError for non-ProgressEvent objects
        with pytest.raises(TypeError):
            tracker.emit_event("not an event")

    def test_ui_manager_exception_handling(self):
        """Test UI manager handles exceptions gracefully."""
        tracker = ProgressTracker()
        config = UIConfig(mode="classic")
        ui_manager = create_ui_manager(config, tracker)

        # Create a callback that raises an exception
        def failing_callback(event):
            raise Exception("Test exception")

        tracker.subscribe(failing_callback)

        # Start tracker and UI
        tracker.start()
        ui_manager.start()

        try:
            # Emit an event - should not crash despite callback exception
            event = create_start_event(PipelineType.TTS, 1, "test")
            tracker.emit_event(event)

            # Give time for processing
            time.sleep(0.1)

            # Tracker should still be running
            assert tracker._running

        finally:
            ui_manager.stop()
            tracker.stop()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])