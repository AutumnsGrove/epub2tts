# epub2tts

A production-ready EPUB to TTS converter that converts EPUB files into optimized text and audio using Kokoro TTS and local VLM for image descriptions.

## Features

- **Modern EPUB Processing**: Native EPUB handling with EbookLib (faster and more accurate than Pandoc)
- **Advanced Text Processing**: Modern NLP-based processing with spaCy, plus legacy regex fallback
- **Chapter Segmentation**: Intelligent chapter detection using TOC data and ML confidence scoring
- **TTS Integration**: High-quality audio generation using Kokoro TTS with MLX optimization
- **Local VLM Integration**: Image content description using local vision-language models (Gemma, LLaVA)
- **Split-Window Terminal UI**: Advanced real-time progress tracking with live stats and activity logs
- **Batch Processing**: Parallel processing of multiple files with comprehensive error handling
- **Resume Capability**: Smart resume functionality for interrupted processing
- **Flexible Output**: Support for text, SSML, and JSON formats with comprehensive metadata
- **Auto-loading Models**: Automatic TTS and VLM model detection and loading
- **Production Ready**: Comprehensive logging, error handling, and performance monitoring

## Quick Start

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Basic text extraction
uv run python scripts/process_epub.py book.epub

# Full pipeline with TTS
uv run python scripts/process_epub.py book.epub --tts --voice "bf_lily"

# Full pipeline with advanced UI
uv run python scripts/process_epub.py book.epub --tts --images --ui-mode split-window

# Batch processing
uv run python scripts/batch_convert.py ./ebooks/*.epub --parallel 4

# Alternative: Use the main CLI interface
uv run python src/cli.py convert book.epub --tts --voice "bf_lily"
uv run python src/cli.py batch ./ebooks/*.epub --parallel 4
uv run python src/cli.py test     # Test system setup
uv run python src/cli.py info book.epub  # Get EPUB information
```

## Installation

### Prerequisites

- Python 3.10+ (required for Kokoro TTS)
- UV (Python package manager)
- Pandoc (for legacy EPUB processing)
- FFmpeg (for audio processing)

### Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install pandoc ffmpeg

# macOS
brew install pandoc ffmpeg

# Windows (using chocolatey)
choco install pandoc ffmpeg
```

### Install Python Package

```bash
git clone https://github.com/AutumnsGrove/epub2tts.git
cd epub2tts

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Verify installation
uv run python scripts/process_epub.py --help
```

## Configuration

Create a custom configuration file:

```yaml
# config/custom_config.yaml
processing:
  epub_processor: "ebooklib"  # "ebooklib" (modern) or "pandoc" (legacy)
  temp_dir: "/tmp/epub2tts"

text_processing:
  processor_mode: "modern"  # "modern" (spacy+nlp), "legacy" (regex), "hybrid"
  spacy_model: "en_core_web_sm"

tts:
  voice: "bf_lily"
  speed: 1.1
  model_path: "./models/Kokoro-82M-8bit"
  use_mlx: true

image_description:
  enabled: true
  model: "gemma-3n-e4b"
  api_url: "http://127.0.0.1:1234"

ui:
  mode: "split-window"  # "classic" or "split-window"
  show_progress_bars: true

output:
  text_format: "plain"  # "plain", "ssml", "json"
  save_intermediate: true
  generate_toc: true
```

Use with:
```bash
uv run python scripts/process_epub.py book.epub -c config/custom_config.yaml
```

## Processing Modes

### Text Processing
- **Modern Mode** (default): Uses spaCy NLP for intelligent text processing and chapter detection
- **Legacy Mode**: Traditional regex-based cleaning for maximum compatibility
- **Hybrid Mode**: Combines both approaches for optimal results

### EPUB Processing
- **EbookLib** (default): Native Python EPUB handling, faster and more accurate
- **Pandoc**: Legacy processing mode for compatibility with older EPUBs

### User Interface
- **Classic Mode**: Traditional command-line progress bars
- **Split-Window Mode**: Advanced terminal UI with real-time stats, progress tracking, and activity logs

### Available Voices (Kokoro TTS)
- **bf_lily**: Female British English (default)
- **am_michael**: Male American English
- **bf_emma**: Female British English (alternative)
- **am_sarah**: Female American English

### VLM Models
- **gemma-3n-e4b**: Lightweight vision model (default)
- **llava**: More comprehensive but resource-intensive

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│ EPUB Input  │────▶│ EbookLib     │────▶│ Modern Text    │────▶│ Clean Text  │
└─────────────┘     │ + TOC        │     │ Pipeline       │     │ + Chapters  │
                    │ Extraction   │     │ (spaCy+NLP)    │     │   Output    │
                    └──────────────┘     └────────────────┘     └─────────────┘
                            │                                            │
                    ┌───────▼────────┐                         ┌────────▼────────┐
                    │ Image Pipeline │                         │  TTS Pipeline   │
                    │ (Gemma/LLaVA)  │                         │(Kokoro+MLX Opt) │
                    └────────────────┘                         └─────────────────┘
                            │                                            │
                    ┌───────▼────────┐                         ┌────────▼────────┐
                    │Image Desc Text │                         │  Audio Files    │
                    └────────────────┘                         │ + Merged Book   │
                                                               └─────────────────┘
```

## Development

### Running Tests

```bash
# All tests
uv run pytest tests/

# Unit tests only
uv run pytest tests/unit/

# With coverage
uv run pytest tests/ --cov=src --cov-report=html

# Test setup and dependencies
uv run python src/cli.py test
```

### Code Formatting

```bash
# Format Python code
uv run black .

# Check formatting
uv run black --check .

# Run linting
uv run flake8 src/ tests/

# Type checking
uv run mypy src/
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests: `uv run pytest tests/`
5. Format code: `uv run black .`
6. Commit changes: `git commit -m "feat: add amazing feature"`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Performance

- **Text extraction**: < 5 seconds for 100MB EPUB
- **Text cleaning**: < 10 seconds for 500KB text
- **TTS generation**: 2x faster than playback speed
- **Memory usage**: < 500MB for typical novel

## Command Reference

### Main CLI Commands
```bash
# Process single EPUB file
uv run python src/cli.py convert book.epub [OPTIONS]

# Batch process multiple files
uv run python src/cli.py batch *.epub [OPTIONS]

# Get EPUB information
uv run python src/cli.py info book.epub

# Validate EPUB file
uv run python src/cli.py validate book.epub

# Test system setup
uv run python src/cli.py test

# Show configuration
uv run python src/cli.py config --show-config
```

### Direct Script Access
```bash
# Process EPUB (with more examples in help)
uv run python scripts/process_epub.py book.epub [OPTIONS]

# Batch convert with advanced options
uv run python scripts/batch_convert.py *.epub [OPTIONS]
```

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

## API Reference

See [docs/API.md](docs/API.md) for detailed API documentation.