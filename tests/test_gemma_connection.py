#!/usr/bin/env python3
"""
Test script to verify Gemma-3n-e4b is running and responding via LM Studio.
"""

import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_lm_studio_connection():
    """Test basic connection to LM Studio API."""
    print("🔌 Testing LM Studio Connection...")

    try:
        import requests

        api_url = "http://127.0.0.1:1234"

        # Test if LM Studio is running
        response = requests.get(f"{api_url}/v1/models", timeout=5)

        if response.status_code == 200:
            models = response.json()
            available_models = [m.get('id', 'unknown') for m in models.get('data', [])]
            print(f"✅ LM Studio is running")
            print(f"📋 Available models: {len(available_models)}")

            # Look for Gemma models
            gemma_models = [m for m in available_models if 'gemma' in m.lower()]
            if gemma_models:
                print(f"🎯 Gemma models found: {gemma_models}")
                return True, gemma_models[0]  # Return first Gemma model
            else:
                print(f"⚠️  No Gemma models found in: {available_models}")
                return False, None
        else:
            print(f"❌ LM Studio connection failed: HTTP {response.status_code}")
            return False, None

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to LM Studio. Is it running on http://127.0.0.1:1234?")
        return False, None
    except requests.exceptions.Timeout:
        print("❌ Connection to LM Studio timed out")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error connecting to LM Studio: {e}")
        return False, None

def test_gemma_basic_response(model_name):
    """Test basic text generation with Gemma model."""
    print(f"\n💬 Testing Gemma Text Generation with model: {model_name}")

    try:
        import requests

        api_url = "http://127.0.0.1:1234"
        endpoint = f"{api_url}/v1/chat/completions"

        # Simple "Hello, world!" test
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, world! Please respond with a brief, friendly greeting."
                }
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }

        print("📤 Sending request to Gemma...")
        start_time = time.time()

        response = requests.post(
            endpoint,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )

        response_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']['content'].strip()
                usage = result.get('usage', {})

                print(f"✅ Gemma responded successfully!")
                print(f"📝 Response: '{message}'")
                print(f"⏱️  Response time: {response_time:.2f}s")
                print(f"🔢 Tokens used: {usage.get('total_tokens', 'unknown')}")

                return True, message
            else:
                print(f"❌ Invalid response format: {result}")
                return False, None
        else:
            print(f"❌ API request failed: HTTP {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False, None

    except requests.exceptions.Timeout:
        print("❌ Request to Gemma timed out (>30s)")
        return False, None
    except Exception as e:
        print(f"❌ Error testing Gemma: {e}")
        return False, None

def test_gemma_vision_capability(model_name):
    """Test if the model supports vision (image understanding)."""
    print(f"\n👁️  Testing Vision Capabilities with model: {model_name}")

    # Test 1: Simple synthetic image
    simple_test = test_simple_vision(model_name)

    # Test 2: Real Mars image
    mars_test = test_mars_image_description(model_name)

    return simple_test[0] or mars_test[0], simple_test[1] and mars_test[1]

def test_simple_vision(model_name):
    """Test with a simple synthetic red square."""
    print("\n🔴 Testing with simple red square...")

    try:
        import requests
        import base64
        from PIL import Image
        import io

        # Create a simple test image (red square)
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        api_url = "http://127.0.0.1:1234"
        endpoint = f"{api_url}/v1/chat/completions"

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What color is this image? Please respond with just the color name."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 20,
            "temperature": 0.1
        }

        response = requests.post(
            endpoint,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']['content'].strip().lower()
                print(f"👁️  Simple test result: '{message}'")

                if 'red' in message:
                    print("✅ Simple vision test passed!")
                    return True, True
                else:
                    print("⚠️  Simple vision test unclear")
                    return True, False

        print("❌ Simple vision test failed")
        return False, False

    except Exception as e:
        print(f"❌ Error in simple vision test: {e}")
        return False, False

def test_mars_image_description(model_name):
    """Test with the real Mars image for realistic image description."""
    print("\n🪐 Testing with Mars image for realistic description...")

    try:
        import requests
        import base64
        from pathlib import Path

        # Load the Mars image
        mars_image_path = Path(__file__).parent.parent / "examples" / "example_mars.jpg"

        if not mars_image_path.exists():
            print(f"⚠️  Mars image not found at {mars_image_path}")
            return False, False

        # Convert to base64
        with open(mars_image_path, 'rb') as img_file:
            img_data = img_file.read()
            img_b64 = base64.b64encode(img_data).decode('utf-8')

        api_url = "http://127.0.0.1:1234"
        endpoint = f"{api_url}/v1/chat/completions"

        # Prompt similar to what would be used in EPUB processing
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at describing images for audiobook narration. Generate brief, clear descriptions that work well when read aloud. Keep descriptions under 50 words. Focus on the most important visual elements."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image briefly for an audiobook listener. Provide a clear, concise description in under 50 words that captures the essential visual information."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }

        print("🚀 Sending Mars image to Gemma...")
        start_time = time.time()

        response = requests.post(
            endpoint,
            json=payload,
            timeout=45,  # Longer timeout for complex image
            headers={"Content-Type": "application/json"}
        )

        response_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                description = result['choices'][0]['message']['content'].strip()
                usage = result.get('usage', {})

                print(f"✅ Mars description generated!")
                print(f"📝 Description: '{description}'")
                print(f"⏱️  Response time: {response_time:.2f}s")
                print(f"🔢 Tokens used: {usage.get('total_tokens', 'unknown')}")

                # Check if description seems reasonable
                mars_keywords = ['mars', 'planet', 'red', 'orange', 'surface', 'sphere', 'round', 'celestial', 'space']
                description_lower = description.lower()
                keyword_matches = [kw for kw in mars_keywords if kw in description_lower]

                if keyword_matches:
                    print(f"🎯 Mars description quality: GOOD (found keywords: {keyword_matches})")
                    return True, True
                else:
                    print("⚠️  Mars description unclear but model responded")
                    return True, False
            else:
                print(f"❌ Invalid Mars response: {result}")
                return False, False
        else:
            print(f"❌ Mars vision test failed: HTTP {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False, False

    except Exception as e:
        print(f"❌ Error testing Mars image: {e}")
        return False, False

def main():
    """Run Gemma connection tests."""
    print("🚀 Gemma-3n-e4b LM Studio Connection Test")
    print("=" * 50)

    # Test 1: Basic LM Studio connection
    connected, model_name = test_lm_studio_connection()

    if not connected:
        print("\n❌ Cannot proceed - LM Studio is not accessible")
        print("\n💡 To fix this:")
        print("   1. Make sure LM Studio is running")
        print("   2. Verify it's listening on http://127.0.0.1:1234")
        print("   3. Load a Gemma model (e.g., google/gemma-3n-e4b)")
        return 1

    # Test 2: Basic text generation
    text_success, response = test_gemma_basic_response(model_name)

    if not text_success:
        print("\n❌ Text generation failed")
        print("\n💡 To fix this:")
        print("   1. Check that the model is fully loaded")
        print("   2. Verify model has enough memory/resources")
        print("   3. Try a different Gemma model variant")
        return 1

    # Test 3: Vision capability (if supported)
    vision_supported, vision_accurate = test_gemma_vision_capability(model_name)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  🔌 LM Studio Connection: {'✅ PASS' if connected else '❌ FAIL'}")
    print(f"  💬 Text Generation: {'✅ PASS' if text_success else '❌ FAIL'}")
    print(f"  👁️  Vision Support: {'✅ PASS' if vision_supported else '❌ FAIL'}")
    if vision_supported:
        print(f"  🎯 Vision Accuracy: {'✅ GOOD' if vision_accurate else '⚠️  UNCLEAR'}")
        print(f"  🪐 Mars Image Test: {'✅ INCLUDED' if vision_supported else '❌ SKIPPED'}")

    if connected and text_success:
        print(f"\n🎉 Success! Gemma model '{model_name}' is working via LM Studio")
        print("📋 Ready for EPUB image description tasks")

        if vision_supported:
            print("👁️  Vision capabilities confirmed - perfect for image descriptions!")
            if vision_accurate:
                print("🪐 Mars image test shows realistic description capabilities")
        else:
            print("⚠️  Vision capabilities unclear - may need different model for images")

        return 0
    else:
        print("\n❌ Tests failed - check LM Studio setup")
        return 1

if __name__ == "__main__":
    sys.exit(main())