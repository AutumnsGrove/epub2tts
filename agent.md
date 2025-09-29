# epub2tts Agent Reference Guide

A comprehensive quick reference for the epub2tts pipeline - converts EPUB files to optimized text and audio using Kokoro TTS and local VLM for image descriptions.

## 🚀 Quick Start

### Basic Commands

```bash
# Install dependencies
uv sync

# Text extraction only
uv run python scripts/process_epub.py book.epub

# Full TTS pipeline
uv run python scripts/process_epub.py book.epub --tts --voice "bf_lily"

# Advanced UI with image processing
uv run python scripts/process_epub.py book.epub --tts --images --ui-mode split-window

# Batch processing
uv run python scripts/batch_convert.py ./ebooks/*.epub --parallel 4

# Alternative CLI interface
uv run python src/cli.py convert book.epub --tts --voice "bf_lily"
uv run python src/cli.py test  # Test system setup
```

### System Test
```bash
# Verify installation and dependencies
uv run python src/cli.py test
```

## 📁 Project Architecture

### Core Components
```
epub2tts/
├── scripts/                    # Main entry points
│   ├── process_epub.py        # Single file processing
│   └── batch_convert.py       # Batch processing
├── src/
│   ├── cli.py                 # Main CLI interface
│   ├── core/                  # Core processing
│   │   ├── epub_processor.py  # Main orchestrator
│   │   ├── ebooklib_processor.py  # Modern EPUB handling
│   │   ├── pandoc_wrapper.py  # Legacy EPUB processing
│   │   └── text_cleaner.py    # Text cleaning pipeline
│   ├── pipelines/             # Processing pipelines
│   │   ├── tts_pipeline.py    # Kokoro TTS integration
│   │   ├── elevenlabs_tts.py  # ElevenLabs TTS integration
│   │   ├── image_pipeline.py  # VLM image descriptions
│   │   └── orchestrator.py    # Pipeline coordination
│   ├── ui/                    # User interfaces
│   │   ├── terminal_ui.py     # Split-window interface
│   │   └── progress_tracker.py # Progress tracking
│   └── utils/                 # Utilities
│       ├── config.py          # Configuration management
│       ├── logger.py          # Logging utilities
│       └── secrets.py         # API key management
├── config/
│   ├── default_config.yaml    # Default settings
│   └── regex_patterns.yaml    # Text cleaning patterns
└── tests/                     # Test suite
```

### Data Flow
```
EPUB → EbookLib → Modern Text Pipeline → Clean Text + Chapters
  ↓                     ↓                     ↓
Images → VLM Pipeline → Image Descriptions    ↓
                                          TTS Pipeline → Audio Files
```

## ⚙️ Configuration

### Key Config Locations
- **Main Config**: `config/default_config.yaml`
- **Custom Config**: Pass with `-c custom_config.yaml`
- **API Keys**: `secrets.json` (create from template)

### Essential Settings

```yaml
# EPUB Processing
processing:
  epub_processor: "ebooklib"  # or "pandoc" for legacy
  temp_dir: "/tmp/epub2tts"

# Text Processing
text_processing:
  processor_mode: "modern"    # "modern", "legacy", or "hybrid"
  spacy_model: "en_core_web_sm"

# TTS Engine Selection
tts:
  engine: "kokoro"           # or "elevenlabs"
  voice: "bf_lily"           # Kokoro voices
  model_path: "./models/Kokoro-82M-8bit"
  use_mlx: true             # Enable MLX optimization

# ElevenLabs (requires API key)
  elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
  elevenlabs_model: "eleven_multilingual_v2"

# Image Processing
image_description:
  enabled: true
  model: "gemma-3n-e4b"
  api_url: "http://127.0.0.1:1234"

# UI Mode
ui:
  mode: "split-window"      # or "classic"
```

## 🎤 TTS Engines

### Kokoro TTS (Default - Local)
- **Pros**: Free, local, fast, good quality
- **Setup**: Download models to `./models/Kokoro-82M-8bit`
- **Voices**: `bf_lily`, `am_michael`, `bf_emma`, `am_sarah`
- **Requirements**: MLX framework (macOS Metal optimization)

### ElevenLabs TTS (Cloud)
- **Pros**: Highest quality, multiple languages
- **Setup**: Add `elevenlabs_api_key` to `secrets.json`
- **Cost**: Paid API service
- **Voices**: 100+ voices, custom voice cloning

### Engine Selection
```bash
# Force Kokoro
uv run python scripts/process_epub.py book.epub --tts

# Force ElevenLabs (requires API key)
# Set engine: "elevenlabs" in config or use custom config
```

## 🖼️ Image Processing

### VLM Integration
- **Purpose**: Describe images in EPUBs for accessibility
- **Default Model**: Gemma-3n-e4b (lightweight)
- **Alternative**: LLaVA (more comprehensive)
- **Setup**: Local VLM server on port 1234

### Configuration
```yaml
image_description:
  enabled: true              # Enable/disable image processing
  model: "gemma-3n-e4b"      # or "llava"
  api_url: "http://127.0.0.1:1234"
  include_context: true      # Add surrounding text context
```

## 📝 Common Workflows

### 1. Quick Text Extraction
```bash
# Extract and clean text only
uv run python scripts/process_epub.py book.epub --no-tts --no-images
```

### 2. Full Audiobook Creation
```bash
# Complete pipeline with TTS and image descriptions
uv run python scripts/process_epub.py book.epub \
  --tts \
  --voice "bf_lily" \
  --images \
  --ui-mode split-window \
  --chapters
```

### 3. Batch Processing
```bash
# Process multiple files in parallel
uv run python scripts/batch_convert.py \
  ./books/*.epub \
  --parallel 4 \
  --tts \
  --output-dir ./output
```

### 4. Custom Configuration
```bash
# Use custom settings
uv run python scripts/process_epub.py book.epub \
  -c config/my_settings.yaml \
  --tts
```

### 5. Resume Interrupted Processing
```bash
# Resume from checkpoint
uv run python scripts/process_epub.py book.epub --resume --tts
```

## 🔧 Development & Testing

### Key Files for Agents
- **Main Orchestrator**: `src/core/epub_processor.py`
- **TTS Pipeline**: `src/pipelines/tts_pipeline.py`
- **Config System**: `src/utils/config.py`
- **CLI Interface**: `scripts/process_epub.py`

### Running Tests
```bash
# All tests
uv run pytest tests/

# Specific test types
uv run pytest tests/unit/
uv run pytest tests/integration/

# TTS-specific tests
uv run python tests/test_simple_mlx.py
uv run python tests/test_elevenlabs_simple.py
```

### Code Quality
```bash
# Format code
uv run black .

# Type checking
uv run mypy src/

# Linting
uv run flake8 src/ tests/
```

## 🔍 Troubleshooting

### Common Issues

#### MLX/Kokoro Issues
```bash
# Test MLX installation
uv run python tests/test_simple_mlx.py

# Check model availability
ls -la models/Kokoro-82M-8bit/

# Force CPU fallback (disable MLX)
# Set use_mlx: false in config
```

#### ElevenLabs Issues
```bash
# Test API key
uv run python tests/test_elevenlabs_simple.py

# Check secrets.json
cat secrets.json  # Should contain elevenlabs_api_key
```

#### EPUB Processing Issues
```bash
# Try different processors
# Set epub_processor: "pandoc" for legacy EPUBs

# Check EPUB validity
uv run python src/cli.py validate book.epub
```

### Performance Tips
- Use `--parallel 4` for batch processing
- Enable split-window UI for progress tracking
- Set appropriate `chunk_size` in config
- Use local Kokoro for fastest processing

## 🔑 API Key Management

### Secrets.json Template
```json
{
  "elevenlabs_api_key": "sk-...",
  "anthropic_api_key": "sk-ant-...",
  "comment": "Add your API keys here. This file should be kept private."
}
```

### Environment Variables (Fallback)
```bash
export ELEVENLABS_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 📊 Output Formats

### Text Formats
- **Plain**: Clean text with chapter breaks
- **SSML**: Speech Synthesis Markup Language
- **JSON**: Structured data with metadata

### Audio Formats
- **WAV**: Uncompressed (default)
- **MP3**: Compressed format

### Directory Structure
```
output/
├── book_name/
│   ├── text/
│   │   ├── book_name.txt
│   │   └── chapters/
│   ├── audio/
│   │   ├── audiobook.wav
│   │   └── chapters/
│   └── metadata/
│       ├── toc.json
│       └── processing_stats.json
```

---

**Version**: 0.1.0
**Last Updated**: 2025-09-28
**Dependencies**: Python 3.10+, UV, Pandoc, FFmpeg