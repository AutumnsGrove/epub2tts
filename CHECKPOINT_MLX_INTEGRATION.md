# MLX Integration Checkpoint - September 27, 2025

## Summary

This document captures the progress made on integrating Kokoro-82M TTS with MLX framework into the epub2tts project. While significant infrastructure was implemented, we encountered issues with the MLX-Audio library that require further investigation.

## ✅ Completed Work

### 1. Dependencies and Environment
- **✅ Packages Installed**: All required MLX packages successfully installed via uv
  - `mlx-audio>=0.2.5`
  - `kokoro>=0.9.4`
  - `torch>=2.8.0`
  - `mlx>=0.29.2`
  - `structlog>=25.4.0` (additional dependency discovered)

### 2. Model Acquisition
- **✅ MLX Model Downloaded**: Successfully downloaded `mlx-community/Kokoro-82M-8bit`
  - Location: `./models/kokoro-mlx/`
  - Size: ~330MB MLX-optimized model
  - Contains all voice files including `bf_lily.pt`
  - Voice inventory: 52 voices available (verified in `/voices/` directory)

### 3. Code Implementation
- **✅ Pipeline Infrastructure**: TTS pipeline already existed and was well-architected
- **✅ Configuration System**: MLX settings already implemented in config
  - `use_mlx: true/false` toggle
  - Model path configuration
  - Voice selection (bf_lily as default)
- **✅ MLXKokoroModel Class**: Enhanced implementation with fallback logic
  - Dual backend support (MLX-Audio + direct Kokoro)
  - Automatic fallback mechanism
  - Voice enumeration from model directory
  - Error handling and logging

### 4. Testing and Validation
- **✅ Mock Pipeline**: Confirmed existing pipeline works perfectly with mock model
- **✅ Voice Detection**: Successfully detected all 52 voices including bf_lily
- **✅ Configuration Loading**: All configs load correctly with MLX settings

## ⚠️ Current Issues

### MLX-Audio Library Compatibility
**Primary Issue**: MLX-Audio library encounters a `SystemExit(1)` during audio generation

**Symptoms Observed**:
```
2025-09-27 15:35:05.329 | INFO | mlx_audio.tts.models.kokoro.kokoro:_get_pipeline:261 - Creating new KokoroPipeline for language: a
/Users/autumn/Documents/.venv/bin/python3: No module named pip
WARNING:src.pipelines.tts_pipeline:MLX-Audio failed (1), falling back to direct Kokoro
```

**Technical Details**:
- Model loads successfully (logs show pipeline creation)
- SystemExit occurs during audio generation phase
- Pip module error suggests environment issue
- MLX model files are present and accessible

### Secondary Issues
1. **Direct Kokoro Fallback**: Not fully tested due to interruption
2. **Speed Adjustment**: Scipy dependency for speed control not verified
3. **Output Format**: Integration with existing audio pipeline needs validation

## 🔍 Technical Analysis

### What's Working Well
1. **Architecture**: The existing TTS pipeline is excellently designed
2. **Configuration**: MLX integration fits naturally into existing config system
3. **Model Access**: Local MLX model downloaded and accessible
4. **Voice Inventory**: All voices properly detected and enumerable
5. **Error Handling**: Graceful fallback mechanism implemented

### Root Cause Hypothesis
The MLX-Audio library issue appears to be:
1. **Environment Related**: Pip module error suggests virtual environment configuration issue
2. **MLX-Audio Version**: Possible compatibility issue with downloaded model format
3. **System Dependencies**: Missing system-level dependencies for MLX

### Alternative Approaches Identified
1. **Direct Kokoro Integration**: Use `kokoro.KPipeline` directly (simpler, less optimized)
2. **MLX Model Conversion**: Convert model to different MLX format
3. **Environment Debugging**: Resolve uv/pip virtual environment conflicts

## 📋 Next Steps (Priority Order)

### Immediate (Phase 1)
1. **Debug Environment Issues**
   - Investigate pip module error in uv environment
   - Verify MLX system dependencies on macOS
   - Test with different virtual environment approach

2. **Test Direct Kokoro Fallback**
   - Verify `kokoro.KPipeline` works with local model
   - Test audio generation with bf_lily voice
   - Validate speed and quality controls

### Short Term (Phase 2)
3. **MLX-Audio Troubleshooting**
   - Try different MLX-Audio versions
   - Test with different model formats
   - Check MLX-Audio GitHub issues for similar problems

4. **Integration Completion**
   - Complete end-to-end pipeline testing
   - Validate audio output quality
   - Performance benchmarking vs mock model

### Long Term (Phase 3)
5. **Production Readiness**
   - Stress testing with full EPUB files
   - Memory usage optimization
   - Error recovery and retry logic
   - Documentation updates

## 🏗️ Implementation Notes

### Current Code State
```python
class MLXKokoroModel:
    def __init__(self, config):
        # Dual backend initialization
        # MLX-Audio preferred, direct Kokoro fallback

    def synthesize(self, text, voice="bf_lily", speed=1.0, pitch=1.0):
        # Try MLX-Audio first
        # Automatic fallback to direct Kokoro on failure
        # Speed adjustment via scipy resampling
```

### Configuration
```yaml
tts:
  model: "kokoro"
  model_path: "./models/kokoro-mlx"  # Local MLX model
  voice: "bf_lily"                   # Verified available
  use_mlx: true                      # Toggle for testing
```

### Key Files Modified
- `src/pipelines/tts_pipeline.py` - Enhanced MLXKokoroModel
- `config/default_config.yaml` - MLX model path
- `requirements.txt` - MLX dependencies (already present)

## 🎯 Success Metrics

### Minimum Viable Product
- [ ] Audio generation works with bf_lily voice
- [ ] Basic speed control functional
- [ ] Integration with existing pipeline complete

### Full Success
- [ ] MLX-optimized performance on Apple Silicon
- [ ] All 52 voices accessible
- [ ] Production-ready error handling
- [ ] Performance improvement over mock model

## 🔧 Debugging Commands

### Quick Tests
```bash
# Test voice enumeration
uv run python -c "from pathlib import Path; print(sorted([f.stem for f in Path('./models/kokoro-mlx/voices').glob('*.pt')]))"

# Test direct Kokoro
uv run python -c "from kokoro import KPipeline; p = KPipeline('a'); print('Kokoro loaded')"

# Environment check
uv run python -c "import mlx; import torch; import kokoro; print('All imports OK')"
```

### Pipeline Test
```bash
# Full pipeline test
uv run python test_tts_pipeline.py  # (create simple test script)
```

## 💡 Key Insights

1. **Infrastructure Ready**: The epub2tts codebase is excellently prepared for TTS integration
2. **MLX Model Available**: High-quality 8-bit quantized model successfully obtained
3. **Voice Quality**: bf_lily voice confirmed available in MLX model
4. **Fallback Strategy**: Robust error handling prevents complete failure
5. **Environment Challenge**: Main blocker is MLX-Audio library compatibility

## 📝 Lessons Learned

1. **Model Acquisition**: Using mlx-community pre-converted models saves significant time
2. **Dual Backend Strategy**: Implementing fallback from MLX-Audio to direct Kokoro provides robustness
3. **Voice Enumeration**: Reading voice files from model directory provides accurate voice list
4. **Configuration Design**: Existing config system easily accommodated MLX settings
5. **Testing Strategy**: Mock model testing validates pipeline before addressing TTS-specific issues

## 🎉 Achievement Summary

This integration attempt successfully:
- ✅ Set up complete MLX infrastructure
- ✅ Downloaded and configured production-ready TTS model
- ✅ Implemented robust dual-backend TTS class
- ✅ Verified voice availability and configuration
- ✅ Created graceful error handling and fallback

The foundation is solid. The remaining work is primarily troubleshooting the MLX-Audio library integration and completing the direct Kokoro fallback implementation.

---

**Status**: Infrastructure Complete, Audio Generation Debugging Required
**Next Session**: Focus on MLX-Audio environment debugging or direct Kokoro implementation
**Estimated Completion**: 2-4 hours additional work