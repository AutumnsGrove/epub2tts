# epub2tts API Documentation

This document describes the API for using epub2tts programmatically.

## Core Classes

### EPUBProcessor

Main processor for EPUB to text conversion.

```python
from epub2tts.core.epub_processor import EPUBProcessor
from epub2tts.utils.config import load_config

# Initialize processor
config = load_config()
processor = EPUBProcessor(config)

# Process EPUB file
result = processor.process_epub(
    epub_path=Path("book.epub"),
    output_dir=Path("./output")
)

if result.success:
    print(f"Processed {len(result.chapters)} chapters")
    print(f"Text length: {len(result.text_content)} characters")
else:
    print(f"Processing failed: {result.error_message}")
```

### TextCleaner

Advanced text cleaning for TTS optimization.

```python
from epub2tts.core.text_cleaner import TextCleaner

# Initialize cleaner
cleaner = TextCleaner()

# Clean text
cleaned_text = cleaner.clean_text(raw_text)

# Segment into chapters
chapters = cleaner.segment_chapters(cleaned_text)

# Get cleaning statistics
stats = cleaner.get_cleaning_stats()
print(f"Removed {stats.characters_removed} characters")
```

### TTS Pipeline

Generate audio using Kokoro TTS.

```python
from epub2tts.pipelines.tts_pipeline import create_tts_pipeline
from epub2tts.utils.config import load_config

# Initialize TTS pipeline
config = load_config()
tts_pipeline = create_tts_pipeline(config.tts)

# Process single chunk
result = tts_pipeline.process_chunk(
    text="Hello, this is a test.",
    output_path="./output/test.wav",
    chunk_id="test_chunk"
)

# Process multiple chapters
chapters = [
    {"title": "Chapter 1", "content": "Chapter content..."},
    {"title": "Chapter 2", "content": "More content..."}
]

tts_results = tts_pipeline.process_chapters(
    chapters,
    output_dir=Path("./audio_output"),
    merge_final=True
)
```

### Image Description Pipeline

Generate descriptions for images using VLM.

```python
from epub2tts.pipelines.image_pipeline import create_image_pipeline
from epub2tts.utils.config import load_config

# Initialize image pipeline
config = load_config()
image_pipeline = create_image_pipeline(config.image_description)

# Process single image
description = image_pipeline.process_image(
    image_path="path/to/image.jpg",
    context="This image appears in chapter 1..."
)

print(f"Description: {description.description}")
print(f"Confidence: {description.confidence}")

# Process multiple images
image_list = [
    {"file_path": "image1.jpg", "context": "Context 1"},
    {"file_path": "image2.jpg", "context": "Context 2"}
]

result = image_pipeline.batch_process_images(image_list)
print(f"Processed {result.processed_images} images")
```

### Pipeline Orchestrator

Coordinate all processing pipelines.

```python
from epub2tts.pipelines.orchestrator import PipelineOrchestrator
from epub2tts.utils.config import load_config

# Initialize orchestrator
config = load_config()
orchestrator = PipelineOrchestrator(config)

# Process complete pipeline
result = orchestrator.process_epub_complete(
    epub_path=Path("book.epub"),
    output_dir=Path("./complete_output"),
    enable_tts=True,
    enable_images=True
)

print(f"Pipeline completed in {result.total_processing_time:.2f}s")
if result.tts_results:
    print(f"Generated audio: {result.tts_results['total_audio_duration']:.1f} minutes")
```

## Configuration

### Loading Configuration

```python
from epub2tts.utils.config import load_config, Config
from pathlib import Path

# Load default configuration
config = load_config()

# Load custom configuration
config = load_config(Path("custom_config.yaml"))

# Access configuration sections
print(f"TTS Model: {config.tts.model}")
print(f"Voice: {config.tts.voice}")
print(f"Speed: {config.tts.speed}")
```

### Custom Configuration

```python
from epub2tts.utils.config import Config, TTSConfig, ImageConfig

# Create custom configuration
config = Config()
config.tts = TTSConfig(
    model="kokoro",
    voice="en-US-female",
    speed=1.2,
    pitch=1.0
)

config.image_description = ImageConfig(
    enabled=True,
    model="llava-1.5-7b",
    max_description_length=150
)
```

## Error Handling

All main functions return result objects with success indicators:

```python
# Check for success
if result.success:
    # Process successful result
    process_result(result)
else:
    # Handle error
    print(f"Error: {result.error_message}")

# Exception handling
try:
    result = processor.process_epub(epub_path, output_dir)
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Logging

Configure logging for debugging:

```python
from epub2tts.utils.logger import setup_logging
import logging

# Basic logging
setup_logging(level=logging.INFO)

# Detailed logging with file output
setup_logging(
    level=logging.DEBUG,
    log_file=Path("./logs/epub2tts.log"),
    format_type="detailed"
)

# Performance logging
from epub2tts.utils.logger import PerformanceLogger

with PerformanceLogger("My operation"):
    # Your code here
    pass
```

## Advanced Usage

### Custom Text Cleaning Rules

```python
from epub2tts.core.text_cleaner import TextCleaner
from pathlib import Path

# Use custom regex patterns
cleaner = TextCleaner(rules_path=Path("custom_patterns.yaml"))

# Validate patterns
errors = cleaner.validate_patterns()
if errors:
    print("Pattern errors:", errors)
```

### Batch Processing

```python
from epub2tts.scripts.batch_convert import BatchProcessor
from epub2tts.utils.config import load_config

# Initialize batch processor
config = load_config()
batch_processor = BatchProcessor(config, max_workers=4)

# Process multiple files
epub_files = [Path("book1.epub"), Path("book2.epub")]
results = batch_processor.process_files(
    epub_files,
    output_base_dir=Path("./batch_output"),
    resume=False
)

# Check results
for result in results:
    if result.success:
        print(f"✅ {result.metadata.get('title', 'Unknown')}")
    else:
        print(f"❌ Error: {result.error_message}")
```

### Memory Management

```python
# Clean up resources when done
orchestrator.cleanup()
image_pipeline.cleanup()

# For large batches, process in chunks
def process_large_batch(epub_files, chunk_size=10):
    for i in range(0, len(epub_files), chunk_size):
        chunk = epub_files[i:i+chunk_size]
        # Process chunk
        results = process_chunk(chunk)
        # Clean up
        cleanup_resources()
```

## Integration Examples

### Web Service Integration

```python
from flask import Flask, request, jsonify
from epub2tts.pipelines.orchestrator import PipelineOrchestrator
from epub2tts.utils.config import load_config

app = Flask(__name__)
config = load_config()
orchestrator = PipelineOrchestrator(config)

@app.route('/process', methods=['POST'])
def process_epub():
    epub_file = request.files['epub']

    # Save uploaded file
    epub_path = Path(f"./uploads/{epub_file.filename}")
    epub_file.save(epub_path)

    # Process
    result = orchestrator.process_epub_complete(
        epub_path,
        Path(f"./outputs/{epub_path.stem}"),
        enable_tts=True
    )

    return jsonify({
        'success': result.epub_processing.success,
        'chapters': len(result.epub_processing.chapters),
        'audio_duration': result.tts_results.get('total_audio_duration', 0) if result.tts_results else 0
    })
```

### Custom Pipeline

```python
from epub2tts.core.epub_processor import EPUBProcessor
from epub2tts.pipelines.tts_pipeline import create_tts_pipeline
from epub2tts.utils.config import load_config

def custom_processing_pipeline(epub_path, output_dir):
    config = load_config()

    # Step 1: Extract text
    epub_processor = EPUBProcessor(config)
    epub_result = epub_processor.process_epub(epub_path, output_dir)

    if not epub_result.success:
        return epub_result

    # Step 2: Custom text processing
    custom_processed_chapters = []
    for chapter in epub_result.chapters:
        # Apply custom processing
        processed_content = custom_text_processor(chapter.content)
        chapter.content = processed_content
        custom_processed_chapters.append(chapter)

    # Step 3: Generate audio with custom settings
    tts_pipeline = create_tts_pipeline(config.tts)
    tts_results = tts_pipeline.process_chapters(
        [{"title": ch.title, "content": ch.content} for ch in custom_processed_chapters],
        output_dir / "custom_audio"
    )

    return {
        'text_result': epub_result,
        'tts_result': tts_results
    }
```