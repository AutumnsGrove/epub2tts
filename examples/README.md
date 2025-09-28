# Examples and Test Assets

This directory contains example files and test assets for the epub2tts project.

## Files

### Images
- **`example_mars.jpg`** - High-quality Mars image used for testing Gemma-3n-e4b vision capabilities
  - Source: NASA/space photography
  - Purpose: Tests realistic image description generation for audiobooks
  - Used in: `test_gemma_connection.py`

## Usage

### Testing Image Description
```bash
# Test Gemma vision capabilities with the Mars image
uv run python test_gemma_connection.py
```

### Using in Development
The Mars image serves as a realistic test case for:
- Vision model performance evaluation
- Description quality assessment
- TTS-optimized text generation
- Real-world EPUB image processing scenarios

## Test Results Example

When testing with `example_mars.jpg`, Gemma-3n-e4b typically generates descriptions like:

> "This image showcases the rusty, reddish-brown surface of Mars, a planet known for its distinctive color. The surface is covered in dusty terrain with darker patches of volcanic rock and lighter areas, likely dust deposits."

These descriptions are optimized for:
- ✅ Audiobook narration (flows well when read aloud)
- ✅ Brevity (under 50 words when configured)
- ✅ Accuracy (correctly identifies Mars, surface features)
- ✅ Context-appropriate language (suitable for various audiences)