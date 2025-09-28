#!/usr/bin/env python3
"""
Test direct Kokoro TTS without MLX-Audio to validate fallback implementation.
"""

import sys
import traceback
import numpy as np
from pathlib import Path

def test_direct_kokoro_synthesis():
    """Test direct Kokoro audio synthesis."""
    print("🔍 Testing Direct Kokoro Audio Synthesis...")

    try:
        from kokoro import KPipeline
        print("  ✅ KPipeline imported")

        # Create pipeline
        pipeline = KPipeline("a")  # 'a' for autodetect
        print("  ✅ KPipeline created successfully")

        # Test synthesis
        test_text = "Hello, this is a test of the Kokoro text-to-speech system."
        print(f"  🔄 Synthesizing: '{test_text}'")

        # Generate audio
        audio_data = pipeline.synthesize(test_text, voice="bf_lily")
        print(f"  ✅ Audio generated! Shape: {audio_data.shape}, Type: {type(audio_data)}")

        # Validate audio data
        if isinstance(audio_data, np.ndarray):
            print(f"  📊 Audio stats:")
            print(f"    - Duration: {len(audio_data) / 22050:.2f} seconds (assuming 22kHz)")
            print(f"    - Min value: {audio_data.min():.4f}")
            print(f"    - Max value: {audio_data.max():.4f}")
            print(f"    - Mean: {audio_data.mean():.4f}")

            # Check if audio has actual content (not silence)
            if np.std(audio_data) > 0.001:
                print("  ✅ Audio contains actual content (not silence)")
            else:
                print("  ⚠️ Audio appears to be mostly silence")

        return True, audio_data

    except Exception as e:
        print(f"  ❌ Direct Kokoro synthesis error: {e}")
        traceback.print_exc()
        return False, None

def test_voice_availability():
    """Test voice file availability."""
    print("\n🔍 Testing Voice Availability...")

    voices_dir = Path("./models/Kokoro-82M-8bit/voices")

    if not voices_dir.exists():
        print(f"  ❌ Voices directory not found: {voices_dir}")
        return False

    # Get all voice files
    voice_files = list(voices_dir.glob("*.pt"))
    print(f"  ✅ Found {len(voice_files)} voice files")

    # Test specific voices
    test_voices = ["bf_lily", "bf_emma", "af_bella", "af_heart"]
    available_voices = []

    for voice in test_voices:
        voice_file = voices_dir / f"{voice}.pt"
        if voice_file.exists():
            print(f"  ✅ {voice}: available ({voice_file.stat().st_size // 1024}KB)")
            available_voices.append(voice)
        else:
            print(f"  ❌ {voice}: not found")

    return len(available_voices) > 0, available_voices

def test_speed_adjustment():
    """Test speed adjustment functionality."""
    print("\n🔍 Testing Speed Adjustment...")

    try:
        import scipy.signal
        print("  ✅ Scipy available for speed adjustment")

        # Create test audio
        sample_rate = 22050
        duration = 1.0  # 1 second
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave

        # Test speed adjustment
        target_length = int(len(test_audio) / 1.5)  # 1.5x speed
        adjusted_audio = scipy.signal.resample(test_audio, target_length)

        print(f"  ✅ Speed adjustment working:")
        print(f"    - Original length: {len(test_audio)} samples")
        print(f"    - Adjusted length: {len(adjusted_audio)} samples")
        print(f"    - Speed factor: {len(test_audio) / len(adjusted_audio):.2f}x")

        return True

    except Exception as e:
        print(f"  ❌ Speed adjustment error: {e}")
        return False

def save_test_audio(audio_data, filename="test_output.wav"):
    """Save test audio to file."""
    print(f"\n🔍 Saving test audio to {filename}...")

    try:
        import soundfile as sf

        # Ensure audio is in correct format
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Normalize if needed
        if np.max(np.abs(audio_data)) > 1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))

        sf.write(filename, audio_data, 22050)
        print(f"  ✅ Audio saved to {filename}")
        return True

    except Exception as e:
        print(f"  ❌ Error saving audio: {e}")
        return False

def main():
    """Run direct Kokoro tests."""
    print("🚀 Direct Kokoro TTS Tests\n")

    # Test voice availability first
    voices_available, available_voices = test_voice_availability()

    if not voices_available:
        print("❌ No voices available, cannot continue")
        return False

    # Test speed adjustment
    speed_working = test_speed_adjustment()

    # Test synthesis
    synthesis_working, audio_data = test_direct_kokoro_synthesis()

    if synthesis_working and audio_data is not None:
        # Save test audio
        save_test_audio(audio_data)

        print("\n✅ Direct Kokoro TTS is working!")
        print("💡 This can be used as fallback when MLX-Audio fails")
        return True
    else:
        print("\n❌ Direct Kokoro TTS failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)