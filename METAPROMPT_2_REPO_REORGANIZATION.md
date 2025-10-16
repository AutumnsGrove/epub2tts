# Metaprompt #2: epub2tts Repository Reorganization

**Task Type:** Sequential reorganization via general-purpose Task agent
**Objective:** Reorganize epub2tts repository with clean separation: /core/, /audio-processing/, /web/, /cli/
**Prerequisites:** Metaprompt #1 COMPLETE - Omniparser package exists and is validated
**Validation Required:** All existing tests pass, CLI still works

---

## Task Overview

You are reorganizing the epub2tts repository to support both CLI and web interfaces with clean architectural separation:

- **Omniparser** (external): All document parsing
- **/core/**: Pipeline orchestration and processing logic
- **/audio-processing/**: Abstract TTS engine interface (Kokoro, ElevenLabs, Hume-ready)
- **/web/**: Web interface (FastAPI backend + vanilla JS frontend)
- **/cli/**: Command-line interface (existing functionality preserved)

This is a major refactoring. Every step must be validated before proceeding to the next.

---

## Prerequisites Validation

**Before starting, verify:**
- [ ] Omniparser package exists in separate repository
- [ ] Omniparser can be installed: `uv add omniparser`
- [ ] Omniparser tests all pass
- [ ] Current epub2tts tests all pass (baseline)

**If any prerequisite fails, STOP and return to Metaprompt #1.**

---

## Current vs. Target Structure

### Current Structure:
```
epub2tts/
├── src/
│   ├── cli.py
│   ├── core/
│   │   ├── epub_processor.py          # Has EPUB logic - TO REMOVE
│   │   ├── ebooklib_processor.py      # Has EPUB logic - TO REMOVE
│   │   ├── pandoc_wrapper.py
│   │   └── text_cleaner.py
│   ├── pipelines/                      # TO MOVE to /core/
│   │   ├── orchestrator.py
│   │   ├── tts_pipeline.py             # Kokoro - TO MOVE to /audio-processing/
│   │   ├── elevenlabs_tts_pipeline.py  # ElevenLabs - TO MOVE to /audio-processing/
│   │   ├── elevenlabs_tts.py
│   │   └── image_pipeline.py
│   ├── text/                           # TO KEEP
│   │   ├── modern_text_processor.py
│   │   └── enhanced_text_cleaner.py
│   ├── ui/                             # TO KEEP (CLI only)
│   │   ├── terminal_ui.py
│   │   └── progress_tracker.py
│   └── utils/                          # TO KEEP
│       ├── config.py
│       ├── logger.py
│       └── secrets.py
└── tests/
```

### Target Structure:
```
epub2tts/
├── cli/                                # CLI interface
│   ├── __init__.py
│   └── main.py                         # Port from src/cli.py
│
├── core/                               # Pipeline orchestration
│   ├── __init__.py
│   ├── orchestrator.py                 # FROM src/pipelines/orchestrator.py
│   ├── pipeline_base.py                # NEW - abstract base
│   ├── progress_tracker.py             # FROM src/ui/progress_tracker.py
│   └── image_pipeline.py               # FROM src/pipelines/image_pipeline.py
│
├── audio_processing/                   # TTS engines (hyphen becomes underscore)
│   ├── __init__.py                     # Factory function
│   ├── base.py                         # NEW - abstract interface
│   ├── kokoro_engine.py                # FROM src/pipelines/tts_pipeline.py
│   ├── elevenlabs_engine.py            # FROM src/pipelines/elevenlabs_tts_pipeline.py
│   └── hume_engine.py                  # NEW - placeholder stub
│
├── web/                                # Web interface (NEW - empty for now)
│   ├── backend/
│   │   └── README.md                   # Placeholder
│   └── frontend/
│       └── README.md                   # Placeholder
│
├── text/                               # Text processing (KEEP)
│   ├── __init__.py
│   ├── modern_text_processor.py
│   └── enhanced_text_cleaner.py
│
├── ui/                                 # Terminal UI (KEEP for CLI)
│   ├── __init__.py
│   └── terminal_ui.py
│
├── utils/                              # Utilities (KEEP)
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   └── secrets.py
│
├── tests/                              # Tests
│   ├── cli/                            # CLI tests
│   ├── core/                           # Core tests
│   ├── audio_processing/               # Audio tests
│   └── integration/                    # Integration tests
│
├── docs/
├── config/
├── pyproject.toml                      # UPDATE dependencies
├── README.md                           # UPDATE with new structure
└── ARCHITECTURE.md                     # NEW - document structure
```

---

## Implementation Phases

### Phase 1: Create New Directory Structure

**Task:** Create new directories (empty for now)

```bash
mkdir -p cli
mkdir -p core
mkdir -p audio_processing
mkdir -p web/backend
mkdir -p web/frontend
mkdir -p tests/cli
mkdir -p tests/core
mkdir -p tests/audio_processing
mkdir -p tests/web
```

**Create placeholder files:**
- `cli/__init__.py`
- `core/__init__.py`
- `audio_processing/__init__.py`
- `web/backend/README.md` (with "Coming soon" message)
- `web/frontend/README.md` (with "Coming soon" message)

**Validation:**
- All directories exist
- Git tracks new directories (add __init__.py files)

---

### Phase 2: Create Abstract Audio Interface

**Task:** Create `audio_processing/base.py` with abstract TTS interface

**Implementation:**
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class AudioSegment:
    """Represents a generated audio segment"""
    audio_data: bytes
    format: str  # "wav", "mp3", etc.
    duration: float
    sample_rate: int
    word_timings: Optional[List[dict]] = None

@dataclass
class TTSRequest:
    """Request for TTS generation"""
    text: str
    voice: str
    speed: float = 1.0
    pitch: float = 1.0
    additional_params: Optional[dict] = None

class BaseTTSEngine(ABC):
    """Abstract base class for all TTS engines"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the TTS engine (load models, connect to API, etc.)"""
        pass

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """
        Generate audio from text.

        Args:
            request: TTSRequest with text and parameters

        Returns:
            AudioSegment with generated audio and metadata
        """
        pass

    @abstractmethod
    async def get_available_voices(self) -> List[str]:
        """Return list of available voice IDs"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources (optional)"""
        pass

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Return engine identifier (e.g., 'kokoro', 'elevenlabs', 'hume')"""
        pass
```

**Validation:**
- File is syntactically correct
- Imports work
- Can create subclass that implements interface

---

### Phase 3: Port Kokoro TTS to Audio Processing

**Task:** Create `audio_processing/kokoro_engine.py` by refactoring `src/pipelines/tts_pipeline.py`

**Source:** `/Users/autumn/Documents/Projects/epub2tts/src/pipelines/tts_pipeline.py`

**Implementation Steps:**
1. Read the existing tts_pipeline.py
2. Extract the Kokoro TTS logic
3. Wrap in `KokoroEngine` class that inherits from `BaseTTSEngine`
4. Implement all abstract methods
5. Adapt existing logic to fit new interface

**Key Changes:**
```python
from .base import BaseTTSEngine, TTSRequest, AudioSegment
from typing import List
import asyncio

class KokoroEngine(BaseTTSEngine):
    """Kokoro TTS implementation (local, MLX-optimized)"""

    def __init__(self, model_path: str = "./models/Kokoro-82M-8bit", **config):
        self.model_path = model_path
        self.config = config
        self.model = None

    async def initialize(self) -> None:
        """Load Kokoro model"""
        # Port existing model loading logic
        # From tts_pipeline.py: __init__ and model loading
        pass

    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """Generate audio using Kokoro"""
        # Port existing synthesis logic
        # From tts_pipeline.py: process_chapter or generate_tts
        # Return AudioSegment with word timings if available
        pass

    async def get_available_voices(self) -> List[str]:
        """Return Kokoro voice list"""
        return ["bf_lily", "am_michael", "bf_emma", "am_sarah", "af_heart", "bf_grace"]

    async def cleanup(self) -> None:
        """Clean up Kokoro resources"""
        if self.model:
            # Cleanup logic if needed
            pass

    @property
    def engine_name(self) -> str:
        return "kokoro"
```

**Important:**
- Preserve ALL existing logic (MLX optimization, error handling, etc.)
- Don't rewrite - adapt and wrap
- Maintain backward compatibility with configuration
- Keep all existing features (speed, pitch, sample rate, etc.)

**Validation:**
- Create `tests/audio_processing/test_kokoro_engine.py`
- Test basic synthesis
- Test with different voices
- Test error handling
- All tests pass

---

### Phase 4: Port ElevenLabs TTS to Audio Processing

**Task:** Create `audio_processing/elevenlabs_engine.py` by refactoring existing ElevenLabs logic

**Sources:**
- `/Users/autumn/Documents/Projects/epub2tts/src/pipelines/elevenlabs_tts_pipeline.py`
- `/Users/autumn/Documents/Projects/epub2tts/src/pipelines/elevenlabs_tts.py`

**Implementation Steps:**
1. Read both ElevenLabs files
2. Combine logic into single `ElevenLabsEngine` class
3. Inherit from `BaseTTSEngine`
4. Implement all abstract methods
5. Preserve existing features (chunking, retries, rate limits)

**Key Implementation:**
```python
from .base import BaseTTSEngine, TTSRequest, AudioSegment
from typing import List
from elevenlabs import ElevenLabs

class ElevenLabsEngine(BaseTTSEngine):
    """ElevenLabs TTS implementation (API-based)"""

    def __init__(self, api_key: str, **config):
        self.api_key = api_key
        self.config = config
        self.client = None

    async def initialize(self) -> None:
        """Initialize ElevenLabs API client"""
        # Port existing initialization logic
        pass

    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """Generate audio using ElevenLabs API"""
        # Port existing synthesis logic
        # Handle chunking, retries, rate limits
        pass

    async def get_available_voices(self) -> List[str]:
        """Fetch voice library from API"""
        # Port existing voice list logic
        pass

    async def cleanup(self) -> None:
        """Clean up ElevenLabs client"""
        pass

    @property
    def engine_name(self) -> str:
        return "elevenlabs"
```

**Validation:**
- Create `tests/audio_processing/test_elevenlabs_engine.py`
- Test with mock API (use unittest.mock)
- Test chunking logic
- Test retry logic
- All tests pass

---

### Phase 5: Create Hume Engine Stub

**Task:** Create `audio_processing/hume_engine.py` as placeholder for future implementation

**Implementation:**
```python
from .base import BaseTTSEngine, TTSRequest, AudioSegment
from typing import List

class HumeEngine(BaseTTSEngine):
    """
    Hume AI TTS implementation (placeholder for future)

    Will support emotional TTS parameters:
    - emotion: joy, sadness, excitement, calm, etc.
    - intensity: 0.0-1.0
    - expressiveness: 0.0-1.0

    Usage when implemented:
        engine = HumeEngine(api_key="...")
        await engine.initialize()

        request = TTSRequest(
            text="Hello world",
            voice="default",
            additional_params={
                "emotion": "joy",
                "intensity": 0.8,
                "expressiveness": 0.7
            }
        )
        audio = await engine.synthesize(request)
    """

    def __init__(self, api_key: str, **config):
        self.api_key = api_key
        self.config = config
        self.client = None

    async def initialize(self) -> None:
        """Initialize Hume API client"""
        raise NotImplementedError(
            "Hume engine not yet implemented. "
            "Waiting for Hume integration to be merged from other machine."
        )

    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """Generate audio with emotional parameters"""
        raise NotImplementedError("Hume engine not yet implemented")

    async def get_available_voices(self) -> List[str]:
        """Fetch Hume voice library"""
        raise NotImplementedError("Hume engine not yet implemented")

    async def cleanup(self) -> None:
        """Clean up Hume client"""
        pass

    @property
    def engine_name(self) -> str:
        return "hume"
```

**Validation:**
- File is syntactically correct
- Import works
- Can instantiate (but methods raise NotImplementedError)
- Clear error messages guide future implementation

---

### Phase 6: Create TTS Engine Factory

**Task:** Create `audio_processing/__init__.py` with factory function

**Implementation:**
```python
"""
Audio Processing Package

Provides abstract interface for TTS engines:
- Kokoro (local, MLX-optimized)
- ElevenLabs (API-based)
- Hume (future, API-based with emotional parameters)

Usage:
    from audio_processing import create_tts_engine, TTSRequest

    engine = create_tts_engine(
        engine_type="kokoro",
        config={"model_path": "./models/Kokoro-82M-8bit"}
    )

    await engine.initialize()

    request = TTSRequest(
        text="Hello world",
        voice="bf_lily",
        speed=1.0
    )

    audio = await engine.synthesize(request)
"""

from .base import BaseTTSEngine, TTSRequest, AudioSegment
from .kokoro_engine import KokoroEngine
from .elevenlabs_engine import ElevenLabsEngine
from .hume_engine import HumeEngine

__all__ = [
    'BaseTTSEngine',
    'TTSRequest',
    'AudioSegment',
    'KokoroEngine',
    'ElevenLabsEngine',
    'HumeEngine',
    'create_tts_engine'
]

def create_tts_engine(
    engine_type: str,
    config: dict = None
) -> BaseTTSEngine:
    """
    Factory function to create TTS engine instances.

    Args:
        engine_type: "kokoro", "elevenlabs", or "hume"
        config: Engine-specific configuration dict
            - For Kokoro: {"model_path": str, "voice": str, ...}
            - For ElevenLabs: {"api_key": str, "voice_id": str, ...}
            - For Hume: {"api_key": str, ...}

    Returns:
        Initialized TTS engine instance

    Raises:
        ValueError: If engine_type is not supported

    Examples:
        >>> engine = create_tts_engine("kokoro", {"model_path": "./models"})
        >>> await engine.initialize()

        >>> engine = create_tts_engine("elevenlabs", {"api_key": "..."})
        >>> await engine.initialize()
    """
    config = config or {}

    engines = {
        "kokoro": KokoroEngine,
        "elevenlabs": ElevenLabsEngine,
        "hume": HumeEngine,
    }

    if engine_type not in engines:
        available = ", ".join(engines.keys())
        raise ValueError(
            f"Unknown engine: {engine_type}. "
            f"Available engines: {available}"
        )

    engine_class = engines[engine_type]
    return engine_class(**config)
```

**Validation:**
- Can import: `from audio_processing import create_tts_engine`
- Factory creates correct engine type
- Error handling works for unknown engines
- Docstrings are comprehensive

---

### Phase 7: Move Pipeline Orchestration to Core

**Task:** Move and adapt orchestrator to use new audio interface

**Source:** `/Users/autumn/Documents/Projects/epub2tts/src/pipelines/orchestrator.py`

**Steps:**
1. Copy `src/pipelines/orchestrator.py` to `core/orchestrator.py`
2. Update imports to use `audio_processing`
3. Adapt to use abstract TTS interface
4. Add Omniparser integration

**Key Changes:**
```python
# core/orchestrator.py

from audio_processing import create_tts_engine, TTSRequest
from omniparser import parse_document

class PipelineOrchestrator:
    """Orchestrates document processing pipeline"""

    def __init__(self, config):
        self.config = config

        # Create TTS engine via factory
        self.tts_engine = create_tts_engine(
            engine_type=config.tts_engine,  # "kokoro", "elevenlabs", "hume"
            config=config.tts_config
        )

    async def process_document(self, file_path: str):
        """
        Process document through full pipeline.

        Args:
            file_path: Path to document file

        Returns:
            Processing result with audio and metadata
        """
        # Step 1: Parse document with Omniparser
        parsed_doc = parse_document(
            file_path,
            extract_images=self.config.extract_images,
            detect_chapters=self.config.detect_chapters
        )

        # Step 2: Initialize TTS engine
        await self.tts_engine.initialize()

        # Step 3: Process through existing text pipeline
        # (Keep existing logic for text processing)

        # Step 4: Generate audio for each chapter
        audio_segments = []
        for chapter in parsed_doc.chapters:
            request = TTSRequest(
                text=chapter.content,
                voice=self.config.voice,
                speed=self.config.speed,
                pitch=self.config.pitch
            )

            audio = await self.tts_engine.synthesize(request)
            audio_segments.append(audio)

        # Step 5: Merge audio segments
        # (Keep existing merge logic)

        # Step 6: Return result
        return result
```

**Important:**
- Preserve existing orchestration logic
- Keep image pipeline integration
- Keep progress tracking
- Add Omniparser integration
- Use abstract audio interface

**Validation:**
- Create `tests/core/test_orchestrator.py`
- Test with mock TTS engine
- Test with mock Omniparser
- Test progress tracking
- All tests pass

---

### Phase 8: Move Image Pipeline to Core

**Task:** Move image pipeline to core

**Simple Move:**
```bash
cp src/pipelines/image_pipeline.py core/image_pipeline.py
```

**Update imports in the file:**
- Change any `from ..pipelines` to `from ..core`
- Update any other internal imports

**Validation:**
- Import works: `from core.image_pipeline import ImagePipeline`
- Existing functionality preserved

---

### Phase 9: Create Progress Tracker in Core

**Task:** Move progress tracker to core (used by both CLI and web)

**Source:** `/Users/autumn/Documents/Projects/epub2tts/src/ui/progress_tracker.py`

**Decision:**
- CLI uses this for terminal UI
- Web will use this for WebSocket updates
- Should be in core (shared)

**Action:**
```bash
cp src/ui/progress_tracker.py core/progress_tracker.py
```

**Update:**
- Keep in `ui/` for CLI compatibility (for now)
- Also add to `core/` for web use
- Later can remove from `ui/` if no conflicts

**Validation:**
- Import from both locations works
- No circular dependencies

---

### Phase 10: Port CLI to New Structure

**Task:** Create `cli/main.py` from `src/cli.py`

**Source:** `/Users/autumn/Documents/Projects/epub2tts/src/cli.py`

**Steps:**
1. Copy `src/cli.py` to `cli/main.py`
2. Update imports to new structure:
   ```python
   # OLD
   from src.pipelines.orchestrator import PipelineOrchestrator
   from src.pipelines.tts_pipeline import KokoroTTSPipeline

   # NEW
   from core.orchestrator import PipelineOrchestrator
   from audio_processing import create_tts_engine
   ```
3. Remove direct EPUB processing (use Omniparser)
4. Update configuration paths

**Key Changes:**
```python
# cli/main.py

import click
from pathlib import Path
from core.orchestrator import PipelineOrchestrator
from audio_processing import create_tts_engine
from omniparser import parse_document
from utils.config import load_config

@click.group()
def cli():
    """epub2tts - EPUB to TTS converter (CLI and Web)"""
    pass

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--engine', type=click.Choice(['kokoro', 'elevenlabs', 'hume']), default='kokoro')
@click.option('--voice', default='bf_lily')
@click.option('--output', '-o', type=click.Path())
def convert(input_file, engine, voice, output):
    """Convert document to audiobook"""

    # Load config
    config = load_config()
    config.tts_engine = engine
    config.voice = voice

    # Create orchestrator
    orchestrator = PipelineOrchestrator(config)

    # Process document
    click.echo(f"Processing {input_file}...")
    result = orchestrator.process_document(input_file)

    click.echo(f"✓ Complete! Output: {result.output_path}")

# ... other commands ...

if __name__ == '__main__':
    cli()
```

**Validation:**
- CLI runs: `uv run python -m cli.main --help`
- Can convert EPUB: `uv run python -m cli.main convert test.epub`
- All CLI commands work
- Output matches previous behavior

---

### Phase 11: Update pyproject.toml

**Task:** Update package configuration with new structure and dependencies

**Key Changes:**

1. **Add omniparser dependency:**
```toml
dependencies = [
    # ... existing dependencies ...
    "omniparser>=1.0.0",
]
```

2. **Update package structure:**
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["cli*", "core*", "audio_processing*", "text*", "utils*", "ui*"]
```

3. **Update entry points:**
```toml
[project.scripts]
epub2tts = "cli.main:cli"
```

4. **Update project description:**
```toml
description = "A production-ready document to TTS converter with CLI and web interfaces"
```

**Validation:**
- `uv sync` runs without errors
- Dependencies install correctly
- Package structure is recognized

---

### Phase 12: Remove Old EPUB Processing Files

**Task:** Remove files that are now handled by Omniparser

**Files to Remove:**
```bash
rm src/core/epub_processor.py
rm src/core/ebooklib_processor.py
rm src/core/pandoc_wrapper.py
```

**Why Safe:**
- EPUB processing now in Omniparser
- epub2tts gets parsed documents from Omniparser
- No other code depends on these files (after refactoring)

**Before Removing:**
1. Search codebase for imports of these files:
   ```bash
   grep -r "epub_processor" .
   grep -r "ebooklib_processor" .
   grep -r "pandoc_wrapper" .
   ```
2. Fix any remaining imports
3. Then remove files

**Validation:**
- No import errors
- All tests still pass
- CLI still works

---

### Phase 13: Remove Old Pipeline Directory

**Task:** Remove `src/pipelines/` (all files moved)

**Files Moved:**
- `orchestrator.py` → `core/orchestrator.py` ✓
- `tts_pipeline.py` → `audio_processing/kokoro_engine.py` ✓
- `elevenlabs_tts_pipeline.py` → `audio_processing/elevenlabs_engine.py` ✓
- `elevenlabs_tts.py` → Merged into elevenlabs_engine.py ✓
- `image_pipeline.py` → `core/image_pipeline.py` ✓

**Before Removing:**
1. Verify all files have been moved/refactored
2. Search for any remaining imports:
   ```bash
   grep -r "from src.pipelines" .
   grep -r "from pipelines" .
   ```
3. Fix any remaining imports

**Then Remove:**
```bash
rm -rf src/pipelines/
```

**Validation:**
- No import errors
- All tests pass
- CLI works

---

### Phase 14: Remove Old src/ Directory (Optional)

**Task:** Clean up legacy src/ structure

**Remaining in src/:**
- `src/cli.py` - Can remove (replaced by cli/main.py)
- `src/core/text_cleaner.py` - Can remove (Omniparser handles this)
- Other files in src/core/ - Verify if needed

**Decision:**
- Keep `src/text/` (modern text processors still useful)
- Keep `src/ui/` (terminal UI for CLI)
- Keep `src/utils/` (shared utilities)
- Remove `src/cli.py` (replaced)
- Remove `src/core/` entirely (all moved or replaced)

**Action:**
```bash
# Remove replaced files
rm src/cli.py
rm -rf src/core/

# Optionally move remaining to top level
mv src/text ./text
mv src/ui ./ui
mv src/utils ./utils

# Remove now-empty src/
rm -rf src/
```

**Or Keep src/ for backwards compatibility:**
```bash
# Just remove duplicated files
rm src/cli.py
rm -rf src/core/
rm -rf src/pipelines/

# Keep src/text/, src/ui/, src/utils/ for now
```

**Validation:**
- All imports still work
- No broken references
- Tests pass
- CLI works

---

### Phase 15: Update All Tests

**Task:** Update test imports and structure

**Test Directory Reorganization:**
```bash
# Create new test structure
mkdir -p tests/cli
mkdir -p tests/core
mkdir -p tests/audio_processing
mkdir -p tests/integration

# Move existing tests
mv tests/test_*.py tests/integration/  # Generic integration tests
```

**Update Test Imports:**
- Search all test files for old imports
- Update to new structure:
  ```python
  # OLD
  from src.pipelines.orchestrator import PipelineOrchestrator

  # NEW
  from core.orchestrator import PipelineOrchestrator
  ```

**New Tests to Create:**
- `tests/audio_processing/test_factory.py` - Test TTS factory
- `tests/audio_processing/test_kokoro_engine.py` - Test Kokoro wrapper
- `tests/audio_processing/test_elevenlabs_engine.py` - Test ElevenLabs wrapper
- `tests/core/test_orchestrator.py` - Test updated orchestrator
- `tests/cli/test_main.py` - Test CLI commands

**Validation:**
- All tests pass: `uv run pytest`
- Test coverage maintained (>80%)
- No skipped tests

---

### Phase 16: Update Documentation

**Task:** Create/update documentation for new structure

**16a. Update README.md:**
- Document new architecture
- Update installation instructions
- Update usage examples (CLI + mention web coming)
- Add architecture diagram

**16b. Create ARCHITECTURE.md:**
```markdown
# epub2tts Architecture

## Overview
epub2tts is a dual-mode (CLI + web) document to audiobook converter.

## Components
- **Omniparser** (external): Universal document parsing
- **core/**: Pipeline orchestration
- **audio-processing/**: TTS engine abstraction
- **cli/**: Command-line interface
- **web/**: Web interface (in development)

## Data Flow
[Include diagram]

## Adding New TTS Engines
[Guide for implementing new engines]
```

**16c. Update API.md:**
- Document new public APIs
- Document audio_processing interface
- Document core orchestrator

**16d. Create MIGRATION_GUIDE.md:**
```markdown
# Migration Guide: Old → New Structure

For developers familiar with the old structure.

## Import Changes
OLD: `from src.pipelines.tts_pipeline import KokoroTTSPipeline`
NEW: `from audio_processing import KokoroEngine, create_tts_engine`

## EPUB Processing
OLD: Used internal EPUB processors
NEW: Uses Omniparser (external package)

## TTS Engines
OLD: Direct class instantiation
NEW: Factory function: `create_tts_engine()`

[More details...]
```

**Validation:**
- Documentation is clear and accurate
- Examples work
- Architecture diagram is correct

---

### Phase 17: Final Validation

**Task:** Comprehensive validation of reorganized repository

**Validation Checklist:**
- [ ] All tests pass: `uv run pytest`
- [ ] Test coverage >80%: `uv run pytest --cov`
- [ ] CLI works: `uv run python -m cli.main --help`
- [ ] Can convert EPUB: `uv run python -m cli.main convert test.epub`
- [ ] Can convert PDF: `uv run python -m cli.main convert test.pdf`
- [ ] Kokoro TTS works
- [ ] ElevenLabs TTS works (with API key)
- [ ] All existing features preserved
- [ ] No import errors
- [ ] No circular dependencies
- [ ] Documentation is up-to-date
- [ ] Code formatted: `uv run black .`
- [ ] Type checking passes: `uv run mypy .`

**Test Commands:**
```bash
# Run all tests
uv run pytest -v

# Check coverage
uv run pytest --cov=. --cov-report=html

# Test CLI
uv run python -m cli.main --version
uv run python -m cli.main --help
uv run python -m cli.main convert tests/fixtures/test.epub

# Format check
uv run black --check .

# Type check
uv run mypy cli core audio_processing
```

**Regression Testing:**
- Test with same EPUB files as before reorganization
- Compare output audio (should be identical)
- Verify all CLI commands work the same
- Check that configuration files still work

**Performance Testing:**
- Processing time should be similar
- Memory usage should be similar
- No performance regressions

---

### Phase 18: Git Commit & Documentation

**Task:** Commit reorganization with clear message

**Git Operations:**
```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Refactor: Reorganize repository structure

- Move document parsing to external Omniparser package
- Reorganize to /core/, /audio-processing/, /cli/ structure
- Abstract TTS engines with common interface (Kokoro, ElevenLabs, Hume-ready)
- Preserve all existing CLI functionality
- Add placeholder /web/ directory for future web interface
- Update all tests and documentation
- All tests pass, CLI works identically

Breaking changes:
- Internal imports changed (external API unchanged)
- EPUB processing now via Omniparser

Migration:
- See MIGRATION_GUIDE.md for details
- For most users: No changes needed (CLI works the same)
- For library users: Update imports per MIGRATION_GUIDE.md
"

# Create tag
git tag -a v2.0.0 -m "Version 2.0: Repository reorganization with Omniparser"
```

**Documentation Update:**
- Update CHANGELOG.md with v2.0.0 release notes
- Update README.md with migration notice
- Create GitHub release (if applicable)

**Validation:**
- Clean git status
- No uncommitted changes
- Tag created successfully

---

## Success Criteria

**Must Have:**
- ✅ All tests pass (no regressions)
- ✅ CLI works identically to before
- ✅ Clean architectural separation (/core/, /audio-processing/, /cli/)
- ✅ Abstract TTS interface implemented
- ✅ Omniparser integration works
- ✅ All existing features preserved
- ✅ Documentation updated
- ✅ Hume engine stub ready for future implementation

**Quality Metrics:**
- Test coverage maintained (>80%)
- No import errors or circular dependencies
- Code formatted and type-checked
- Clear migration guide for developers

**Validation Statement:**
Before proceeding to web development, you MUST confirm:

> "Repository reorganization is COMPLETE. All tests pass. CLI works identically. Architecture is clean. Ready for web development."

---

## Important Notes

1. **Preserve Existing Functionality** - The CLI must work exactly as before. This is a refactoring, not a rewrite.

2. **Test Continuously** - Run tests after every phase. If tests fail, fix before proceeding.

3. **No Rewrites** - Port existing code, don't rewrite it. The TTS logic is production-tested.

4. **Abstract Properly** - The audio interface must be truly abstract. Adding Hume later should require ONLY implementing hume_engine.py.

5. **Document Everything** - Future developers need clear migration guides.

6. **Validate Thoroughly** - The final validation checklist is critical. Don't skip it.

---

## Handoff to Web Development

Once reorganization is complete and validated, the next steps are:

**Phase A: Web Backend Development**
- FastAPI application structure
- REST API endpoints
- WebSocket for real-time updates
- Document upload/processing
- TTS generation API (wraps audio_processing)
- Reading position save/restore

**Phase B: Web Frontend Development**
- Vanilla JavaScript components
- Upload interface
- Reader view with word highlighting
- Audio player with controls
- Settings panel

**Do NOT start web development until reorganization is FULLY validated.**

---

**End of Metaprompt #2**

This metaprompt provides complete, step-by-step instructions for reorganizing the epub2tts repository with validation at every step.
