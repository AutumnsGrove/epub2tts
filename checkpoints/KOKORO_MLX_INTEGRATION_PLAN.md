# Kokoro-82M MLX Integration Plan

## Overview

This document outlines the comprehensive plan for integrating Kokoro-82M TTS model with MLX framework into the epub2tts project for optimized speech synthesis.

## Project Current State

### Existing Architecture
- **TTS Pipeline**: `src/pipelines/tts_pipeline.py` with mock implementation
- **Configuration**: `src/utils/config.py` with TTS settings
- **Voice Target**: "bf_lily" (as specified)
- **Structure**: Well-organized pipeline ready for real TTS integration

### Current Mock Implementation
The project has a `MockKokoroModel` class that generates sine wave audio for testing. This will be replaced with the actual Kokoro-82M implementation.

## Research Summary

### MLX-Audio Framework
- **Purpose**: TTS/STS library built on Apple's MLX framework
- **Optimization**: Designed for efficient speech synthesis on Apple Silicon
- **Performance**: Fast inference on M-series Apple chips
- **Features**:
  - Multiple language support
  - Voice customization options
  - Speech speed control (0.5x to 2.0x)
  - Model quantization for performance optimization

### Kokoro-82M Model Specifications
- **Parameters**: 82 million (lightweight but high-quality)
- **License**: Apache 2.0 (commercial use allowed)
- **Architecture**: StyleTTS 2 + ISTFTNet (no diffusion/encoder)
- **Languages**: 8 languages, 54 voices
- **Performance**: #1 in TTS Spaces Arena, outperforms larger models
- **Cost**: Under $1 per million characters
- **Training**: ~$1000 total cost, few hundred hours of audio

### Voice Configuration
- **Target Voice**: "bf_lily" (British female)
- **Language Code**: 'a' (American English, but bf_lily is British)
- **Default Settings**: Speed 1.0, standard pitch

## Integration Strategy

### Two Implementation Approaches

#### Option A: MLX-Audio Integration (Recommended)
```python
from mlx_audio.tts.generate import generate_audio

class MLXKokoroModel:
    def __init__(self, config):
        self.generate_func = generate_audio
        self.model_path = "hexgrad/Kokoro-82M"
        self.voice = "bf_lily"

    def synthesize(self, text, voice="bf_lily", speed=1.0, pitch=1.0):
        return self.generate_func(
            text=text,
            model_path=self.model_path,
            voice=voice,
            speed=speed
        )
```

#### Option B: Direct Kokoro Integration
```python
from kokoro import KPipeline

class DirectKokoroModel:
    def __init__(self, config):
        self.pipeline = KPipeline(lang_code='a')
        self.voice = "bf_lily"

    def synthesize(self, text, voice="bf_lily", speed=1.0, pitch=1.0):
        generator = self.pipeline(text, voice=voice)
        return np.array(list(generator))
```

### Recommended Approach
**Option A (MLX-Audio)** is recommended for:
- Better Apple Silicon optimization
- Simpler API interface
- Built-in performance optimizations
- Future-proof architecture

## Required Dependencies

### New Requirements to Add
```bash
# Add to requirements.txt
mlx-audio>=0.1.0
kokoro>=0.9.2
torch>=2.0.0
mlx>=0.18.0
```

### Installation Commands
```bash
pip install mlx-audio
pip install kokoro>=0.9.2
pip install torch>=2.0.0
pip install mlx>=0.18.0
```

## Code Changes Required

### 1. Update `requirements.txt`
Add the new dependencies listed above.

### 2. Modify `src/pipelines/tts_pipeline.py`

#### Replace MockKokoroModel
```python
class MLXKokoroModel:
    """Real Kokoro model using MLX framework for optimized inference."""

    def __init__(self, config: TTSConfig):
        """Initialize MLX Kokoro model."""
        try:
            from mlx_audio.tts.generate import generate_audio
            self.generate_func = generate_audio
            self.config = config
            self.model_path = "hexgrad/Kokoro-82M"
            self.voice = "bf_lily"  # Default voice as specified
            logger.info("Initialized MLX Kokoro model successfully")
        except ImportError as e:
            logger.error(f"Failed to import MLX audio: {e}")
            raise RuntimeError("MLX audio not available")

    def synthesize(
        self,
        text: str,
        voice: str = "bf_lily",
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> np.ndarray:
        """
        Generate audio using MLX-optimized Kokoro model.

        Args:
            text: Text to synthesize
            voice: Voice to use (default: bf_lily)
            speed: Speech speed multiplier
            pitch: Pitch adjustment (note: may not be supported)

        Returns:
            Audio data as numpy array
        """
        try:
            # Generate audio using MLX-Audio
            audio_data = self.generate_func(
                text=text,
                model_path=self.model_path,
                voice=voice,
                speed=speed
            )

            # Convert to numpy array if needed
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)

            return audio_data.astype(np.float32)

        except Exception as e:
            logger.error(f"MLX Kokoro synthesis failed: {e}")
            raise

    def get_available_voices(self) -> List[str]:
        """Get list of available voices."""
        # Note: This would need to be implemented based on MLX-Audio API
        return ["bf_lily", "af_heart", "bf_emma", "am_adam"]  # Common voices
```

#### Update Model Initialization
```python
def _initialize_model(self) -> None:
    """Initialize the Kokoro TTS model."""
    try:
        logger.info(f"Loading Kokoro model: {self.config.model}")

        # Try to load MLX Kokoro model
        try:
            self.model = MLXKokoroModel(self.config)
            logger.info("Using MLX-optimized Kokoro model")
        except (ImportError, RuntimeError) as e:
            logger.warning(f"MLX Kokoro not available: {e}")
            logger.info("Falling back to mock TTS for development")
            self.model = MockKokoroModel(self.config)

        self.is_initialized = True

    except Exception as e:
        logger.error(f"Failed to initialize Kokoro model: {e}")
        raise RuntimeError(f"Cannot initialize TTS model: {e}")
```

### 3. Update `src/utils/config.py`

#### Add MLX-Specific Configuration
```python
@dataclass
class TTSConfig:
    # Existing fields...

    # MLX-specific settings
    use_mlx: bool = True
    model_path: str = "hexgrad/Kokoro-82M"
    voice: str = "bf_lily"  # Default to bf_lily as specified
    quantization: bool = False  # Enable for faster inference
    mlx_cache_dir: Optional[str] = None

    # Performance settings
    batch_size: int = 1
    max_workers: int = 4
```

### 4. Update Default Configuration Files

#### Update default voice in configuration
Ensure all configuration files use "bf_lily" as the default voice.

## Implementation Roadmap

### Phase 1: Foundation Setup (1-2 hours)

#### 1.1 Update Dependencies
```bash
# Update requirements.txt
echo "mlx-audio>=0.1.0" >> requirements.txt
echo "kokoro>=0.9.2" >> requirements.txt
echo "torch>=2.0.0" >> requirements.txt
echo "mlx>=0.18.0" >> requirements.txt

# Install dependencies
pip install -r requirements.txt
```

#### 1.2 Test MLX-Audio Installation
```python
# Quick test script
from mlx_audio.tts.generate import generate_audio

# Test with bf_lily voice
test_audio = generate_audio(
    text="Hello, this is a test of the bf_lily voice.",
    model_path="hexgrad/Kokoro-82M",
    voice="bf_lily",
    speed=1.0
)
print(f"Test audio shape: {test_audio.shape}")
```

#### 1.3 Update Configuration
- Modify `src/utils/config.py` to include MLX settings
- Set default voice to "bf_lily"
- Add MLX-specific configuration options

### Phase 2: Core Integration (2-3 hours)

#### 2.1 Replace Mock Implementation
- Update `KokoroTTSPipeline` in `src/pipelines/tts_pipeline.py`
- Replace `MockKokoroModel` with `MLXKokoroModel`
- Ensure backward compatibility with existing API
- Add proper error handling and fallback to mock

#### 2.2 Voice Configuration
- Hardcode "bf_lily" as the default voice throughout
- Update voice handling in pipeline methods
- Test voice parameter passing

#### 2.3 Integration Testing
- Test basic text-to-speech functionality
- Verify audio output format and quality
- Test with sample text chunks

### Phase 3: Testing & Optimization (1-2 hours)

#### 3.1 Integration Testing
```bash
# Test with sample EPUB
python scripts/process_epub.py sample.epub --tts --voice "bf_lily"

# Test batch processing
python scripts/batch_convert.py ./test_files/*.epub --parallel 2
```

#### 3.2 Performance Tuning
- Add MLX-specific optimizations
- Implement batch processing improvements
- Add quantization options for faster inference
- Profile memory usage and inference time

#### 3.3 Error Handling
- Add MLX-specific error handling
- Implement graceful fallback to mock model
- Add logging for performance metrics

### Phase 4: Production Readiness (1 hour)

#### 4.1 Update Documentation
- Update README with MLX requirements
- Document new voice options and MLX benefits
- Add troubleshooting section for MLX issues

#### 4.2 Final Testing
- End-to-end pipeline testing with real EPUB files
- Performance benchmarking vs mock implementation
- Memory usage profiling
- Audio quality verification

#### 4.3 Configuration Validation
- Ensure all config files use proper defaults
- Test configuration loading and validation
- Verify voice parameter handling

## Expected Benefits

### Performance Improvements
- **Inference Speed**: 2-5x faster on Apple Silicon vs CPU-only TTS
- **Memory Efficiency**: MLX optimizations reduce memory footprint
- **Batch Processing**: Improved throughput for multiple chapters
- **Local Processing**: No network dependencies

### Quality Improvements
- **Audio Quality**: Superior quality vs mock implementation
- **Voice Consistency**: Professional-grade bf_lily voice
- **Natural Speech**: StyleTTS 2 architecture for human-like speech
- **Pronunciation**: Better handling of complex text

### Cost Benefits
- **No API Costs**: Eliminate cloud TTS service fees
- **Scalability**: Process unlimited text without usage charges
- **Reliability**: No rate limits or service outages
- **Privacy**: All processing happens locally

## Compatibility Notes

### Apple Silicon (Recommended)
- **Optimal Performance**: M1/M2/M3 chips with MLX optimization
- **Memory Efficiency**: Unified memory architecture benefits
- **Fast Inference**: Hardware-accelerated neural network operations

### Intel Macs
- **Reduced Performance**: MLX benefits limited on Intel
- **CPU Fallback**: Will work but slower than Apple Silicon
- **Memory Usage**: Higher memory requirements vs Apple Silicon

### Linux/Windows
- **Limited MLX Support**: May require additional setup
- **Alternative Options**: Consider direct Kokoro integration
- **Performance**: Standard CPU/GPU performance

## Troubleshooting

### Common Issues

#### MLX Installation Issues
```bash
# If MLX fails to install
pip install --upgrade pip
pip install mlx-audio --no-cache-dir

# On Intel Macs
pip install mlx-audio --force-reinstall
```

#### Model Download Issues
```bash
# Manually download model if auto-download fails
huggingface-cli download hexgrad/Kokoro-82M
```

#### Memory Issues
```python
# Enable quantization for memory efficiency
config.quantization = True
config.batch_size = 1  # Reduce batch size
```

### Performance Optimization Tips

#### For Apple Silicon
- Enable MLX optimizations
- Use appropriate batch sizes (2-4)
- Monitor memory usage during processing

#### For Intel/Other Platforms
- Consider direct Kokoro integration
- Reduce batch sizes
- Monitor CPU usage and temperature

## Testing Strategy

### Unit Tests
- Test MLXKokoroModel initialization
- Test audio synthesis functionality
- Test voice parameter handling
- Test error handling and fallbacks

### Integration Tests
- Test full pipeline with MLX integration
- Test batch processing with multiple chapters
- Test audio file merging and output formats
- Test configuration loading and validation

### Performance Tests
- Benchmark inference speed vs mock
- Memory usage profiling
- Batch processing throughput testing
- Audio quality assessment

## Future Enhancements

### Potential Improvements
- **Multiple Voices**: Support for additional voices beyond bf_lily
- **Voice Cloning**: Custom voice training capabilities
- **Streaming**: Real-time audio generation for long texts
- **SSML Support**: Advanced speech markup language features

### Advanced Features
- **Emotion Control**: Emotional speech synthesis
- **Speed Variations**: Dynamic speed changes within text
- **Pronunciation Dictionary**: Custom pronunciation handling
- **Language Detection**: Automatic language switching

## Conclusion

This integration plan provides a comprehensive roadmap for replacing the mock TTS implementation with a production-ready Kokoro-82M + MLX solution. The plan maintains backward compatibility while delivering significant improvements in audio quality, processing speed, and cost efficiency.

The phased approach ensures minimal disruption to the existing codebase while providing clear milestones for implementation progress. With an estimated 4-6 hours of implementation time, this integration will transform the epub2tts project into a high-quality, cost-effective audiobook production tool.