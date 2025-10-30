# epub2tts

A production-ready EPUB to TTS converter that converts EPUB files into optimized text and audio using multiple TTS engines (Kokoro, ElevenLabs, Hume AI) and local VLM for image descriptions.

## Features

- **Modern EPUB Processing**: Production-ready EPUB parsing with OmniParser (8.7x faster than Pandoc)
- **Advanced Text Processing**: Modern NLP-based processing with spaCy, plus legacy regex fallback
- **Chapter Segmentation**: Intelligent chapter detection using TOC data and ML confidence scoring
- **Multi-Engine TTS Integration**: Support for three TTS engines:
  - **Kokoro TTS**: Local, high-quality audio with MLX optimization
  - **ElevenLabs**: Premium cloud-based voices with natural inflection
  - **Hume AI**: Ultra-low latency (<200ms), emotion-aware synthesis with multilingual support (11 languages)
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

# Full pipeline with Kokoro TTS (local)
uv run python scripts/process_epub.py book.epub --tts --voice "bf_lily"

# Full pipeline with ElevenLabs TTS (cloud)
uv run python scripts/process_epub.py book.epub --tts --engine elevenlabs --voice "Rachel"

# Full pipeline with Hume AI TTS (ultra-low latency)
uv run python scripts/process_epub.py book.epub --tts --engine hume --voice "Female English Actor"

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
- OmniParser (EPUB parsing - included as dependency)
- FFmpeg (for audio processing)

### Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows (using chocolatey)
choco install ffmpeg
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
  temp_dir: "/tmp/epub2tts"

text_processing:
  processor_mode: "modern"  # "modern" (spacy+nlp), "legacy" (regex), "hybrid"
  spacy_model: "en_core_web_sm"

tts:
  engine: "kokoro"  # "kokoro", "elevenlabs", or "hume"
  voice: "bf_lily"
  speed: 1.1
  model_path: "./models/Kokoro-82M-8bit"
  use_mlx: true

# Kokoro TTS settings (local engine)
kokoro:
  voice: "bf_lily"
  speed: 1.1
  model_path: "./models/Kokoro-82M-8bit"
  use_mlx: true

# ElevenLabs settings (cloud engine)
elevenlabs:
  api_key: "${ELEVENLABS_API_KEY}"  # Set via environment variable
  voice: "Rachel"
  model: "eleven_multilingual_v2"
  stability: 0.5
  similarity_boost: 0.75

# Hume AI settings (ultra-low latency engine)
hume:
  api_key: "${HUME_API_KEY}"  # Set via environment variable
  voice: "Female English Actor"
  language: "en"  # en, es, fr, de, it, pt, ru, ja, ko, hi, ar
  model: "octave-2"  # Latest model (40% faster, 50% lower cost)
  streaming: false

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
- **OmniParser**: Production-ready EPUB parser with native TOC support and high-accuracy chapter detection (8.7x faster than legacy Pandoc)

### User Interface
- **Classic Mode**: Traditional command-line progress bars
- **Split-Window Mode**: Advanced terminal UI with real-time stats, progress tracking, and activity logs

### Available Voices

#### Kokoro TTS (Local)
- **bf_lily**: Female British English (default)
- **am_michael**: Male American English
- **bf_emma**: Female British English (alternative)
- **am_sarah**: Female American English

#### ElevenLabs (Cloud - requires API key)
- **Rachel**: Female American English (conversational)
- **Adam**: Male American English (deep)
- **Bella**: Female American English (soft)
- **Antoni**: Male American English (warm)
- Custom voice cloning available

#### Hume AI (Cloud - requires API key)
Ultra-low latency (<200ms) with emotion-aware synthesis:
- **Female English Actor**: Expressive female English voice
- **Male English Actor**: Expressive male English voice
- **Female Spanish Actor**: Expressive female Spanish voice
- **Male Spanish Actor**: Expressive male Spanish voice
- Supports 11 languages: en, es, fr, de, it, pt, ru, ja, ko, hi, ar
- Voice cloning support available
- 40% faster than previous generation (Octave 1)
- 50% lower cost than Octave 1

### VLM Models
- **gemma-3n-e4b**: Lightweight vision model (default)
- **llava**: More comprehensive but resource-intensive

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│ EPUB Input  │────▶│ OmniParser   │────▶│ Modern Text    │────▶│ Clean Text  │
└─────────────┘     │ + TOC        │     │ Pipeline       │     │ + Chapters  │
                    │ Extraction   │     │ (spaCy+NLP)    │     │   Output    │
                    └──────────────┘     └────────────────┘     └─────────────┘
                            │                                            │
                    ┌───────▼────────┐                         ┌────────▼────────┐
                    │ Image Pipeline │                         │  TTS Pipeline   │
                    │ (Gemma/LLaVA)  │                         │   (Multi-Eng)   │
                    └────────────────┘                         └─────────────────┘
                            │                                            │
                    ┌───────▼────────┐                         ┌────────▼────────┐
                    │Image Desc Text │                         │ ┌─────────────┐ │
                    └────────────────┘                         │ │Kokoro (MLX) │ │
                                                               │ │ ElevenLabs  │ │
                                                               │ │  Hume AI    │ │
                                                               │ └─────────────┘ │
                                                               │  Audio Files    │
                                                               │ + Merged Book   │
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

### TTS Engine Examples

#### Kokoro TTS (Local)
```bash
# Default local TTS
uv run python scripts/process_epub.py book.epub --tts

# With specific voice
uv run python scripts/process_epub.py book.epub --tts --voice "bf_lily"

# With speed adjustment
uv run python scripts/process_epub.py book.epub --tts --voice "am_michael" --speed 1.2
```

#### ElevenLabs TTS (Cloud)
```bash
# Basic ElevenLabs usage (requires ELEVENLABS_API_KEY)
uv run python scripts/process_epub.py book.epub --tts --engine elevenlabs --voice "Rachel"

# With custom model and settings
uv run python scripts/process_epub.py book.epub --tts --engine elevenlabs --voice "Adam" --model "eleven_turbo_v2"
```

#### Hume AI TTS (Cloud)
```bash
# Basic Hume usage (requires HUME_API_KEY)
uv run python scripts/process_epub.py book.epub --tts --engine hume

# With specific voice
uv run python scripts/process_epub.py book.epub --tts --engine hume --voice "Female English Actor"

# With different language
uv run python scripts/process_epub.py book.epub --tts --engine hume --voice "Male Spanish Actor" --language es

# With streaming mode for ultra-low latency
uv run python scripts/process_epub.py book.epub --tts --engine hume --streaming

# French audiobook
uv run python scripts/process_epub.py livre.epub --tts --engine hume --language fr

# Japanese audiobook
uv run python scripts/process_epub.py book.epub --tts --engine hume --language ja
```

### API Key Setup
```bash
# Set up ElevenLabs API key
export ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"

# Set up Hume AI API key
export HUME_API_KEY="your_hume_api_key_here"

# Or add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
echo 'export ELEVENLABS_API_KEY="your_key_here"' >> ~/.bashrc
echo 'export HUME_API_KEY="your_key_here"' >> ~/.bashrc

# Or use a secrets.json file (see Configuration section)
```

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

## API Reference

See [docs/API.md](docs/API.md) for detailed API documentation.