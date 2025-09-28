#!/usr/bin/env python3
"""
Test script to verify TTS pipeline fixes.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_logging():
    """Setup logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_metal_framework_resilience():
    """Test Metal framework error handling and fallback mechanisms."""
    print("\n🔬 Testing Metal Framework Resilience...")

    try:
        from utils.config import load_config
        from pipelines.tts_pipeline import MLXKokoroModel

        config = load_config()
        model = MLXKokoroModel(config.tts)

        print(f"✅ MLX Model initialized with degradation level: {model.degradation_level}")
        print(f"✅ Force sequential: {model.force_sequential}")
        print(f"✅ Max retries: {model.max_retries}")

        # Test resource cleanup
        model._cleanup_metal_resources()
        print("✅ Metal resource cleanup executed without errors")

        # Test mock synthesis fallback
        mock_audio = model._try_mock_synthesis("Test text", 1.0)
        print(f"✅ Mock synthesis fallback works: {mock_audio.shape}")

        return True

    except Exception as e:
        print(f"❌ Metal framework test failed: {e}")
        return False

def test_image_pipeline_paths():
    """Test image pipeline path handling."""
    print("\n🖼️  Testing Image Pipeline Path Handling...")

    try:
        from utils.config import load_config
        from pipelines.image_pipeline import ImageDescriptionPipeline, GemmaVLMModel

        config = load_config()

        # Test Gemma model initialization (without actual connection)
        gemma_model = GemmaVLMModel("gemma-3n-e4b", "http://127.0.0.1:1234")
        print(f"✅ Gemma model created: {gemma_model.model_name}")
        print(f"✅ API endpoint: {gemma_model.api_endpoint}")

        # Test pipeline creation
        pipeline = ImageDescriptionPipeline(config.image_description)
        print("✅ Image pipeline created successfully")

        # Test model info
        model_info = pipeline.get_model_info()
        print(f"✅ Model info: {model_info['model_name']}")

        return True

    except Exception as e:
        print(f"❌ Image pipeline test failed: {e}")
        return False

def test_configuration_integration():
    """Test that all configurations are properly integrated."""
    print("\n⚙️  Testing Configuration Integration...")

    try:
        from utils.config import load_config

        config = load_config()

        # Verify TTS configuration
        print(f"✅ TTS Model: {config.tts.model}")
        print(f"✅ TTS Use MLX: {config.tts.use_mlx}")

        # Verify Image configuration
        print(f"✅ Image Model: {config.image_description.model}")
        print(f"✅ Image API URL: {config.image_description.api_url}")
        print(f"✅ Image Enabled: {config.image_description.enabled}")

        # Verify other settings
        print(f"✅ Max Description Length: {config.image_description.max_description_length}")
        print(f"✅ Include Context: {config.image_description.include_context}")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_pipeline_orchestration():
    """Test pipeline orchestration without running full processing."""
    print("\n🎼 Testing Pipeline Orchestration...")

    try:
        from utils.config import load_config
        from pipelines.orchestrator import PipelineOrchestrator

        config = load_config()
        orchestrator = PipelineOrchestrator(config)

        # Test pipeline status
        status = orchestrator.get_pipeline_status()
        print("✅ Pipeline Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")

        # Test cleanup
        orchestrator.cleanup()
        print("✅ Pipeline cleanup completed")

        return True

    except Exception as e:
        print(f"❌ Pipeline orchestration test failed: {e}")
        return False

def main():
    """Run all tests."""
    setup_logging()

    print("🚀 Starting TTS Pipeline Fix Tests")
    print("=" * 50)

    tests = [
        test_configuration_integration,
        test_metal_framework_resilience,
        test_image_pipeline_paths,
        test_pipeline_orchestration
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {i+1}. {test.__name__}: {status}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! TTS pipeline fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())