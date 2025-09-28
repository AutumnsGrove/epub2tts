#!/usr/bin/env python3
"""
Test script to validate the TTS pipeline integration with Kokoro TTS.
"""

import sys
import numpy as np
from pathlib import Path
import soundfile as sf

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.tts_pipeline import KokoroTTSPipeline, MLXKokoroModel
from utils.config import TTSConfig, load_config

def test_config_loading():
    """Test configuration loading."""
    print("🔍 Testing Configuration Loading...")

    try:
        config = load_config()
        print(f"  ✅ Config loaded successfully")
        print(f"    - TTS Model: {config.tts.model}")
        print(f"    - Model Path: {config.tts.model_path}")
        print(f"    - Voice: {config.tts.voice}")
        print(f"    - Use MLX: {config.tts.use_mlx}")
        print(f"    - Sample Rate: {config.tts.sample_rate}")

        return True, config
    except Exception as e:
        print(f"  ❌ Config loading failed: {e}")
        return False, None

def test_tts_model_init(config):
    """Test TTS model initialization."""
    print("\n🔍 Testing TTS Model Initialization...")

    try:
        model = MLXKokoroModel(config.tts)
        print(f"  ✅ MLXKokoroModel initialized")
        print(f"    - Using MLX-Audio: {model.use_mlx_audio}")
        print(f"    - Model Path: {model.model_path}")
        print(f"    - Voice: {model.voice}")

        # Test voice enumeration
        voices = model.get_available_voices()
        print(f"    - Available voices: {len(voices)} ({', '.join(voices[:5])}...)")

        return True, model
    except Exception as e:
        print(f"  ❌ Model initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_audio_synthesis(model, test_texts):
    """Test audio synthesis."""
    print("\n🔍 Testing Audio Synthesis...")

    results = []
    for i, text in enumerate(test_texts):
        try:
            print(f"  🔄 Test {i+1}: '{text[:30]}...'")

            # Synthesize audio
            audio_data = model.synthesize(text, voice="bf_lily", speed=1.0)

            # Validate audio
            if isinstance(audio_data, np.ndarray) and len(audio_data) > 0:
                duration = len(audio_data) / 22050
                print(f"    ✅ Audio generated: {len(audio_data)} samples ({duration:.2f}s)")
                print(f"      - Min: {audio_data.min():.4f}, Max: {audio_data.max():.4f}")
                print(f"      - Non-zero: {np.count_nonzero(audio_data)} samples")

                # Save test audio
                output_file = f"test_output_{i+1}.wav"
                sf.write(output_file, audio_data, 22050)
                print(f"      - Saved to: {output_file}")

                results.append((True, len(audio_data), duration))
            else:
                print(f"    ❌ Invalid audio data: {type(audio_data)}")
                results.append((False, 0, 0))

        except Exception as e:
            print(f"    ❌ Synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((False, 0, 0))

    return results

def test_tts_pipeline_integration(config):
    """Test full TTS pipeline integration."""
    print("\n🔍 Testing TTS Pipeline Integration...")

    try:
        pipeline = KokoroTTSPipeline(config.tts)
        print(f"  ✅ TTS Pipeline initialized")

        # Test pipeline info
        info = pipeline.get_voice_info()
        print(f"    - Current voice: {info['current_voice']}")
        print(f"    - Available voices: {len(info['available_voices'])} voices")
        print(f"    - Sample rate: {info['sample_rate']}")

        # Test synthesis through pipeline
        test_text = "The TTS pipeline is working correctly with Kokoro."
        result = pipeline.process_chunk(test_text, "test_pipeline_output.wav")

        if result.success and result.audio_path:
            print(f"  ✅ Pipeline synthesis successful: {result.duration:.2f}s audio")
            print(f"    - Saved to: {result.audio_path}")
            return True
        else:
            print(f"  ❌ Pipeline synthesis failed: {result.error_message}")
            return False

    except Exception as e:
        print(f"  ❌ Pipeline integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_voice_comparison(model):
    """Test different voice qualities."""
    print("\n🔍 Testing Voice Quality Comparison...")

    voices_to_test = ["bf_lily", "bf_emma", "af_bella", "af_heart"]
    test_text = "This is a voice quality test for comparison."

    for voice in voices_to_test:
        try:
            print(f"  🔄 Testing voice: {voice}")
            audio_data = model.synthesize(test_text, voice=voice)

            if isinstance(audio_data, np.ndarray) and len(audio_data) > 0:
                duration = len(audio_data) / 22050
                print(f"    ✅ {voice}: {len(audio_data)} samples ({duration:.2f}s)")

                # Save voice comparison audio
                sf.write(f"test_voice_{voice}.wav", audio_data, 22050)
                print(f"      - Saved to: test_voice_{voice}.wav")
            else:
                print(f"    ❌ {voice}: synthesis failed")

        except Exception as e:
            print(f"    ❌ {voice}: error - {e}")

def main():
    """Run TTS pipeline tests."""
    print("🚀 TTS Pipeline Integration Tests\n")

    # Test texts with varying complexity
    test_texts = [
        "Hello world!",
        "This is a longer sentence to test the quality of text-to-speech synthesis with more complex patterns.",
        "Testing punctuation: questions? exclamations! And... pauses.",
        "Numbers and abbreviations: 123 main street, Dr. Smith, at 3:45 PM on Jan. 1st, 2025."
    ]

    results = {}

    # 1. Test configuration
    config_ok, config = test_config_loading()
    results['config'] = config_ok

    if not config_ok:
        print("❌ Cannot continue without valid configuration")
        return False

    # 2. Test model initialization
    model_ok, model = test_tts_model_init(config)
    results['model_init'] = model_ok

    if not model_ok:
        print("❌ Cannot continue without valid model")
        return False

    # 3. Test audio synthesis
    synthesis_results = test_audio_synthesis(model, test_texts)
    successful_synthesis = sum(1 for success, _, _ in synthesis_results if success)
    results['synthesis'] = successful_synthesis == len(test_texts)

    # 4. Test pipeline integration
    pipeline_ok = test_tts_pipeline_integration(config)
    results['pipeline'] = pipeline_ok

    # 5. Test voice comparison
    test_voice_comparison(model)

    # Summary
    print("\n📊 Test Results Summary:")
    total_tests = len(results)
    passed_tests = sum(results.values())

    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name.replace('_', ' ').title()}")

    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! TTS pipeline is ready for production use.")
        print("\n📁 Generated test files:")
        test_files = list(Path(".").glob("test_*.wav"))
        for file in test_files:
            print(f"  - {file.name}")
        return True
    else:
        print("\n⚠️ Some tests failed. Review the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)