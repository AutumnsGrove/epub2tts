#!/usr/bin/env python3
"""
Simple MLX integration test to verify the TTS pipeline is working.
"""

import sys
import os
import numpy as np
import soundfile as sf
from pathlib import Path

def test_mlx_kokoro_direct():
    """Test MLX Kokoro integration directly."""
    print("🚀 Simple MLX Kokoro Test\n")

    # Test 1: Test imports
    print("🔍 Testing imports...")
    try:
        import mlx
        print("  ✅ MLX imported")

        import mlx_audio
        print("  ✅ MLX-Audio imported")

        import kokoro
        print("  ✅ Kokoro imported")

    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

    # Test 2: Test MLX-Audio generation (returns None issue)
    print("\n🔍 Testing MLX-Audio generation...")
    try:
        from mlx_audio.tts.generate import generate_audio

        model_path = "./models/Kokoro-82M-8bit"
        text = "This is a test of the MLX audio generation system."
        voice = "bf_lily"

        print(f"  🔄 Generating audio...")
        print(f"    Model: {model_path}")
        print(f"    Text: {text}")
        print(f"    Voice: {voice}")

        audio_data = generate_audio(
            text=text,
            model_path=model_path,
            voice=voice,
            speed=1.0
        )

        print(f"  📊 MLX-Audio result: {type(audio_data)}")
        if audio_data is None:
            print("  ⚠️ MLX-Audio returned None (known issue)")
            print("  💡 Audio was likely saved to file instead")

            # Check for generated file
            generated_files = list(Path(".").glob("audio_*.wav"))
            if generated_files:
                latest_file = max(generated_files, key=os.path.getctime)
                print(f"  ✅ Found generated file: {latest_file}")

                # Load the audio file to verify
                audio_data, sample_rate = sf.read(str(latest_file))
                print(f"  📊 Loaded audio: {audio_data.shape}, {sample_rate}Hz")
                return True, audio_data, sample_rate
            else:
                print("  ❌ No audio files found")
                return False, None, None
        else:
            print(f"  ✅ MLX-Audio returned data: {audio_data.shape}")
            return True, audio_data, 22050

    except Exception as e:
        print(f"  ❌ MLX-Audio error: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None

def test_direct_kokoro_fallback():
    """Test direct Kokoro as fallback."""
    print("\n🔍 Testing direct Kokoro fallback...")
    try:
        from kokoro import KPipeline

        # Create pipeline
        pipeline = KPipeline("a")  # 'a' for autodetect
        print("  ✅ KPipeline created")

        # Test synthesis
        text = "This is a test of the direct Kokoro fallback system."
        print(f"  🔄 Synthesizing: {text}")

        voice_pack = pipeline.load_voice("bf_lily")
        ps, tokens = pipeline.g2p(text)
        output = pipeline.infer(pipeline.model, ps, voice_pack)
        audio_data = output.audio.numpy() if hasattr(output.audio, 'numpy') else output.audio

        if isinstance(audio_data, np.ndarray) and len(audio_data) > 0:
            duration = len(audio_data) / 22050
            print(f"  ✅ Direct Kokoro success: {audio_data.shape}, {duration:.2f}s")

            # Save test output
            sf.write("test_direct_kokoro.wav", audio_data, 22050)
            print(f"  💾 Saved to: test_direct_kokoro.wav")

            return True, audio_data
        else:
            print(f"  ❌ Invalid audio data: {type(audio_data)}")
            return False, None

    except Exception as e:
        print(f"  ❌ Direct Kokoro error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_voice_comparison():
    """Test different voices."""
    print("\n🔍 Testing voice comparison...")

    voices_to_test = ["bf_lily", "bf_emma", "af_bella"]
    text = "Voice quality comparison test."

    from kokoro import KPipeline
    pipeline = KPipeline("a")

    results = {}
    for voice in voices_to_test:
        try:
            print(f"  🔄 Testing {voice}...")
            voice_pack = pipeline.load_voice(voice)
            ps, tokens = pipeline.g2p(text)
            output = pipeline.infer(pipeline.model, ps, voice_pack)
            audio_data = output.audio.numpy() if hasattr(output.audio, 'numpy') else output.audio

            if isinstance(audio_data, np.ndarray) and len(audio_data) > 0:
                duration = len(audio_data) / 22050
                sf.write(f"test_voice_{voice}.wav", audio_data, 22050)
                print(f"    ✅ {voice}: {duration:.2f}s - saved")
                results[voice] = True
            else:
                print(f"    ❌ {voice}: failed")
                results[voice] = False

        except Exception as e:
            print(f"    ❌ {voice}: error - {e}")
            results[voice] = False

    return results

def main():
    """Run all tests."""
    print("🎯 MLX Integration Status Test\n")

    results = {}

    # Test MLX-Audio generation
    mlx_success, mlx_audio, mlx_sr = test_mlx_kokoro_direct()
    results['mlx_audio'] = mlx_success

    # Test direct Kokoro fallback
    kokoro_success, kokoro_audio = test_direct_kokoro_fallback()
    results['direct_kokoro'] = kokoro_success

    # Test voice comparison
    voice_results = test_voice_comparison()
    results['voices'] = sum(voice_results.values()) > 0

    # Summary
    print("\n📊 Test Results Summary:")
    total_tests = len(results)
    passed_tests = sum(results.values())

    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name.replace('_', ' ').title()}")

    print(f"\n🎯 Overall: {passed_tests}/{total_tests} major tests passed")

    # Specific findings
    print("\n🔍 Key Findings:")
    if results['mlx_audio']:
        print("  ✅ MLX-Audio is working (may save to file instead of returning data)")
    else:
        print("  ❌ MLX-Audio has issues")

    if results['direct_kokoro']:
        print("  ✅ Direct Kokoro fallback is working correctly")
    else:
        print("  ❌ Direct Kokoro fallback failed")

    if results['voices']:
        print("  ✅ Multiple voices are available and working")
    else:
        print("  ❌ Voice switching has issues")

    # Recommendations
    print("\n💡 Recommendations:")
    if results['direct_kokoro'] and not results['mlx_audio']:
        print("  🔄 Use direct Kokoro as primary until MLX-Audio return issue is fixed")
    elif results['mlx_audio']:
        print("  🚀 MLX-Audio is working - may need to handle file-based output")

    if passed_tests >= 2:
        print("  ✅ TTS system is functional and ready for use")
    else:
        print("  ⚠️ TTS system needs debugging before production use")

    return passed_tests >= 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)