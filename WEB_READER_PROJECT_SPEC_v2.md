# epub2tts Web Reader - Project Specification v2.0

## Document Version: 2.0
**Last Updated:** October 16, 2025
**Status:** Active - Implementation Phase
**Target Platform:** Self-hosted web application (Desktop-first, mobile-accessible)

---

## 1. Executive Summary

### 1.1 Project Overview
The epub2tts Web Reader transforms the existing CLI tool into a dual-mode application supporting both command-line and web-based interfaces. It provides a desktop-optimized reading experience with integrated text-to-speech capabilities, supporting multiple document formats through the separate Omniparser library.

### 1.2 Core Value Proposition
- **Privacy-first**: Self-hosted, no cloud dependencies for core functionality
- **Multi-modal**: Support for text uploads, URLs, and multiple document formats
- **Dual Interface**: Both CLI and web access in single application
- **Modular**: Clean separation between parsing (Omniparser), audio (TTS engines), and orchestration (core pipelines)
- **Flexible**: Switch voices and adjust parameters while audio is playing
- **Desktop-optimized**: Primary focus on desktop browsers with mobile accessibility

### 1.3 Architecture Philosophy
**Separation of Concerns:**
- **Omniparser** (separate repo): Universal document parsing to Markdown
- **epub2tts/core**: Pipeline orchestration and processing logic
- **epub2tts/audio-processing**: Abstract TTS engine interface (Kokoro, ElevenLabs, Hume-ready)
- **epub2tts/web**: Web interface (FastAPI backend + vanilla JS frontend)
- **epub2tts/cli**: Command-line interface (existing functionality preserved)

---

## 2. Architecture Overview

### 2.1 Technology Stack

**Backend:**
- Python 3.10+ (FastAPI framework)
- Existing epub2tts pipeline orchestration
- WebSocket support for real-time updates
- SQLite for metadata and position tracking
- Omniparser (external package) for document parsing

**Frontend:**
- Vanilla HTML5/CSS3/JavaScript (no frameworks)
- Web Components for modular UI
- Progressive Web App (PWA) manifest (future)
- Service Worker for caching (reach goal)

**Audio Processing:**
- Kokoro TTS (MLX-optimized, local)
- ElevenLabs TTS (API-based, cloud)
- Hume AI TTS (future, API-based with emotional parameters)
- Abstract interface for easy engine addition

**Storage:**
- SQLite for metadata, positions, and logs
- File system for audio/text cache (last 5 items)
- Optional cloud storage integration (future)

### 2.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Client (Desktop)                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │   Upload   │  │  Reader UI   │  │  Playback Ctrl   │    │
│  │  Interface │  │ (Web Comp.)  │  │   (HTML5 Audio)  │    │
│  └─────┬──────┘  └──────┬───────┘  └────────┬─────────┘    │
│        │                 │                    │              │
└────────┼─────────────────┼────────────────────┼──────────────┘
         │                 │                    │
    ┌────▼─────────────────▼────────────────────▼────┐
    │      WebSocket + REST API (FastAPI)            │
    │            /web/backend/                        │
    └────┬───────────────────────┬───────────────────┘
         │                       │
    ┌────▼────────┐         ┌────▼─────────────────────┐
    │ Omniparser  │         │   Core Pipeline          │
    │ (External)  │         │   /core/                 │
    │ - EPUB      │────────▶│   orchestrator.py        │
    │ - PDF       │         │   progress_tracker.py    │
    │ - DOCX      │         └────┬─────────────────────┘
    │ - HTML/URL  │              │
    │ - TXT/MD    │              │
    └─────────────┘         ┌────▼─────────────────────┐
                            │  Audio Processing        │
                            │  /audio-processing/      │
                            │  - base.py (abstract)    │
                            │  - kokoro_engine.py      │
                            │  - elevenlabs_engine.py  │
                            │  - hume_engine.py (stub) │
                            └──────────────────────────┘
                                     │
                            ┌────────▼──────────────────┐
                            │    Storage Layer          │
                            │    - SQLite (metadata)    │
                            │    - Cache (audio/text)   │
                            └───────────────────────────┘
```

### 2.3 Data Flow

```
User Upload → FastAPI Backend → Omniparser (external) → Clean Markdown
                                                              ↓
                                                  Core Pipeline Orchestrator
                                                              ↓
                                                  Audio Processing (abstract)
                                                              ↓
                                           ┌──────────────────┴──────────────┐
                                           ▼                                  ▼
                                    Kokoro Engine                    ElevenLabs Engine
                                    (local, MLX)                     (API, cloud)
                                           │                                  │
                                           └──────────────┬───────────────────┘
                                                          ↓
                                                Audio Streamed to Frontend
                                                          ↓
                                            Word-by-word Highlighting
                                                          ↓
                                          Position Auto-saved to SQLite
```

### 2.4 Repository Structure

```
epub2tts/
├── cli/                          # CLI interface (existing, preserved)
│   ├── __init__.py
│   └── main.py                   # Entry point for CLI commands
│
├── core/                         # Pipeline orchestration (MOVED from src/pipelines/)
│   ├── __init__.py
│   ├── orchestrator.py           # Master pipeline coordinator
│   ├── pipeline_base.py          # Abstract base for pipelines
│   ├── progress_tracker.py       # Event-driven progress tracking
│   └── image_pipeline.py         # VLM image description pipeline
│
├── audio-processing/             # TTS engines (NEW organization)
│   ├── __init__.py
│   ├── base.py                   # Abstract TTS interface
│   ├── kokoro_engine.py          # Kokoro TTS implementation
│   ├── elevenlabs_engine.py      # ElevenLabs API wrapper
│   └── hume_engine.py            # Hume AI (placeholder/future)
│
├── web/                          # Web interface (NEW)
│   ├── backend/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py           # FastAPI application
│   │   │   ├── config.py         # Web-specific configuration
│   │   │   ├── database.py       # SQLite async connection
│   │   │   ├── models/           # Pydantic data models
│   │   │   │   ├── document.py
│   │   │   │   ├── position.py
│   │   │   │   └── tts.py
│   │   │   ├── routers/          # API endpoints
│   │   │   │   ├── documents.py  # Upload/retrieve/list
│   │   │   │   ├── tts.py        # TTS generation
│   │   │   │   ├── positions.py  # Reading position save/restore
│   │   │   │   └── analytics.py  # Usage logs/stats (future)
│   │   │   ├── services/         # Business logic
│   │   │   │   ├── document_service.py
│   │   │   │   ├── tts_service.py    # Wraps audio-processing/
│   │   │   │   └── cache_manager.py
│   │   │   └── websocket/
│   │   │       └── manager.py    # Real-time progress updates
│   │   ├── cache/                # Document cache storage
│   │   ├── uploads/              # Temporary file uploads
│   │   └── tests/                # Backend tests
│   │
│   └── frontend/
│       ├── index.html
│       ├── css/
│       │   ├── main.css          # Global styles
│       │   ├── reader.css        # Reader-specific styles
│       │   ├── components.css    # Web component styles
│       │   └── responsive.css    # Mobile adaptations
│       ├── js/
│       │   ├── app.js            # Main application
│       │   ├── components/       # Web Components
│       │   │   ├── upload-zone.js
│       │   │   ├── reader-view.js
│       │   │   ├── audio-player.js
│       │   │   ├── toc-drawer.js
│       │   │   └── settings-panel.js
│       │   ├── services/
│       │   │   ├── api.js        # Backend API client
│       │   │   ├── websocket.js  # WebSocket connection
│       │   │   └── word-sync.js  # Audio-text synchronization
│       │   └── utils/
│       │       └── helpers.js
│       ├── assets/               # Icons, images
│       └── manifest.json         # PWA manifest (future)
│
├── utils/                        # Shared utilities (existing)
│   ├── config.py
│   ├── logger.py
│   └── secrets.py
│
├── text/                         # Text processing (existing)
│   ├── modern_text_processor.py
│   └── enhanced_text_cleaner.py
│
├── ui/                           # Terminal UI (CLI only)
│   ├── terminal_ui.py
│   └── progress_tracker.py
│
├── tests/                        # Test suite
│   ├── unit/
│   ├── integration/
│   └── web/                      # Web-specific tests
│
├── docs/                         # Documentation
├── config/                       # Configuration files
├── pyproject.toml                # UV package configuration
└── README.md
```

---

## 3. Core Features Specification

### 3.1 Content Ingestion

#### 3.1.1 Upload Interface (Web)
**Requirements:**
- Drag-and-drop file upload zone
- File size validation (25MB hard limit)
- Progress indicator for uploads
- Support for multiple files in queue

**Supported Formats** (via Omniparser):
- EPUB (delegated to Omniparser)
- PDF (new in Omniparser)
- DOCX (new in Omniparser)
- TXT (new in Omniparser)
- HTML (new in Omniparser)
- Markdown (new in Omniparser)
- URLs (web scraping in Omniparser)

**Backend Validation Flow:**
```python
# web/backend/app/routers/documents.py
async def upload_document(file: UploadFile):
    # 1. Validate file size (25MB)
    # 2. Save to temporary location
    # 3. Call Omniparser (external package)
    # 4. Process through core/orchestrator.py
    # 5. Return job_id for WebSocket tracking
```

#### 3.1.2 Omniparser Integration

**Omniparser** (external package, separate repo):
- Installed via: `uv add omniparser`
- Interface:
  ```python
  from omniparser import parse_document

  result = parse_document(
      file_path="/path/to/file.pdf",
      extract_images=True,
      detect_chapters=True
  )

  # Returns:
  # {
  #   "document_id": "uuid",
  #   "title": "Document Title",
  #   "author": "Author (if available)",
  #   "word_count": 50000,
  #   "content": "markdown formatted text...",
  #   "chapters": [...],
  #   "images": [...],
  #   "metadata": {...}
  # }
  ```

**Benefits of Separation:**
- Omniparser can be updated independently
- Other projects can use Omniparser
- epub2tts focuses on TTS orchestration
- Clear separation of parsing vs. processing

### 3.2 Audio Processing Architecture

#### 3.2.1 Abstract Interface (`audio-processing/base.py`)

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

#### 3.2.2 Kokoro Engine (`audio-processing/kokoro_engine.py`)

Wraps existing `src/pipelines/tts_pipeline.py` logic:

```python
from .base import BaseTTSEngine, TTSRequest, AudioSegment
from typing import List

class KokoroEngine(BaseTTSEngine):
    """Kokoro TTS implementation (local, MLX-optimized)"""

    def __init__(self, model_path: str = "./models/Kokoro-82M-8bit"):
        self.model_path = model_path
        self.model = None

    async def initialize(self) -> None:
        """Load Kokoro model"""
        # Import existing logic from src/pipelines/tts_pipeline.py
        # Initialize MLX model
        pass

    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """Generate audio using Kokoro"""
        # Call existing synthesis logic
        # Return AudioSegment with word timings
        pass

    async def get_available_voices(self) -> List[str]:
        return ["bf_lily", "am_michael", "bf_emma", "am_sarah"]

    @property
    def engine_name(self) -> str:
        return "kokoro"
```

#### 3.2.3 ElevenLabs Engine (`audio-processing/elevenlabs_engine.py`)

Wraps existing `src/pipelines/elevenlabs_tts_pipeline.py`:

```python
from .base import BaseTTSEngine, TTSRequest, AudioSegment
from typing import List

class ElevenLabsEngine(BaseTTSEngine):
    """ElevenLabs TTS implementation (API-based)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None

    async def initialize(self) -> None:
        """Initialize ElevenLabs API client"""
        # Import existing logic from src/pipelines/elevenlabs_tts_pipeline.py
        pass

    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """Generate audio using ElevenLabs API"""
        # Call existing API logic
        # Handle chunking, retries, rate limits
        pass

    async def get_available_voices(self) -> List[str]:
        """Fetch voice library from API"""
        pass

    @property
    def engine_name(self) -> str:
        return "elevenlabs"
```

#### 3.2.4 Hume Engine (`audio-processing/hume_engine.py`)

**Placeholder for future implementation:**

```python
from .base import BaseTTSEngine, TTSRequest, AudioSegment
from typing import List

class HumeEngine(BaseTTSEngine):
    """
    Hume AI TTS implementation (future)

    Will support emotional TTS parameters:
    - emotion: joy, sadness, excitement, calm, etc.
    - intensity: 0.0-1.0
    - expressiveness: 0.0-1.0
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None

    async def initialize(self) -> None:
        """Initialize Hume API client"""
        # TODO: Implement when Hume integration is merged
        raise NotImplementedError("Hume engine not yet implemented")

    async def synthesize(self, request: TTSRequest) -> AudioSegment:
        """Generate audio with emotional parameters"""
        # TODO: Parse additional_params for emotion settings
        # TODO: Call Hume API
        raise NotImplementedError("Hume engine not yet implemented")

    async def get_available_voices(self) -> List[str]:
        """Fetch Hume voice library"""
        raise NotImplementedError("Hume engine not yet implemented")

    @property
    def engine_name(self) -> str:
        return "hume"
```

**Adding Hume Later:**
1. Implement methods in `hume_engine.py`
2. Add to factory function in `audio-processing/__init__.py`
3. Update web UI to expose emotional parameters
4. No changes needed to core orchestration

#### 3.2.5 Factory Function (`audio-processing/__init__.py`)

```python
from .base import BaseTTSEngine
from .kokoro_engine import KokoroEngine
from .elevenlabs_engine import ElevenLabsEngine
from .hume_engine import HumeEngine

def create_tts_engine(
    engine_type: str,
    config: dict
) -> BaseTTSEngine:
    """
    Factory function to create TTS engine instances.

    Args:
        engine_type: "kokoro", "elevenlabs", or "hume"
        config: Engine-specific configuration

    Returns:
        Initialized TTS engine instance
    """
    engines = {
        "kokoro": KokoroEngine,
        "elevenlabs": ElevenLabsEngine,
        "hume": HumeEngine,
    }

    if engine_type not in engines:
        raise ValueError(f"Unknown engine: {engine_type}")

    engine = engines[engine_type](**config)
    return engine
```

### 3.3 Core Pipeline Integration

The existing pipeline orchestration in `core/orchestrator.py` now uses the abstract audio interface:

```python
# core/orchestrator.py
from audio_processing import create_tts_engine, TTSRequest

class PipelineOrchestrator:
    """Orchestrates document processing pipeline"""

    def __init__(self, config):
        self.config = config
        self.tts_engine = create_tts_engine(
            engine_type=config.tts_engine,
            config=config.tts_config
        )

    async def process_document(self, parsed_document: dict):
        """
        Process document through TTS pipeline.

        Args:
            parsed_document: Output from Omniparser
        """
        # 1. Receive parsed markdown from Omniparser
        # 2. Apply text processing (existing logic)
        # 3. Generate audio via abstract TTS engine
        # 4. Merge audio segments
        # 5. Return output

        await self.tts_engine.initialize()

        for chapter in parsed_document["chapters"]:
            request = TTSRequest(
                text=chapter["content"],
                voice=self.config.voice,
                speed=self.config.speed,
                pitch=self.config.pitch
            )

            audio = await self.tts_engine.synthesize(request)
            # Process audio...
```

### 3.4 Web Backend Architecture

#### 3.4.1 FastAPI Application (`web/backend/app/main.py`)

```python
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from .routers import documents, tts, positions
from .websocket import manager

app = FastAPI(title="epub2tts Web Reader")

# Mount frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# API routes
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages (subscribe to job updates, etc.)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Root serves index.html
@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")
```

#### 3.4.2 Document Upload Router (`web/backend/app/routers/documents.py`)

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..services.document_service import DocumentService
from omniparser import parse_document
import uuid

router = APIRouter()
doc_service = DocumentService()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.

    Returns job_id for WebSocket progress tracking.
    """
    # 1. Validate file size
    if file.size > 25_000_000:  # 25MB
        raise HTTPException(400, "File too large")

    # 2. Save temporarily
    temp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # 3. Parse with Omniparser
    try:
        parsed = parse_document(temp_path)
    except Exception as e:
        raise HTTPException(400, f"Parse error: {str(e)}")

    # 4. Queue for TTS processing
    job_id = await doc_service.create_processing_job(parsed)

    return {"job_id": job_id, "document_id": parsed["document_id"]}

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """Retrieve processed document"""
    doc = await doc_service.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc

@router.get("/")
async def list_documents():
    """List all documents"""
    return await doc_service.list_documents()
```

#### 3.4.3 TTS Router (`web/backend/app/routers/tts.py`)

```python
from fastapi import APIRouter, HTTPException
from ..services.tts_service import TTSService
from ..models.tts import TTSGenerateRequest

router = APIRouter()
tts_service = TTSService()

@router.post("/generate")
async def generate_audio(request: TTSGenerateRequest):
    """
    Generate audio for a document.

    Wraps core/orchestrator.py and audio-processing/ engines.
    """
    try:
        result = await tts_service.generate_audio(
            document_id=request.document_id,
            voice=request.voice,
            engine=request.engine,  # "kokoro", "elevenlabs", "hume"
            speed=request.speed,
            pitch=request.pitch,
            additional_params=request.additional_params
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"TTS generation failed: {str(e)}")

@router.get("/voices")
async def get_voices(engine: str = "kokoro"):
    """Get available voices for an engine"""
    voices = await tts_service.get_voices(engine)
    return {"engine": engine, "voices": voices}
```

#### 3.4.4 WebSocket Manager (`web/backend/app/websocket/manager.py`)

```python
from fastapi import WebSocket
from typing import Dict, Set
import json

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    async def disconnect(self, websocket: WebSocket):
        # Remove from all subscriptions
        for job_id in list(self.active_connections.keys()):
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)

    async def subscribe_to_job(self, job_id: str, websocket: WebSocket):
        """Subscribe to updates for a processing job"""
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)

    async def broadcast_progress(self, job_id: str, progress: dict):
        """Send progress update to all subscribers"""
        if job_id in self.active_connections:
            message = json.dumps({
                "type": "progress",
                "job_id": job_id,
                "data": progress
            })
            for connection in self.active_connections[job_id]:
                await connection.send_text(message)

manager = WebSocketManager()
```

### 3.5 Frontend Architecture

#### 3.5.1 Application Entry (`web/frontend/js/app.js`)

```javascript
// Main application controller
class App {
  constructor() {
    this.api = new APIService('/api');
    this.ws = new WebSocketService('/ws');
    this.state = {
      currentDocument: null,
      isPlaying: false,
      selectedVoice: 'bf_lily',
      selectedEngine: 'kokoro',
      playbackSpeed: 1.0
    };

    this.init();
  }

  async init() {
    // Initialize Web Components
    this.uploadZone = document.querySelector('upload-zone');
    this.reader = document.querySelector('reader-view');
    this.player = document.querySelector('audio-player');

    // Setup event listeners
    this.setupEventListeners();

    // Connect WebSocket
    await this.ws.connect();

    // Load saved state
    await this.loadSavedState();
  }

  setupEventListeners() {
    this.uploadZone.addEventListener('file-uploaded', this.handleUpload.bind(this));
    this.player.addEventListener('play', this.handlePlay.bind(this));
    this.player.addEventListener('pause', this.handlePause.bind(this));
    this.player.addEventListener('seek', this.handleSeek.bind(this));
  }

  async handleUpload(event) {
    const file = event.detail.file;

    // Upload to backend
    const result = await this.api.uploadDocument(file);

    // Subscribe to processing updates
    this.ws.subscribeToJob(result.job_id, (progress) => {
      this.updateProgress(progress);
    });
  }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
```

#### 3.5.2 Reader View Component (`web/frontend/js/components/reader-view.js`)

```javascript
class ReaderView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.words = [];
    this.currentWordIndex = 0;
  }

  connectedCallback() {
    this.render();
  }

  loadDocument(document) {
    this.document = document;
    this.words = this.parseWords(document.content);
    this.render();
  }

  parseWords(text) {
    // Split text into words with position tracking
    const words = [];
    const regex = /\S+/g;
    let match;

    while ((match = regex.exec(text)) !== null) {
      words.push({
        text: match[0],
        index: words.length,
        startPos: match.index,
        endPos: match.index + match[0].length
      });
    }

    return words;
  }

  highlightWord(index) {
    // Remove previous highlight
    const previous = this.shadowRoot.querySelector('.word.current');
    if (previous) previous.classList.remove('current');

    // Highlight current word
    const current = this.shadowRoot.querySelector(`[data-word-index="${index}"]`);
    if (current) {
      current.classList.add('current');
      current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    this.currentWordIndex = index;
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        .reader-container {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
          font-family: Georgia, serif;
          font-size: 1.125rem;
          line-height: 1.6;
        }

        .word {
          transition: background-color 0.1s ease;
          cursor: pointer;
        }

        .word.current {
          background-color: rgba(76, 175, 80, 0.3);
          border-radius: 2px;
          padding: 0 2px;
        }

        .word:hover {
          background-color: rgba(76, 175, 80, 0.1);
        }
      </style>

      <div class="reader-container">
        ${this.words.map(word => `
          <span class="word" data-word-index="${word.index}">${word.text}</span>
        `).join(' ')}
      </div>
    `;

    // Add click handlers for tap-to-jump
    this.shadowRoot.querySelectorAll('.word').forEach(wordEl => {
      wordEl.addEventListener('click', () => {
        const index = parseInt(wordEl.dataset.wordIndex);
        this.dispatchEvent(new CustomEvent('word-clicked', {
          detail: { index }
        }));
      });
    });
  }
}

customElements.define('reader-view', ReaderView);
```

#### 3.5.3 Audio Player Component (`web/frontend/js/components/audio-player.js`)

```javascript
class AudioPlayer extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.audio = new Audio();
    this.isPlaying = false;
  }

  connectedCallback() {
    this.render();
    this.setupAudioHandlers();
  }

  setupAudioHandlers() {
    this.audio.addEventListener('timeupdate', () => {
      this.updateProgress();
      this.updateWordHighlight();
    });

    this.audio.addEventListener('ended', () => {
      this.isPlaying = false;
      this.updatePlayButton();
    });
  }

  loadAudio(url, wordTimings) {
    this.audio.src = url;
    this.wordTimings = wordTimings;
    this.audio.load();
  }

  play() {
    this.audio.play();
    this.isPlaying = true;
    this.updatePlayButton();
    this.dispatchEvent(new CustomEvent('play'));
  }

  pause() {
    this.audio.pause();
    this.isPlaying = false;
    this.updatePlayButton();
    this.dispatchEvent(new CustomEvent('pause'));
  }

  seek(time) {
    this.audio.currentTime = time;
    this.dispatchEvent(new CustomEvent('seek', { detail: { time } }));
  }

  updateWordHighlight() {
    if (!this.wordTimings) return;

    const currentTime = this.audio.currentTime;
    const wordIndex = this.wordTimings.findIndex(
      timing => currentTime >= timing.start && currentTime < timing.end
    );

    if (wordIndex !== -1) {
      this.dispatchEvent(new CustomEvent('word-update', {
        detail: { index: wordIndex }
      }));
    }
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        .player-container {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: white;
          border-top: 1px solid #ddd;
          padding: 1rem;
        }

        .controls {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1rem;
        }

        button {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 4px;
          background: #4CAF50;
          color: white;
          cursor: pointer;
        }

        button:hover {
          background: #388E3C;
        }

        .progress-bar {
          width: 100%;
          height: 4px;
          background: #ddd;
          margin-bottom: 1rem;
          cursor: pointer;
          position: relative;
        }

        .progress-fill {
          height: 100%;
          background: #4CAF50;
          width: 0%;
          transition: width 0.1s linear;
        }
      </style>

      <div class="player-container">
        <div class="progress-bar">
          <div class="progress-fill"></div>
        </div>

        <div class="controls">
          <button class="skip-back">⏮ 15s</button>
          <button class="play-pause">▶️ Play</button>
          <button class="skip-forward">15s ⏭</button>
          <select class="speed-select">
            <option value="0.5">0.5x</option>
            <option value="0.75">0.75x</option>
            <option value="1.0" selected>1.0x</option>
            <option value="1.25">1.25x</option>
            <option value="1.5">1.5x</option>
            <option value="2.0">2.0x</option>
          </select>
        </div>
      </div>
    `;

    // Setup button handlers
    this.shadowRoot.querySelector('.play-pause').addEventListener('click', () => {
      this.isPlaying ? this.pause() : this.play();
    });

    this.shadowRoot.querySelector('.skip-back').addEventListener('click', () => {
      this.seek(Math.max(0, this.audio.currentTime - 15));
    });

    this.shadowRoot.querySelector('.skip-forward').addEventListener('click', () => {
      this.seek(Math.min(this.audio.duration, this.audio.currentTime + 15));
    });

    this.shadowRoot.querySelector('.speed-select').addEventListener('change', (e) => {
      this.audio.playbackRate = parseFloat(e.target.value);
    });
  }
}

customElements.define('audio-player', AudioPlayer);
```

---

## 4. Implementation Phases

### Phase 1: Repository Split & Reorganization (Week 1)

**Omniparser Extraction:**
- Create separate `omniparser` repository
- Port existing EPUB processing logic
- Implement new parsers (PDF, DOCX, HTML, TXT, Markdown)
- Create PyPI-ready package
- Comprehensive testing

**epub2tts Reorganization:**
- Move pipelines to `/core/`
- Create `/audio-processing/` with abstract interface
- Refactor existing TTS implementations
- Create `/web/` directory structure
- Update all imports
- Verify CLI still works

**Validation:**
- All existing tests pass
- CLI generates audiobooks correctly
- Omniparser package installs via `uv add omniparser`

### Phase 2: Web Backend Development (Weeks 2-3)

**FastAPI Setup:**
- Initialize FastAPI application
- Database schema (SQLite with async)
- Document upload endpoints
- TTS generation endpoints
- Reading position save/restore
- WebSocket manager for real-time updates

**Core Integration:**
- Wrap `core/orchestrator.py` in web service
- Integrate Omniparser for document parsing
- Use `audio-processing/` engines via abstract interface
- Background job processing

**Testing:**
- API endpoint tests
- WebSocket communication tests
- Integration tests with core pipeline

### Phase 3: Web Frontend Development (Weeks 4-5)

**Core UI Components:**
- Upload zone with drag-and-drop
- Reader view with word wrapping
- Audio player with custom controls
- Word-by-word highlighting sync
- Table of contents drawer
- Settings panel

**Desktop Optimization:**
- Responsive CSS (desktop-first)
- Keyboard shortcuts
- Proper typography and spacing
- Progress indicators

**Mobile Accessibility:**
- Touch-friendly controls
- Responsive breakpoints
- Mobile browser testing
- Graceful degradation

### Phase 4: Integration & MVP (Week 6)

**End-to-End Testing:**
- Complete user flow: upload → process → play
- Voice switching during playback
- Position save/restore
- Multiple document management

**Documentation:**
- User guide
- API documentation
- Deployment instructions
- Developer documentation

**Polish:**
- Bug fixes
- Performance optimization
- Error handling improvements

### Future Phases (Post-MVP)

**Advanced Features:**
- Cloud storage integration (Google Drive, OneDrive)
- Analytics dashboard
- Advanced TTS parameters UI
- Document cache management UI

**PWA Implementation:**
- Service worker for offline mode
- Install prompt
- Background sync

**WebGPU Research & Implementation:**
- Browser-side Kokoro TTS inference
- Model caching in IndexedDB
- Progressive enhancement

---

## 5. Technical Specifications

### 5.1 Performance Requirements

**Desktop Browser Targets:**
- Initial load: < 3 seconds
- Document upload: < 5 seconds for typical file
- TTS generation: Real-time or faster (1.0x+)
- Word highlight latency: < 50ms
- Audio buffering: No gaps in playback

**Mobile Browser Targets:**
- Functional on iOS Safari 16+
- Functional on Chrome Android 100+
- Touch-friendly UI (min 44px tap targets)
- Responsive layout adapts gracefully

**Backend Performance:**
- Concurrent users: 3-5 simultaneous
- Processing time: < 30 seconds for 100-page document
- Memory usage: < 1GB RAM per user
- Raspberry Pi 4/5 capable

### 5.2 Browser Compatibility

**Primary Support (Desktop):**
- Chrome/Edge 100+
- Firefox 110+
- Safari 16+

**Mobile Support (Accessible):**
- iOS Safari 16+
- Chrome Android 100+
- Samsung Internet 20+

**Graceful Degradation:**
- Older browsers: Display upgrade message
- No JavaScript: Display error page
- Slow connections: Progressive loading indicators

### 5.3 Security Considerations

**File Upload Security:**
- File type validation (magic bytes)
- Size limits enforced (25MB)
- Sanitized file names
- Temporary storage with cleanup

**API Security:**
- CORS configuration for local network
- Rate limiting on endpoints
- Input validation on all routes
- SQL injection prevention (parameterized queries)

**Data Privacy:**
- All processing local (no external analytics)
- API keys stored securely (secrets management)
- Cloud sync opt-in only
- Clear data retention policy

---

## 6. Success Metrics

### MVP Success Criteria (6 weeks):
- ✅ Omniparser parses EPUB, PDF, TXT successfully
- ✅ Kokoro TTS generates audio via web interface
- ✅ Word-by-word highlighting syncs with audio
- ✅ Upload → process → play flow works end-to-end
- ✅ Desktop browsers fully functional
- ✅ Mobile browsers accessible with core features
- ✅ CLI functionality preserved and working
- ✅ All existing tests pass after reorganization

### Post-MVP Goals:
- Multi-format support (DOCX, HTML, URLs)
- ElevenLabs integration in web UI
- Live voice switching
- Position auto-save across devices
- Cloud storage sync
- PWA with offline mode
- WebGPU browser-side TTS (if feasible)

---

## 7. Open Questions & Research

### 7.1 WebGPU Feasibility Study

**Research Questions:**
1. Current browser support for WebGPU (2025 status)
2. ONNX Runtime Web + WebGPU integration path
3. Model conversion: PyTorch → ONNX → WebGPU format
4. Performance benchmarks on desktop/mobile
5. Model size vs. quality trade-offs
6. IndexedDB caching strategies
7. Fallback implementation approach

**Research Method:**
- Dedicated house-research agent session
- Document findings in separate report
- Decision point: Include in MVP or defer

**Expected Outcome:**
- Comprehensive pros/cons analysis
- Implementation complexity estimate
- Recommended approach with fallback strategy

---

## 8. Risk Assessment

### 8.1 Technical Risks

**High Risk:**
- WebGPU browser compatibility/stability
  - *Mitigation:* Server-side TTS as primary, WebGPU as enhancement
  - *Contingency:* Skip WebGPU for MVP

**Medium Risk:**
- Omniparser parsing quality across formats
  - *Mitigation:* Comprehensive testing with diverse documents
  - *Contingency:* Focus on EPUB/PDF for MVP, add formats iteratively

**Low Risk:**
- Web framework choice (vanilla JS vs. framework)
  - *Mitigation:* Vanilla JS proven for similar projects
  - *Contingency:* Well-defined component architecture

### 8.2 Project Risks

**Scope Management:**
- Temptation to add features during development
- *Mitigation:* Strict MVP focus, post-MVP roadmap
- *Action:* Regular scope reviews

**Timeline:**
- 6-week MVP timeline is ambitious
- *Mitigation:* Focus on core features only
- *Action:* Weekly progress reviews, adjust as needed

---

## 9. Conclusion

This specification provides a comprehensive roadmap for transforming epub2tts into a dual-mode CLI + web application with clean architectural separation:

- **Omniparser** handles all document parsing (separate repo)
- **epub2tts/core** orchestrates processing pipelines
- **epub2tts/audio-processing** provides abstract TTS interface (Kokoro, ElevenLabs, Hume-ready)
- **epub2tts/web** delivers desktop-optimized web experience with mobile accessibility
- **epub2tts/cli** preserves existing command-line functionality

**Key Priorities:**
1. Clean separation of concerns (parsing, orchestration, audio, UI)
2. Abstract interfaces for easy extension (Hume, future engines)
3. Desktop-first web UI with mobile accessibility
4. Preserve existing CLI functionality
5. Modular architecture for independent updates

**Next Steps:**
1. Create Omniparser project specification
2. Create implementation metaprompts for Task agents
3. Execute Phase 1: Repository split and reorganization
4. Validate everything works before proceeding to web development

---

**End of Specification Document v2.0**

*This specification reflects the revised architecture with clear separation between parsing (Omniparser), orchestration (core), audio processing (abstract engines), and user interfaces (CLI + web).*
