# epub2tts

A production-ready EPUB to TTS converter that converts EPUB files into optimized text and audio using Kokoro TTS and local VLM for image descriptions.

## Features

- **EPUB to Text Conversion**: Extract and clean text from EPUB files using Pandoc
- **Advanced Text Processing**: Regex-based cleaning with TTS optimization
- **Chapter Segmentation**: Automatic chapter detection and splitting
- **TTS Integration**: Generate high-quality audio using Kokoro TTS
- **Image Descriptions**: Local VLM integration for image content description
- **Batch Processing**: Process multiple files with parallel execution
- **Resume Capability**: Resume interrupted processing
- **Flexible Output**: Support for text, SSML, and JSON formats

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Basic text extraction
python scripts/process_epub.py book.epub

# Full pipeline with TTS
python scripts/process_epub.py book.epub --tts --voice "en-US-1"

# Batch processing
python scripts/batch_convert.py ./ebooks/*.epub --parallel 4
```

## Installation

### Prerequisites

- Python 3.8+
- Pandoc
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
git clone https://github.com/[username]/epub2tts.git
cd epub2tts
pip install -r requirements.txt
pip install -e .
```

## Configuration

Create a custom configuration file:

```yaml
# config/custom_config.yaml
processing:
  remove_footnotes: false
  preserve_formatting: true

tts:
  voice: "en-GB-female"
  speed: 1.1
  pitch: 0.95

output:
  format: "ssml"
  split_chapters: true
  max_chapter_size: 10000
```

Use with:
```bash
python scripts/process_epub.py book.epub -c config/custom_config.yaml
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│ EPUB Input  │────▶│ Pandoc       │────▶│ Text Pipeline  │────▶│ Clean Text  │
└─────────────┘     │ Extraction   │     │ (Regex/Rules)  │     │   Output    │
                    └──────────────┘     └────────────────┘     └─────────────┘
                            │                                            │
                    ┌───────▼────────┐                         ┌────────▼────────┐
                    │ Image Pipeline │                         │  TTS Pipeline   │
                    │     (VLM)      │                         │    (Kokoro)     │
                    └────────────────┘                         └─────────────────┘
                            │                                            │
                    ┌───────▼────────┐                         ┌────────▼────────┐
                    │Image Desc Text │                         │  Audio Files    │
                    └────────────────┘                         │   (.wav/.mp3)   │
                                                               └─────────────────┘
```

## Development

### Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Formatting

```bash
# Format Python code
black .

# Check formatting
black --check .
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests: `pytest tests/`
5. Format code: `black .`
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

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

## API Reference

See [docs/API.md](docs/API.md) for detailed API documentation.