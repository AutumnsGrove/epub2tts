# Troubleshooting Guide

This guide helps resolve common issues with epub2tts.

## Installation Issues

### Pandoc Not Found

**Error**: `PandocError: Pandoc not found at 'pandoc'`

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install pandoc

# macOS
brew install pandoc

# Windows
choco install pandoc

# Or download from: https://pandoc.org/installing.html
```

**Alternative**: Specify custom Pandoc path in config:
```yaml
processing:
  pandoc_path: "/usr/local/bin/pandoc"
```

### FFmpeg Not Found

**Error**: Audio processing fails with missing FFmpeg

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### Python Dependencies

**Error**: Import errors or missing modules

**Solution**:
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# For specific issues, install individually:
pip install pypandoc pyyaml regex beautifulsoup4
```

## EPUB Processing Issues

### Invalid EPUB Format

**Error**: `PandocError: Invalid EPUB format`

**Solutions**:
1. **Validate EPUB**: Use epub2tts validation:
   ```bash
   python scripts/process_epub.py book.epub --validate-only
   ```

2. **Repair with Calibre**:
   - Open EPUB in Calibre
   - Convert to EPUB again
   - This often fixes format issues

3. **Check file integrity**:
   ```bash
   # Check if file is corrupted
   file book.epub
   unzip -t book.epub
   ```

### Empty or Corrupted Content

**Error**: `PandocError: Pandoc returned empty content`

**Solutions**:
1. **Check EPUB structure**:
   ```bash
   # Extract and examine EPUB
   unzip book.epub -d extracted/
   ls -la extracted/
   ```

2. **Try different conversion**:
   ```bash
   # Test with Pandoc directly
   pandoc book.epub -t markdown -o test.md
   ```

3. **Use alternative source**: Try re-downloading the EPUB file

### Large File Issues

**Error**: Processing hangs or runs out of memory

**Solutions**:
1. **Increase memory limits**:
   ```yaml
   processing:
     max_parallel_jobs: 1  # Reduce parallelism

   chapters:
     max_words_per_chunk: 2000  # Smaller chunks
   ```

2. **Process in parts**: Use chapter splitting

3. **Check available memory**:
   ```bash
   free -h  # Linux
   vm_stat  # macOS
   ```

## Text Cleaning Issues

### Regex Pattern Errors

**Error**: Pattern compilation fails

**Solution**:
```bash
# Test regex patterns
python -c "
from src.core.text_cleaner import TextCleaner
cleaner = TextCleaner()
errors = cleaner.validate_patterns()
print('Errors:', errors)
"
```

**Fix invalid patterns**:
1. Check `config/regex_patterns.yaml`
2. Escape special characters: `[`, `]`, `(`, `)`, `{`, `}`, `\`
3. Test patterns online: https://regex101.com/

### Unexpected Text Removal

**Issue**: Important content gets removed

**Solution**:
1. **Review cleaning rules**:
   ```yaml
   cleaning:
     remove_footnotes: false  # Keep footnotes
     remove_page_numbers: false  # Keep page numbers
   ```

2. **Test on sample text**:
   ```python
   from src.core.text_cleaner import TextCleaner
   cleaner = TextCleaner()

   sample = "Your problematic text here"
   cleaned = cleaner.clean_text(sample)
   print(f"Original: {sample}")
   print(f"Cleaned: {cleaned}")
   ```

3. **Disable specific patterns**: Comment out problematic patterns in `regex_patterns.yaml`

## TTS Issues

### Model Loading Fails

**Error**: `RuntimeError: Cannot initialize TTS model`

**Solutions**:
1. **Check model path**:
   ```yaml
   tts:
     model_path: "./models/kokoro"  # Verify this exists
   ```

2. **Download models**: Ensure Kokoro TTS models are installed

3. **Test with mock model**: For development, mock model should work

4. **Check dependencies**:
   ```bash
   pip install torch torchaudio  # If using PyTorch models
   pip install soundfile pydub
   ```

### Audio Generation Fails

**Error**: TTS processing fails for specific text

**Solutions**:
1. **Check text preprocessing**:
   ```python
   # Test text preprocessing
   from src.pipelines.tts_pipeline import KokoroTTSPipeline
   pipeline = KokoroTTSPipeline(config.tts)
   processed = pipeline._preprocess_text("Your problematic text")
   print(f"Processed: {processed}")
   ```

2. **Reduce text length**: Split long chapters

3. **Check special characters**: Remove or replace problematic Unicode

### Audio Quality Issues

**Issue**: Generated audio sounds poor

**Solutions**:
1. **Adjust TTS settings**:
   ```yaml
   tts:
     speed: 1.0      # Try different speeds
     pitch: 1.0      # Adjust pitch
     sample_rate: 22050  # Higher quality
   ```

2. **Check output format**:
   ```yaml
   tts:
     output_format: "wav"  # Higher quality than MP3
   ```

## Image Processing Issues

### VLM Model Loading Fails

**Error**: Image description pipeline fails to initialize

**Solutions**:
1. **Disable image processing** (temporary):
   ```yaml
   image_description:
     enabled: false
   ```

2. **Check model availability**:
   ```bash
   # For transformers-based models
   pip install transformers torch
   ```

3. **Use mock model**: For testing, mock model should work

4. **Check GPU availability**:
   ```python
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   ```

### Poor Image Descriptions

**Issue**: Generated descriptions are not helpful

**Solutions**:
1. **Adjust description length**:
   ```yaml
   image_description:
     max_description_length: 200  # Longer descriptions
   ```

2. **Provide better context**:
   ```yaml
   image_description:
     include_context: true
   ```

3. **Check image quality**: Ensure images are clear and not corrupted

### Memory Issues with Images

**Error**: Out of memory during image processing

**Solutions**:
1. **Reduce parallelism**:
   ```yaml
   processing:
     max_parallel_jobs: 1
   ```

2. **Process images sequentially** in code

3. **Resize large images**: Images are automatically resized to 1024px max

## Performance Issues

### Slow Processing

**Issue**: Processing takes too long

**Solutions**:
1. **Increase parallelism**:
   ```yaml
   processing:
     max_parallel_jobs: 8  # Use more CPU cores
   ```

2. **Use SSD storage**: Faster disk I/O

3. **Monitor resource usage**:
   ```bash
   htop  # Monitor CPU/memory usage
   iotop  # Monitor disk I/O
   ```

4. **Profile bottlenecks**:
   ```bash
   python -m cProfile scripts/process_epub.py book.epub
   ```

### High Memory Usage

**Issue**: Process uses too much RAM

**Solutions**:
1. **Reduce chunk sizes**:
   ```yaml
   chapters:
     max_words_per_chunk: 1000
   ```

2. **Process sequentially**:
   ```yaml
   processing:
     max_parallel_jobs: 1
   ```

3. **Clear cache regularly**:
   ```python
   # In code
   import gc
   gc.collect()
   ```

## Configuration Issues

### Invalid Configuration

**Error**: Configuration validation fails

**Solution**:
```bash
# Test configuration
python -c "
from src.utils.config import load_config
try:
    config = load_config()
    print('Configuration valid')
except Exception as e:
    print(f'Configuration error: {e}')
"
```

**Common fixes**:
- Check YAML syntax
- Verify numeric ranges (speed: 0.5-2.0, pitch: 0.5-2.0)
- Ensure required fields are present

### Path Issues

**Error**: File or directory not found

**Solutions**:
1. **Use absolute paths**:
   ```yaml
   processing:
     temp_dir: "/tmp/epub2tts"
     pandoc_path: "/usr/local/bin/pandoc"
   ```

2. **Check permissions**:
   ```bash
   ls -la /path/to/directory
   chmod 755 /path/to/directory
   ```

3. **Create directories**:
   ```bash
   mkdir -p /path/to/output/directory
   ```

## CLI Issues

### Import Errors

**Error**: `ModuleNotFoundError` when running scripts

**Solution**:
```bash
# Run from project root
cd /path/to/epub2tts
python scripts/process_epub.py book.epub

# Or install package
pip install -e .
epub2tts convert book.epub
```

### Permission Denied

**Error**: Cannot write to output directory

**Solutions**:
```bash
# Check permissions
ls -la output/
chmod 755 output/

# Use different output directory
python scripts/process_epub.py book.epub -o ~/Documents/epub_output
```

## Debugging

### Enable Debug Logging

```bash
python scripts/process_epub.py book.epub --verbose
```

**Or in code**:
```python
from src.utils.logger import setup_logging
import logging

setup_logging(level=logging.DEBUG)
```

### Test System Setup

```bash
python scripts/process_epub.py test-setup
```

### Check Dependencies

```bash
# Test individual components
python -c "from src.core.pandoc_wrapper import verify_pandoc; print(verify_pandoc())"
python -c "from src.core.text_cleaner import TextCleaner; print('TextCleaner OK')"
python -c "from src.utils.config import load_config; print('Config OK')"
```

## Getting Help

### Check Logs

Default log location: `./logs/epub2tts.log`

### Report Issues

When reporting issues, include:

1. **System information**:
   ```bash
   python --version
   pandoc --version
   pip list | grep -E "(epub2tts|pypandoc|pyyaml)"
   ```

2. **Error message** (full traceback)

3. **Configuration** (sanitized)

4. **Sample EPUB** (if possible)

5. **Steps to reproduce**

### Minimal Test Case

```python
# Minimal reproduction script
from pathlib import Path
from src.core.epub_processor import EPUBProcessor
from src.utils.config import load_config

config = load_config()
processor = EPUBProcessor(config)

try:
    result = processor.process_epub(
        Path("test.epub"),
        Path("./test_output")
    )
    print(f"Success: {result.success}")
    if not result.success:
        print(f"Error: {result.error_message}")
except Exception as e:
    print(f"Exception: {e}")
```

Save this as `debug_test.py` and run with your problematic EPUB file.