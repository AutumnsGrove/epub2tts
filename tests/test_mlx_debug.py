#!/usr/bin/env python3
"""
Debug script to test MLX-Audio integration and identify SystemExit issues.
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test basic imports."""
    print("🔍 Testing imports...")
    try:
        import mlx
        # MLX doesn't have __version__ in all versions
        print(f"  ✅ MLX imported successfully")

        import mlx_audio
        print(f"  ✅ MLX-Audio imported successfully")

        import kokoro
        print(f"  ✅ Kokoro imported successfully")

        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_mlx_audio_basic():
    """Test MLX-Audio basic functionality."""
    print("\n🔍 Testing MLX-Audio basic functionality...")
    try:
        from mlx_audio.tts.generate import generate_audio
        print("  ✅ MLX-Audio generate function imported")
        return True
    except Exception as e:
        print(f"  ❌ MLX-Audio import error: {e}")
        traceback.print_exc()
        return False

def test_model_path():
    """Test model path exists."""
    print("\n🔍 Testing model path...")
    model_path = Path("./models/Kokoro-82M-8bit")

    if model_path.exists():
        print(f"  ✅ Model directory exists: {model_path}")

        # Check key files
        config_file = model_path / "config.json"
        model_file = model_path / "kokoro-v1_0.safetensors"
        voices_dir = model_path / "voices"

        if config_file.exists():
            print(f"  ✅ Config file exists: {config_file}")
        else:
            print(f"  ❌ Config file missing: {config_file}")

        if model_file.exists():
            print(f"  ✅ Model file exists: {model_file}")
        else:
            print(f"  ❌ Model file missing: {model_file}")

        if voices_dir.exists():
            voice_files = list(voices_dir.glob("*.pt"))
            print(f"  ✅ Voices directory with {len(voice_files)} voices")

            # Check for bf_lily specifically
            bf_lily = voices_dir / "bf_lily.pt"
            if bf_lily.exists():
                print(f"  ✅ bf_lily voice found: {bf_lily}")
            else:
                print(f"  ❌ bf_lily voice missing")
        else:
            print(f"  ❌ Voices directory missing: {voices_dir}")

        return True
    else:
        print(f"  ❌ Model directory missing: {model_path}")
        return False

def test_direct_kokoro():
    """Test direct Kokoro without MLX-Audio."""
    print("\n🔍 Testing direct Kokoro...")
    try:
        from kokoro import KPipeline
        print("  ✅ KPipeline imported")

        # Try to create pipeline with required lang_code parameter
        pipeline = KPipeline("a")  # 'a' for autodetect
        print("  ✅ KPipeline created successfully")

        return True
    except Exception as e:
        print(f"  ❌ Direct Kokoro error: {e}")
        traceback.print_exc()
        return False

def test_mlx_audio_generation():
    """Test MLX-Audio generation that previously failed."""
    print("\n🔍 Testing MLX-Audio generation (where SystemExit occurred)...")

    try:
        from mlx_audio.tts.generate import generate_audio

        # Test with minimal parameters
        model_path = "./models/Kokoro-82M-8bit"
        text = "Hello world"
        voice = "bf_lily"

        print(f"  🔄 Attempting generation with:")
        print(f"    Model: {model_path}")
        print(f"    Text: {text}")
        print(f"    Voice: {voice}")

        # This is where the SystemExit(1) occurred previously
        audio_data = generate_audio(
            text=text,
            model_path=model_path,
            voice=voice,
            speed=1.0
        )

        print(f"  ✅ MLX-Audio generation successful! Audio shape: {audio_data.shape}")
        return True

    except SystemExit as e:
        print(f"  ❌ SystemExit caught: {e}")
        print(f"  📋 This is the error mentioned in the checkpoint")
        return False
    except Exception as e:
        print(f"  ❌ MLX-Audio generation error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 MLX Integration Debug Tests\n")

    results = []
    results.append(("Imports", test_imports()))
    results.append(("MLX-Audio Basic", test_mlx_audio_basic()))
    results.append(("Model Path", test_model_path()))
    results.append(("Direct Kokoro", test_direct_kokoro()))
    results.append(("MLX-Audio Generation", test_mlx_audio_generation()))

    print("\n📊 Results Summary:")
    for test_name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}")

    total_passed = sum(result[1] for result in results)
    print(f"\n🎯 {total_passed}/{len(results)} tests passed")

    if not results[-1][1]:  # If MLX-Audio generation failed
        print("\n💡 Recommendations:")
        print("  1. Try the direct Kokoro fallback implementation")
        print("  2. Check for environment or path issues")
        print("  3. Consider alternative MLX-Audio versions")

if __name__ == "__main__":
    main()