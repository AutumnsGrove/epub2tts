# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-10-29

### Changed
- **BREAKING**: EPUB processing now uses OmniParser library (>= 0.3.0) exclusively
- Simplified EPUBProcessor architecture - removed processor selection logic
- Direct integration of OmniParser models (Document, Metadata, Chapter)
- Improved EPUB parsing performance (0.34s for 40k words, 13 chapters)

### Added
- Inline conversion methods for OmniParser → epub2tts data models
- Comprehensive integration tests for OmniParser
- Full backward compatibility with existing ProcessingResult interface

### Removed
- **1,371 lines of legacy code removed** (87% reduction in EPUB processing)
- `src/core/ebooklib_processor.py` (964 lines) - replaced by OmniParser
- `src/core/pandoc_wrapper.py` (407 lines) - no longer needed
- `tests/unit/test_pandoc_wrapper.py` - obsolete
- Dependencies: `ebooklib`, `pypandoc`, `pypandoc-binary` (now via OmniParser)
- Config options: `epub_processor`, `pandoc_path` (OmniParser only now)

### Performance
- EPUB parsing: **8.7x faster** than Pandoc (0.34s vs 2.9s)
- Chapter detection: **13 chapters** vs 3 (Pandoc regex-based)
- Metadata extraction: **12 fields** vs 6 (richer metadata)
- Native TOC support: **High accuracy** chapter boundaries

### Migration Notes
- No action required for most users - ProcessingResult interface unchanged
- Custom processors: Migrate to OmniParser's `parse_document()` API
- Config files: Remove `epub_processor` and `pandoc_path` settings (auto-migrated)

## [0.1.0] - 2025-10-28

### Added
- Initial release with Kokoro TTS and EbookLib EPUB processing
- Modern text processing with spaCy and NLTK
- Image description support with local VLM
- Split-window terminal UI with Rich
- ElevenLabs TTS integration
- Comprehensive test suite (149 tests)

---

[Unreleased]: https://github.com/AutumnsGrove/epub2tts/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/AutumnsGrove/epub2tts/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/AutumnsGrove/epub2tts/releases/tag/v0.1.0
