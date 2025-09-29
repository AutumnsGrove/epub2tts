#!/usr/bin/env python3
"""
Example script demonstrating ElevenLabs TTS integration.

This script shows how to:
1. Set up the ElevenLabs TTS pipeline
2. Process text chunks
3. Handle different voice settings
4. Batch process multiple texts
"""

import sys
import os
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.elevenlabs_tts_pipeline import (
    ElevenLabsTTSPipeline,
    ElevenLabsConfig,
    create_elevenlabs_tts_pipeline
)
from utils.logger import setup_logging

def main():
    """Demonstrate ElevenLabs TTS functionality."""

    # Setup logging
    setup_logging()

    print("🎙️ ElevenLabs TTS Integration Demo")
    print("=" * 50)

    try:
        # Create TTS pipeline with default configuration
        print("1. Initializing ElevenLabs TTS pipeline...")
        pipeline = create_elevenlabs_tts_pipeline()

        # Check if initialization was successful
        if not pipeline.is_initialized:
            print("❌ Failed to initialize ElevenLabs pipeline. Check your API key.")
            return

        print("✅ ElevenLabs pipeline initialized successfully!")

        # Get available voices
        print("\n2. Getting available voices...")
        voices = pipeline.get_available_voices()

        if voices:
            print(f"📢 Found {len(voices)} available voices:")
            for i, voice in enumerate(voices[:5]):  # Show first 5 voices
                print(f"   {i+1}. {voice['name']} (ID: {voice['voice_id']})")
            if len(voices) > 5:
                print(f"   ... and {len(voices) - 5} more voices")
        else:
            print("⚠️ No voices retrieved. Using default voice.")

        # Test single text processing
        print("\n3. Testing single text processing...")
        test_text = "Hello! This is a test of the ElevenLabs text-to-speech integration. The system should convert this text into natural-sounding speech."

        output_dir = Path("output/elevenlabs_test")
        output_dir.mkdir(parents=True, exist_ok=True)

        result = pipeline.process_chunk(
            text=test_text,
            output_path=str(output_dir / "test_single.mp3"),
            chunk_id="test_single"
        )

        if result.success:
            print(f"✅ Single text processing successful!")
            print(f"   📁 Audio saved to: {result.audio_path}")
            print(f"   ⏱️ Processing time: {result.processing_time:.2f}s")
            print(f"   📝 Characters processed: {result.characters_processed}")
        else:
            print(f"❌ Single text processing failed: {result.error_message}")

        # Test text chunking
        print("\n4. Testing text chunking...")
        long_text = """
        This is a longer text that will be automatically chunked by the ElevenLabs TTS pipeline.
        The system intelligently splits text at sentence boundaries to stay within API character limits.
        Each chunk is processed separately and can be merged later into a complete audiobook.
        This approach ensures reliable processing even for very long documents like books or articles.
        The chunking algorithm preserves sentence structure and maintains natural speech flow.
        """.strip()

        chunks = pipeline.chunk_text(long_text)
        print(f"📄 Long text split into {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}: {len(chunk)} characters")

        # Test batch processing
        print("\n5. Testing batch processing...")
        test_chunks = [
            {"id": "intro", "text": "Welcome to the ElevenLabs TTS demonstration."},
            {"id": "features", "text": "This system provides high-quality text-to-speech conversion with multiple voice options."},
            {"id": "conclusion", "text": "Thank you for trying the ElevenLabs integration!"}
        ]

        batch_results = pipeline.batch_process(
            text_chunks=test_chunks,
            output_dir=output_dir / "batch_test"
        )

        successful_batch = [r for r in batch_results if r.success]
        print(f"📦 Batch processing completed: {len(successful_batch)}/{len(batch_results)} successful")

        # Show usage statistics
        print("\n6. Session statistics...")
        stats = pipeline.get_usage_stats()
        print(f"   📊 Total characters processed: {stats['total_characters_processed']}")
        print(f"   🔄 Total API calls: {stats['total_api_calls']}")
        print(f"   ⚡ Processing rate: {stats['processing_rate_chars_per_second']:.1f} chars/sec")
        print(f"   ⏱️ Session duration: {stats['session_duration_seconds']:.1f} seconds")

        # Test audio merging if we have multiple files
        if len(successful_batch) > 1:
            print("\n7. Testing audio merging...")
            audio_files = [r.audio_path for r in successful_batch]
            merged_path = output_dir / "merged_test.mp3"

            if pipeline.merge_audio_files(audio_files, str(merged_path)):
                print(f"✅ Audio files merged successfully: {merged_path}")
            else:
                print("❌ Audio merging failed")

        print(f"\n🎉 Demo completed! Check the output directory: {output_dir}")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_configuration():
    """Test different configuration options."""

    print("\n🔧 Testing custom configuration...")

    # Create custom config
    custom_config = ElevenLabsConfig(
        api_key="dummy-key-for-testing",  # This will fail but shows config options
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        stability=0.7,  # More stable voice
        similarity_boost=0.3,  # Less similarity boost
        style=0.2,  # Slight style adjustment
        max_chunk_chars=2000,  # Smaller chunks
        max_retries=2,  # Fewer retries
        rate_limit_delay=1.5  # Longer delay between retries
    )

    print("Custom configuration created:")
    print(f"   Voice ID: {custom_config.voice_id}")
    print(f"   Model: {custom_config.model_id}")
    print(f"   Stability: {custom_config.stability}")
    print(f"   Max chunk size: {custom_config.max_chunk_chars} characters")
    print(f"   Retry settings: {custom_config.max_retries} retries, {custom_config.rate_limit_delay}s delay")

if __name__ == "__main__":
    # Run main demo
    main()

    # Test configuration options
    test_configuration()

    print("\n📖 For more information:")
    print("   - Check the ElevenLabs API documentation: https://elevenlabs.io/docs")
    print("   - Review the pipeline source code in: src/pipelines/elevenlabs_tts_pipeline.py")
    print("   - Ensure your ElevenLabs API key is set in secrets.json")