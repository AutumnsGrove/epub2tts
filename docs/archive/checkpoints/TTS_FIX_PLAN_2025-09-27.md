# TTS Pipeline Fix Plan - September 27, 2025

## Executive Summary

This document outlines a comprehensive plan to fix critical issues in the epub2tts TTS pipeline, specifically addressing Metal framework errors, image processing path conflicts, and MLX-Audio integration problems discovered during full pipeline testing.

## Issues Identified

### 1. Critical: Metal Framework Error 🚨
**Error**: `[_MTLCommandBuffer addCompletedHandler:]:1011: failed assertion 'Completed handler provided after commit call'`

**Root Cause Analysis**:
- Occurs during MLX TTS processing when using Apple Silicon optimizations
- Metal framework resource management conflict in concurrent operations
- Likely caused by improper cleanup of GPU resources between TTS chunks
- MLX framework may not be thread-safe in current implementation

**Impact**:
- Complete TTS pipeline failure
- No audio generation despite successful text processing
- Inconsistent behavior across different text lengths

### 2. High Priority: Image Pipeline Path Issues 🖼️
**Symptoms**:
- `[Errno 2] No such file or directory` errors for image files
- Images extracted but paths become stale before processing
- Temp directory cleanup conflicts with image description pipeline

**Root Cause Analysis**:
- Two separate temp directories created during EPUB processing
- Image extraction uses different temp path than image description pipeline
- Race condition between file extraction and processing
- Premature cleanup of temporary media directories

**Impact**:
- 0/64 images successfully processed despite extraction
- Failed image descriptions integration
- Incomplete pipeline output

### 3. Medium Priority: MLX-Audio File Handling 💾
**Issues**:
- MLX-Audio returns `None` instead of audio arrays
- File-based output detection unreliable
- Temporary file cleanup timing issues
- Inconsistent audio data format handling

**Impact**:
- Fallback to direct Kokoro required
- Performance degradation
- Potential file system clutter

## Detailed Fix Strategy

### Phase 1: Metal Framework Stability (Priority 1)

#### 1.1 Disable Concurrent MLX Operations
```python
# In MLXKokoroModel.synthesize()
if self.use_mlx_audio:
    # Ensure sequential processing for MLX operations
    # Add resource cleanup between calls
    try:
        # Clear any existing Metal resources
        import gc
        gc.collect()

        # Process with explicit resource management
        audio_data = self.generate_func(...)
    finally:
        # Explicit cleanup
        gc.collect()
```

#### 1.2 Implement Metal Resource Management
- Add proper MLX context management
- Implement resource pooling for repeated operations
- Add explicit GPU memory cleanup between chunks
- Implement retry logic with resource reset

#### 1.3 Sequential Processing Fallback
```python
class MLXKokoroModel:
    def __init__(self, config):
        # Force sequential processing for MLX
        self.force_sequential = True
        self.max_retries = 3
```

### Phase 2: Image Pipeline Fix (Priority 2)

#### 2.1 Persistent Image Storage
```python
def _save_results(self, ..., temp_media_dir):
    # Copy images BEFORE any cleanup
    if temp_media_dir and temp_media_dir.exists():
        images_dir = output_dir / f"{base_name}_images"
        images_dir.mkdir(exist_ok=True)

        # Copy all media files immediately
        media_files = list(temp_media_dir.glob("**/*"))
        image_paths = []

        for media_file in media_files:
            if media_file.is_file():
                dest_file = images_dir / media_file.name
                shutil.copy2(media_file, dest_file)
                image_paths.append(dest_file)

        # Update image_info with new paths
        for info in image_info:
            # Update paths to point to copied images
            info['local_path'] = images_dir / Path(info['path']).name
```

#### 2.2 Fix Image Description Pipeline Integration
```python
class PipelineOrchestrator:
    def process_epub_complete(self, ...):
        # Process images AFTER they're copied to permanent location
        if enable_images and self.image_pipeline:
            # Wait for image copying to complete
            self._ensure_images_copied(epub_result, output_dir)

            # Update image paths before processing
            updated_image_info = self._update_image_paths(
                epub_result.image_info,
                output_dir
            )

            # Process with corrected paths
            image_result = self.image_pipeline.batch_process_images(
                updated_image_info,
                parallel=True
            )
```

#### 2.3 Eliminate Race Conditions
- Implement proper dependency ordering
- Add file existence validation before processing
- Implement proper temp directory lifecycle management

### Phase 3: MLX-Audio Robustness (Priority 3)

#### 3.1 File-Based Output Handling
```python
def synthesize(self, text, voice="bf_lily", speed=1.0, pitch=1.0):
    if self.use_mlx_audio:
        # Create dedicated output directory
        output_dir = Path("./temp_audio")
        output_dir.mkdir(exist_ok=True)

        try:
            # Generate with specific output path
            output_file = output_dir / f"audio_{hash(text)}.wav"

            audio_data = self.generate_func(
                text=text,
                model_path=self.model_path,
                voice=voice,
                speed=speed,
                output_path=str(output_file)  # Explicit output control
            )

            # Load from file if returned None
            if audio_data is None and output_file.exists():
                import soundfile as sf
                audio_data, _ = sf.read(str(output_file))
                output_file.unlink()  # Clean up immediately

        finally:
            # Cleanup any orphaned files
            self._cleanup_temp_audio(output_dir)
```

#### 3.2 Robust Fallback Mechanism
```python
class MLXKokoroModel:
    def __init__(self, config):
        self.fallback_attempts = 0
        self.max_fallback_attempts = 2

    def synthesize(self, text, voice="bf_lily", speed=1.0, pitch=1.0):
        for attempt in range(self.max_fallback_attempts + 1):
            try:
                if attempt == 0 and self.use_mlx_audio:
                    return self._try_mlx_audio(text, voice, speed, pitch)
                else:
                    return self._try_direct_kokoro(text, voice, speed, pitch)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_fallback_attempts:
                    raise
```

### Phase 4: Comprehensive Error Handling

#### 4.1 Metal-Specific Error Handling
```python
def _handle_metal_error(self, error):
    """Handle Metal framework specific errors."""
    if "MTLCommandBuffer" in str(error):
        logger.error("Metal framework error detected, switching to CPU fallback")
        self.use_mlx_audio = False
        # Clear GPU resources
        self._cleanup_metal_resources()
        return True
    return False
```

#### 4.2 Progressive Degradation
```python
class KokoroTTSPipeline:
    def __init__(self, config):
        self.degradation_level = 0  # 0=MLX, 1=Direct, 2=Mock

    def _initialize_model(self):
        try:
            if self.degradation_level == 0:
                self.model = MLXKokoroModel(self.config)
            elif self.degradation_level == 1:
                self.model = DirectKokoroModel(self.config)
            else:
                self.model = MockKokoroModel(self.config)
        except Exception as e:
            self.degradation_level += 1
            if self.degradation_level <= 2:
                logger.warning(f"Degrading to level {self.degradation_level}")
                self._initialize_model()
            else:
                raise
```

## Implementation Timeline

### Week 1: Critical Fixes
- **Day 1-2**: Metal framework error resolution
- **Day 3-4**: Image pipeline path fixes
- **Day 5**: Integration testing

### Week 2: Robustness & Testing
- **Day 1-2**: MLX-Audio file handling improvements
- **Day 3-4**: Comprehensive error handling
- **Day 5**: End-to-end testing

### Week 3: Optimization & Documentation
- **Day 1-2**: Performance optimization
- **Day 3-4**: Documentation updates
- **Day 5**: Production testing

## Testing Strategy

### Unit Tests
```python
def test_metal_resource_cleanup():
    """Test proper Metal resource management."""

def test_image_path_persistence():
    """Test image paths remain valid throughout pipeline."""

def test_mlx_audio_fallback():
    """Test fallback mechanisms work correctly."""
```

### Integration Tests
```python
def test_full_pipeline_stability():
    """Test complete pipeline with error injection."""

def test_concurrent_processing():
    """Test pipeline under concurrent load."""
```

### Performance Tests
- Memory usage profiling during TTS
- GPU resource utilization monitoring
- File I/O performance analysis

## Risk Mitigation

### High Risk: Metal Framework Instability
**Mitigation**:
- Implement immediate fallback to CPU-only processing
- Add comprehensive resource monitoring
- Create isolated Metal operations

### Medium Risk: File System Race Conditions
**Mitigation**:
- Implement file locking mechanisms
- Add retry logic with exponential backoff
- Create atomic file operations

### Low Risk: Performance Degradation
**Mitigation**:
- Benchmark before/after changes
- Implement performance monitoring
- Add configurable optimization levels

## Success Metrics

### Functional Requirements
- [ ] TTS pipeline completes without Metal errors
- [ ] All images successfully processed and described
- [ ] Audio files generated for all text chunks
- [ ] No file system race conditions

### Performance Requirements
- [ ] TTS processing time < 2x baseline
- [ ] Memory usage remains stable
- [ ] No temporary file leaks

### Quality Requirements
- [ ] Audio quality maintained across all fixes
- [ ] Error recovery works reliably
- [ ] Logging provides sufficient debugging info

## Monitoring & Maintenance

### Error Tracking
```python
class TTSErrorTracker:
    def __init__(self):
        self.metal_errors = 0
        self.file_errors = 0
        self.fallback_count = 0

    def track_error(self, error_type, error_msg):
        # Log and track error patterns
```

### Performance Monitoring
- Add TTS processing time metrics
- Monitor GPU memory usage
- Track fallback frequency

### Health Checks
- Pre-flight Metal framework validation
- File system permission checks
- Model availability verification

## Conclusion

This comprehensive fix plan addresses the critical TTS pipeline issues while maintaining backward compatibility and providing robust error handling. The phased approach ensures minimal disruption while systematically resolving each identified problem.

The implementation prioritizes stability over performance initially, with optimization opportunities identified for future iterations. Comprehensive testing and monitoring ensure the fixes work reliably across different system configurations and input types.

---

**Status**: Ready for Implementation
**Priority**: High - Critical for production TTS functionality
**Estimated Effort**: 2-3 weeks full implementation
**Dependencies**: MLX framework, Kokoro TTS library, Metal framework
**Risk Level**: Medium - Well-understood issues with clear solutions

If you need further context please use Context7 mcp server for up-to-date information. ALso, use subagents as needed. And we will be using google/gemma-3n-e4b served via LM Studio (http://127.0.0.1:1234) for our image analysis. we need to extract out the content so we can then create a brief summarsy to then add into the text BEFORE the tts pipeline. Use gemma-3n-e4b also for the image description generations. ensure they are not long, but not unrecognizable. ask any follow up question before tackling this plan.