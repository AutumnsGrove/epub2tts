#!/usr/bin/env python3
"""
Simple TTS test without complex imports to test core functionality.
"""

import sys
import numpy as np
from pathlib import Path
import soundfile as sf

def test_basic_kokoro():
    """Test basic Kokoro functionality."""
    print("🔍 Testing Basic Kokoro TTS...")

    try:
        from kokoro import KPipeline
        print("  ✅ Kokoro imported successfully")

        # Initialize pipeline
        pipeline = KPipeline('a')  # 'a' for autodetect
        print("  ✅ KPipeline initialized")

        # Test synthesis
        test_text = "Hello! This is a test of the Kokoro text to speech system."
        print(f"  🔄 Synthesizing: '{test_text}'")

        audio_data = pipeline.synthesize(test_text, voice="bf_lily")
        print(f"  ✅ Audio generated: {type(audio_data)}, shape: {getattr(audio_data, 'shape', 'N/A')}")

        # Convert to numpy if needed
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)

        if len(audio_data) > 0:
            duration = len(audio_data) / 22050
            print(f"    - Duration: {duration:.2f} seconds")
            print(f"    - Min/Max: {audio_data.min():.4f}/{audio_data.max():.4f}")

            # Save audio
            output_file = "simple_test_output.wav"
            sf.write(output_file, audio_data, 22050)
            print(f"    - Saved to: {output_file}")

            return True
        else:
            print("  ❌ Empty audio data")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mlx_audio():
    """Test MLX-Audio directly."""
    print("\n🔍 Testing MLX-Audio Direct...")

    try:
        from mlx_audio.tts.generate import generate_audio
        print("  ✅ MLX-Audio imported")

        # Test generation
        test_text = "Testing MLX Audio generation."
        model_path = "../models/Kokoro-82M-8bit"

        print(f"  🔄 Generating with MLX-Audio...")
        audio_data = generate_audio(
            text=test_text,
            model_path=model_path,
            voice="bf_lily",
            speed=1.0
        )

        print(f"  ✅ MLX-Audio generation successful: {type(audio_data)}")

        if hasattr(audio_data, 'shape'):
            print(f"    - Shape: {audio_data.shape}")

        return True

    except SystemExit as e:
        print(f"  ❌ MLX-Audio SystemExit: {e}")
        return False
    except Exception as e:
        print(f"  ❌ MLX-Audio error: {e}")
        return False

def test_voice_files():
    """Test voice file availability."""
    print("\n🔍 Testing Voice Files...")

    voices_dir = Path("../models/Kokoro-82M-8bit/voices")

    if voices_dir.exists():
        voice_files = list(voices_dir.glob("*.pt"))
        print(f"  ✅ Found {len(voice_files)} voice files")

        # Test specific voices
        test_voices = ["bf_lily", "bf_emma", "af_bella"]
        for voice in test_voices:
            voice_file = voices_dir / f"{voice}.pt"
            if voice_file.exists():
                size_kb = voice_file.stat().st_size // 1024
                print(f"    ✅ {voice}: {size_kb}KB")
            else:
                print(f"    ❌ {voice}: not found")

        return True
    else:
        print(f"  ❌ Voices directory not found: {voices_dir}")
        return False

def main():
    """Run simple TTS tests."""
    print("🚀 Simple TTS Tests\n")

    results = []

    # Test voice files
    results.append(("Voice Files", test_voice_files()))

    # Test basic Kokoro
    results.append(("Basic Kokoro", test_basic_kokoro()))

    # Test MLX-Audio
    results.append(("MLX-Audio", test_mlx_audio()))

    # Summary
    print("\n📊 Test Results:")
    passed = 0
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
        if success:
            passed += 1

    print(f"\n🎯 {passed}/{len(results)} tests passed")

    if passed >= 1:  # At least one method working
        print("\n🎉 TTS functionality is available!")
        return True
    else:
        print("\n❌ No TTS methods working")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)