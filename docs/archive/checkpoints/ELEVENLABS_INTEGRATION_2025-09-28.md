# ElevenLabs TTS Integration Implementation

**Date**: 2025-09-28
**Status**: ✅ COMPLETED
**Scope**: Add ElevenLabs TTS API support as alternative to Kokoro TTS

## 📋 Implementation Summary

Successfully integrated ElevenLabs TTS API as an optional high-quality text-to-speech engine alongside the existing Kokoro TTS system. Users can now choose between local Kokoro TTS (default) or cloud-based ElevenLabs TTS by simply adding an API key.

## 🚀 Key Features Implemented

### 1. **Secrets Management System**
- **Location**: `src/utils/secrets.py`
- **Template**: `secrets_template.json`
- **Configuration**: Updated `.gitignore` to protect `secrets.json`
- **Features**:
  - Secure API key loading from `secrets.json`
  - Environment variable fallback support
  - Validation and availability checking
  - Clear error messaging for setup issues

### 2. **ElevenLabs TTS Pipeline**
- **Location**: `src/pipelines/elevenlabs_tts.py`
- **Class**: `ElevenLabsTTSPipeline`
- **Features**:
  - Full ElevenLabs API integration
  - Intelligent text chunking (2500 char limit)
  - Rate limiting and retry logic
  - Voice management and selection
  - Progress tracking integration
  - Error handling with graceful fallbacks

### 3. **Enhanced Configuration System**
- **Updated**: `src/utils/config.py` - Added ElevenLabs settings to `TTSConfig`
- **Updated**: `config/default_config.yaml` - Added comprehensive ElevenLabs configuration
- **New Settings**:
  - `engine`: Choose between "kokoro" and "elevenlabs"
  - `elevenlabs_voice_id`: Voice selection (default: George)
  - `elevenlabs_model`: Model selection (default: eleven_multilingual_v2)
  - Voice tuning: stability, similarity_boost, style
  - Performance: max_chunk_chars, retry settings

### 4. **Smart TTS Factory Pattern**
- **Updated**: `src/pipelines/tts_pipeline.py`
- **Function**: `create_tts_pipeline()`
- **Logic**:
  - Auto-detects available engines based on API key presence
  - Respects explicit user engine selection
  - Graceful fallback to Kokoro if ElevenLabs fails
  - Clear logging of engine selection reasoning

### 5. **Comprehensive Testing**
- **Location**: `tests/test_elevenlabs_integration.py`
- **Coverage**:
  - Secrets management functionality
  - ElevenLabs pipeline initialization and processing
  - Factory pattern engine selection
  - Configuration system integration
  - Error handling and fallback scenarios
  - Mocked tests to avoid requiring API keys

### 6. **Updated Dependencies**
- **Added**: `elevenlabs>=1.0.0` to both `pyproject.toml` and `requirements.txt`
- **Compatibility**: Works with existing dependencies

## 🛠️ Usage Instructions

### Quick Setup

1. **Get ElevenLabs API Key**:
   - Sign up at [ElevenLabs](https://elevenlabs.io/)
   - Generate API key from dashboard

2. **Configure API Key**:
   ```bash
   cp secrets_template.json secrets.json
   # Edit secrets.json and add your API key
   ```

3. **Choose Engine** (Optional):
   ```yaml
   # In config/default_config.yaml or local config
   tts:
     engine: "elevenlabs"  # or "kokoro" for default
   ```

### API Key Setup

**Option 1: secrets.json (Recommended)**
```json
{
  "elevenlabs_api_key": "your-api-key-here",
  "comment": "Keep this file private"
}
```

**Option 2: Environment Variable**
```bash
export ELEVENLABS_API_KEY="your-api-key-here"
```

### Configuration Options

```yaml
tts:
  # Engine selection
  engine: "elevenlabs"  # "kokoro" (default) or "elevenlabs"

  # ElevenLabs settings
  elevenlabs_voice_id: "JBFqnCBsd6RMkjVDRZzb"  # George (professional male)
  elevenlabs_model: "eleven_multilingual_v2"    # Recommended for quality
  elevenlabs_stability: 0.75                    # Voice consistency (0.0-1.0)
  elevenlabs_similarity_boost: 0.75             # Voice accuracy (0.0-1.0)
  elevenlabs_style: 0.0                        # Expression level (0.0-1.0)
  elevenlabs_max_chunk_chars: 2500             # Text chunking size
```

### Available Voices

Common ElevenLabs voices included in defaults:
- **JBFqnCBsd6RMkjVDRZzb**: George (professional male)
- **21m00Tcm4TlvDq8ikWAM**: Rachel (clear female)
- **AZnzlk1XvdvUeBnXmlld**: Domi (confident female)
- **EXAVITQu4vr4xnSDxMaL**: Bella (expressive female)

Use `pipeline.get_voice_info()` to see all available voices.

### Available Models

- **eleven_multilingual_v2**: Best quality, supports 29 languages
- **eleven_flash_v2_5**: Ultra-low latency, supports 32 languages
- **eleven_turbo_v2_5**: Balanced quality and speed

## 🔄 Engine Selection Logic

The system automatically selects the best available TTS engine:

1. **User explicitly sets `engine: "elevenlabs"`**:
   - ✅ API key found → Use ElevenLabs
   - ❌ No API key → Fall back to Kokoro + warning

2. **User explicitly sets `engine: "kokoro"`**:
   - ✅ Always use Kokoro (respects user choice)

3. **Auto-detection (default)**:
   - ✅ ElevenLabs API key found → Use ElevenLabs
   - ❌ No API key → Use Kokoro (default)

## 📊 Technical Implementation Details

### Text Processing
- **Character Limit**: 2500 characters per API request (configurable)
- **Chunking Strategy**: Intelligent sentence-boundary splitting
- **SSML Support**: Preserves pause and emphasis markers
- **Preprocessing**: Removes TTS-unfriendly patterns

### Error Handling
- **Rate Limiting**: Exponential backoff with retry logic
- **API Errors**: Graceful handling of quota, auth, and network issues
- **Fallback**: Automatic fallback to Kokoro on ElevenLabs failures
- **Logging**: Detailed error messages and status reporting

### Performance
- **Sequential Processing**: Respects ElevenLabs rate limits
- **Progress Tracking**: Integration with existing progress system
- **Memory Efficient**: Streams audio data without large buffers
- **Caching**: No local caching (respects API ToS)

## 🧪 Testing Strategy

### Test Categories
1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: End-to-end pipeline testing
3. **Mock Tests**: API interaction testing without real keys
4. **Configuration Tests**: Config loading and validation

### Running Tests
```bash
# Run ElevenLabs-specific tests
uv run pytest tests/test_elevenlabs_integration.py -v

# Run all tests
uv run pytest tests/ -v
```

## 🔒 Security Considerations

### API Key Protection
- ✅ `secrets.json` excluded from git via `.gitignore`
- ✅ No hardcoded API keys in source code
- ✅ Environment variable fallback support
- ✅ Clear setup instructions and templates

### API Usage
- ✅ Respects ElevenLabs rate limits
- ✅ No unauthorized voice cloning or model training
- ✅ Character usage tracking for cost monitoring
- ✅ Graceful handling of quota limits

## 📈 Benefits & Impact

### For Users
- **Choice**: Local (Kokoro) vs Cloud (ElevenLabs) TTS options
- **Quality**: Access to professional-grade voices
- **Flexibility**: Easy switching between engines
- **Compatibility**: Works with existing epub2tts workflows

### For Developers
- **Extensible**: Factory pattern makes adding new engines easy
- **Robust**: Comprehensive error handling and fallbacks
- **Testable**: Full test coverage with mocking support
- **Maintainable**: Clean separation of concerns

## 🔮 Future Enhancements

### Potential Improvements
1. **Voice Cloning**: Support for custom voice creation
2. **Streaming**: Real-time audio streaming for long texts
3. **Cost Optimization**: Smart chunking to minimize API calls
4. **Quality Profiles**: Preset configurations for different use cases
5. **Batch Processing**: Optimized processing for multiple books

### Other TTS Engines
The factory pattern makes it easy to add additional engines:
- Azure Cognitive Services Speech
- Google Cloud Text-to-Speech
- Amazon Polly
- OpenAI TTS

## 📝 Files Modified/Created

### New Files
- ✅ `src/utils/secrets.py` - Secrets management utilities
- ✅ `src/pipelines/elevenlabs_tts.py` - ElevenLabs TTS pipeline
- ✅ `secrets_template.json` - API key setup template
- ✅ `tests/test_elevenlabs_integration.py` - Comprehensive test suite
- ✅ `checkpoints/ELEVENLABS_INTEGRATION_2025-09-28.md` - This documentation

### Modified Files
- ✅ `src/utils/config.py` - Added ElevenLabs settings to TTSConfig
- ✅ `config/default_config.yaml` - Added ElevenLabs configuration section
- ✅ `src/pipelines/tts_pipeline.py` - Enhanced factory function
- ✅ `.gitignore` - Added secrets.json exclusion
- ✅ `pyproject.toml` - Added elevenlabs dependency
- ✅ `requirements.txt` - Added elevenlabs dependency

## ✅ Verification Checklist

- [x] **Secrets Management**: Secure API key handling implemented
- [x] **ElevenLabs Integration**: Full pipeline implementation completed
- [x] **Configuration System**: Enhanced with ElevenLabs settings
- [x] **Factory Pattern**: Smart engine selection implemented
- [x] **Dependencies**: ElevenLabs package added to both config files
- [x] **Testing**: Comprehensive test suite created
- [x] **Documentation**: Complete implementation documentation
- [x] **Security**: API keys protected from version control
- [x] **Backward Compatibility**: Existing Kokoro functionality preserved
- [x] **Error Handling**: Graceful fallbacks and clear error messages

## 🎯 Conclusion

The ElevenLabs TTS integration has been successfully implemented, providing users with a professional-grade text-to-speech option while maintaining full backward compatibility with the existing Kokoro TTS system. The implementation follows security best practices, includes comprehensive testing, and uses a flexible factory pattern that makes future TTS engine additions straightforward.

Users can now enjoy high-quality voice synthesis by simply adding an ElevenLabs API key, while developers benefit from a well-architected, extensible TTS system.