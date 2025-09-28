#!/usr/bin/env python3
"""
Demo script to test the sophisticated terminal UI system.

This script demonstrates the split-window UI with simulated progress
for both TTS and image processing pipelines.
"""

import sys
import time
import threading
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ui.progress_tracker import (
    ProgressTracker, PipelineType, EventType,
    create_start_event, create_progress_event, create_complete_event, create_error_event
)
from ui.terminal_ui import TerminalUIManager, UIConfig, create_ui_manager
from utils.config import load_config


def simulate_tts_pipeline(tracker: ProgressTracker):
    """Simulate TTS pipeline processing."""
    chapters = [
        "Chapter 1: Introduction",
        "Chapter 2: Getting Started",
        "Chapter 3: Advanced Topics",
        "Chapter 4: Best Practices",
        "Chapter 5: Conclusion"
    ]

    # Start TTS processing
    tracker.emit_event(create_start_event(
        PipelineType.TTS,
        total_items=len(chapters),
        current_item="Starting TTS processing"
    ))

    for i, chapter in enumerate(chapters):
        # Start chapter
        tracker.emit_event(create_progress_event(
            PipelineType.TTS,
            completed_items=i,
            total_items=len(chapters),
            current_item=chapter
        ))

        # Simulate processing time
        time.sleep(2 + (i % 3))  # Variable processing time

        # Complete chapter
        tracker.emit_event(create_complete_event(
            PipelineType.TTS,
            current_item=chapter,
            duration=30.5 + i * 5,  # Simulated audio duration
            processing_time=2.1 + i * 0.3
        ))

        # Final progress update
        tracker.emit_event(create_progress_event(
            PipelineType.TTS,
            completed_items=i + 1,
            total_items=len(chapters),
            current_item=f"Completed {i+1}/{len(chapters)} chapters"
        ))


def simulate_image_pipeline(tracker: ProgressTracker):
    """Simulate image processing pipeline."""
    images = [
        "figure_1_diagram.png",
        "chart_2_performance.jpg",
        "illustration_3_concept.png",
        "graph_4_results.jpg",
        "diagram_5_architecture.png",
        "photo_6_example.jpg",
        "screenshot_7_interface.png"
    ]

    # Start image processing
    tracker.emit_event(create_start_event(
        PipelineType.IMAGE,
        total_items=len(images),
        current_item="Starting image processing"
    ))

    cache_hits = 0

    for i, image in enumerate(images):
        # Start image
        tracker.emit_event(create_progress_event(
            PipelineType.IMAGE,
            completed_items=i,
            total_items=len(images),
            current_item=image
        ))

        # Simulate cache hit for some images
        is_cache_hit = i % 3 == 0
        if is_cache_hit:
            cache_hits += 1
            time.sleep(0.1)  # Cache hits are fast
        else:
            time.sleep(1.5 + (i % 2))  # Variable processing time

        # Complete image
        tracker.emit_event(create_complete_event(
            PipelineType.IMAGE,
            current_item=image,
            processing_time=0.1 if is_cache_hit else 2.3,
            cache_hit=is_cache_hit,
            confidence=0.85 + (i % 3) * 0.05
        ))

        # Progress update with custom stats
        tracker.emit_event(create_progress_event(
            PipelineType.IMAGE,
            completed_items=i + 1,
            total_items=len(images),
            current_item=f"Processed {i+1}/{len(images)} images",
            custom_stats={'cache_hits': cache_hits}
        ))


def main():
    """Main demo function."""
    print("🎨 epub2tts Terminal UI Demo")
    print("=" * 50)

    try:
        # Load configuration and set to split-window mode
        config = load_config()
        config.ui.mode = "split-window"
        config.ui.update_frequency = 0.05  # Fast updates for demo

        print(f"📊 UI Mode: {config.ui.mode}")
        print(f"🔄 Update Frequency: {config.ui.update_frequency}s")

        # Create progress tracker and UI
        tracker = ProgressTracker()
        ui_manager = create_ui_manager(config.ui, tracker)

        if not ui_manager.is_available():
            print("❌ Split-window UI not available (Rich library required)")
            print("💡 Run: pip install rich>=13.0.0")
            return

        print("✅ Split-window UI available")
        print("\n🚀 Starting UI demo...")
        print("   - Press Ctrl+C to stop")
        print("   - Watch the real-time progress in both panels")
        print()

        # Start UI
        if not ui_manager.start():
            print("❌ Failed to start UI")
            return

        try:
            # Start both pipelines in parallel
            tts_thread = threading.Thread(target=simulate_tts_pipeline, args=(tracker,))
            image_thread = threading.Thread(target=simulate_image_pipeline, args=(tracker,))

            tts_thread.start()
            image_thread.start()

            # Wait for both to complete
            tts_thread.join()
            image_thread.join()

            # Keep UI running a bit longer to see final results
            time.sleep(3)

        finally:
            ui_manager.stop()

        print("\n✅ Demo completed successfully!")
        print("🎉 The sophisticated terminal UI system is working perfectly!")

    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
        if 'ui_manager' in locals():
            ui_manager.stop()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()