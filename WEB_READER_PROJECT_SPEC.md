# epub2tts Web Reader - Project Specification

## Document Version: 1.0
**Last Updated:** October 10, 2025  
**Status:** Draft - Planning Phase  
**Target Platform:** Self-hosted web application (Raspberry Pi compatible)

---

## 1. Executive Summary

### 1.1 Project Overview
The epub2tts Web Reader is a browser-based expansion of the existing epub2tts CLI tool. It provides a mobile-like reading experience with integrated text-to-speech capabilities, supporting both local AI models (Kokoro TTS via WebGPU) and API-based voices (ElevenLabs, future Hume integration).

### 1.2 Core Value Proposition
- **Privacy-first**: Self-hosted, no cloud dependencies for core functionality
- **Multi-modal**: Support for text uploads, URLs, and multiple document formats
- **Lightweight**: Runs on Raspberry Pi, optimized for resource-constrained environments
- **Interactive**: Real-time word highlighting and tap-to-navigate functionality
- **Flexible**: Switch voices and adjust parameters while audio is playing

### 1.3 Target Deployment
- Raspberry Pi 4/5 (primary target)
- Any Linux/macOS/Windows machine capable of running Python 3.10+
- User-managed network access (recommended: Tailscale)
- Browser access from any device (desktop, mobile, tablet)

---

## 2. Architecture Overview

### 2.1 Technology Stack

**Backend:**
- Python 3.10+ (FastAPI framework)
- Existing epub2tts processing pipeline
- WebSocket support for real-time updates
- Background task queue (Celery or similar)

**Frontend:**
- Vanilla HTML5/CSS3/JavaScript (no frameworks)
- Web Components for modular UI
- WebGPU API for Kokoro TTS inference
- Progressive Web App (PWA) manifest
- Service Worker for caching (reach goal)

**Storage:**
- SQLite for metadata and logs
- File system for audio/text cache (last 5 items)
- Optional cloud storage integration (Google Drive, OneDrive)

### 2.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser Client                        │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │   Upload   │  │  Reader UI   │  │  Playback Ctrl   │    │
│  │  Interface │  │ (Web Comp.)  │  │   (WebGPU)       │    │
│  └─────┬──────┘  └──────┬───────┘  └────────┬─────────┘    │
│        │                 │                    │              │
└────────┼─────────────────┼────────────────────┼──────────────┘
         │                 │                    │
    ┌────▼─────────────────▼────────────────────▼────┐
    │         WebSocket + REST API (FastAPI)         │
    └────┬────────────────────────┬──────────────────┘
         │                        │
    ┌────▼──────────┐      ┌──────▼───────────────────┐
    │  Text Pipeline │      │    TTS Pipeline          │
    │  (Omniparser)  │      │  - Kokoro (local/GPU)    │
    │  - EPUB        │      │  - ElevenLabs (API)      │
    │  - PDF         │      │  - Hume (future)         │
    │  - DOCX        │      └──────────────────────────┘
    │  - Markdown    │
    │  - HTML/URLs   │
    └────┬───────────┘
         │
    ┌────▼──────────────────────────────────────────┐
    │              Storage Layer                     │
    │  - SQLite (metadata, logs, positions)         │
    │  - Cache (5 recent items: text + audio)       │
    │  - Optional: Cloud sync (Drive/OneDrive)      │
    └────────────────────────────────────────────────┘
```

### 2.3 Data Flow

```
User Upload → Backend Validation (25MB) → Omniparser → Clean Markdown
                                                              ↓
                                             SQLite Record Created
                                                              ↓
                                          Frontend Receives Chunks
                                                              ↓
                                   User Selects Voice/Parameters
                                                              ↓
                              ┌────────────────┴────────────────┐
                              ▼                                 ▼
                        Kokoro (WebGPU)                   ElevenLabs API
                        Browser-side                      Backend Request
                              │                                 │
                              └────────────┬────────────────────┘
                                           ↓
                                  Audio Streamed to Player
                                           ↓
                              Word-by-word Highlighting
                                           ↓
                           Position Auto-saved to SQLite
```

---

## 3. Core Features Specification

### 3.1 Content Ingestion

#### 3.1.1 Upload Interface
**Requirements:**
- Drag-and-drop file upload zone
- File size validation (25MB hard limit)
- Progress indicator for uploads
- Support for multiple files in queue

**Supported Formats:**
- EPUB (existing pipeline)
- PDF (new)
- DOCX (new)
- TXT (new)
- HTML (new)
- Markdown (new)

**URL Input:**
- Text field for URL entry
- General web scraping (Trafilatura or Newspaper3k)
- Extract main content, remove ads/navigation
- Handle paywalls gracefully (inform user of limitations)

#### 3.1.2 File Validation & Processing
```python
# Backend validation flow
validate_file_size(max_size=25_000_000)  # 25MB
validate_file_type(allowed_extensions)
queue_processing_task(file_id, user_preferences)
return processing_job_id
```

### 3.2 Text Processing Pipeline (Omniparser)

**Potential Separate Project:** `omniparser` - Universal document-to-markdown converter

#### 3.2.1 Processing Chain
```
Input File → Format Detector → Specialized Parser → HTML Cleaner → 
Markdown Converter → Chapter Detector → Metadata Extractor → 
Clean Markdown Output
```

#### 3.2.2 Parser Implementations

**EPUB:** (existing)
- Use current epub2tts pipeline
- EbookLib + spaCy processing

**PDF:**
- PyMuPDF or pdfplumber
- OCR fallback for image-based PDFs (Tesseract)
- Table extraction

**DOCX:**
- python-docx
- Preserve formatting markers
- Extract images to descriptions (existing VLM pipeline)

**HTML/URLs:**
- Trafilatura for content extraction
- Readability.js algorithm port
- Remove: scripts, styles, nav, ads, sidebars
- Keep: main content, images, code blocks

**Markdown/TXT:**
- Minimal processing
- Validate UTF-8 encoding
- Normalize line endings

#### 3.2.3 Common Post-Processing
- Remove excessive whitespace
- Normalize quotes and dashes
- Handle special characters (em-dashes, etc.)
- Extract and describe images (existing VLM)
- Generate table of contents
- Detect chapter boundaries

**Output Format:**
```json
{
  "document_id": "uuid",
  "title": "Document Title",
  "author": "Author Name (if available)",
  "word_count": 50000,
  "processed_text": "markdown formatted text...",
  "chapters": [
    {"id": 0, "title": "Chapter 1", "start_pos": 0, "end_pos": 5000},
    {"id": 1, "title": "Chapter 2", "start_pos": 5001, "end_pos": 10000}
  ],
  "images": [
    {"position": 2500, "description": "AI-generated description"}
  ],
  "metadata": {
    "original_format": "pdf",
    "processing_time": 3.2,
    "processor_version": "1.0.0"
  }
}
```

### 3.3 TTS Engine Integration

#### 3.3.1 Kokoro TTS (Local - WebGPU)

**Model Loading Strategy:**
```javascript
// Frontend: WebGPU model management
class KokoroEngine {
  async loadModel() {
    // Check IndexedDB for cached model
    const cached = await this.checkModelCache();
    
    if (!cached) {
      // Download model on first use
      await this.downloadModel('/api/models/kokoro-82m-webgpu');
      await this.cacheInIndexedDB();
    }
    
    // Initialize WebGPU pipeline
    this.session = await this.initWebGPU();
  }
  
  async synthesize(text, voice, parameters) {
    // Run inference in browser
    const audioBuffer = await this.session.run({
      text: text,
      voice: voice,
      speed: parameters.speed,
      pitch: parameters.pitch
    });
    
    return audioBuffer;
  }
}
```

**Model Caching:**
- Store in IndexedDB (browser-side)
- Persist across sessions
- ~80MB storage (Kokoro-82M-8bit)
- Version checking for updates

**Voice Options:**
- bf_lily (Female British - default)
- am_michael (Male American)
- bf_emma (Female British alt)
- am_sarah (Female American)

**Adjustable Parameters:**
(Behind "Advanced" menu)
- Speed: 0.5x - 2.0x
- Pitch: -5 to +5 semitones
- Temperature: 0.1 - 1.0 (variability)

#### 3.3.2 API-based Voices

**ElevenLabs Integration:** (existing)
- Backend handles API calls
- Stream audio to frontend
- Support voice library
- Handle rate limits gracefully

**Hume AI Integration:** (future)
- Similar architecture to ElevenLabs
- Emotional TTS parameters
- Backend API proxy

**Fallback Strategy:**
```python
# Backend TTS selection logic
def get_tts_engine(user_preference, kokoro_available):
    if user_preference == "local" and kokoro_available:
        return KokoroTTS()
    elif user_preference == "elevenlabs" and api_key_valid():
        return ElevenLabsTTS()
    else:
        return DefaultTTS()  # Browser speech synthesis fallback
```

#### 3.3.3 Live Voice Switching

**Implementation:**
```javascript
// Frontend: Handle voice switching during playback
async function switchVoice(newVoice) {
  const currentPosition = player.getCurrentWord();
  const remainingText = document.getRemainingText(currentPosition);
  
  // Show loading indicator
  showProcessingMessage("Switching voice...");
  
  // Re-synthesize from current position
  if (ttsMode === "local") {
    audioBuffer = await kokoro.synthesize(remainingText, newVoice);
  } else {
    audioBuffer = await fetchAPIAudio(remainingText, newVoice);
  }
  
  // Resume playback with new voice
  player.loadBuffer(audioBuffer);
  player.seek(0);
  player.play();
}
```

**Expected Behavior:**
- 1-3 second gap while processing
- Progress indicator during switch
- Maintain exact word position
- Cache both voice versions (if space allows)

### 3.4 Interactive Reader UI

#### 3.4.1 Layout Design (Mobile-First)

```
┌─────────────────────────────────────┐
│  ☰  Document Title      ⚙️  [Share] │  Header
├─────────────────────────────────────┤
│                                     │
│  The leaves descend like whispered  │  Reader
│  secrets from the trees, each one  │  Panel
│  a small rebellion against the      │  (scrollable)
│  branch that held it fast through   │
│  summer's long embrace.             │
│                                     │
│  [Rest of paragraph continues...]   │
│                                     │
├─────────────────────────────────────┤
│  ━━━━━━━━━━━━━●─────────  0:45/2:30 │  Progress
├─────────────────────────────────────┤
│   [⏮ 15]  [▶️/⏸]  [15 ⏭]   [1.0x]  │  Controls
└─────────────────────────────────────┘
```

#### 3.4.2 Text Display Features

**Word-by-Word Highlighting:**
```css
/* CSS for highlighted word */
.word {
  transition: background-color 0.1s ease;
}

.word.current {
  background-color: rgba(76, 175, 80, 0.3);
  border-radius: 2px;
  padding: 0 2px;
}

.word.played {
  color: rgba(0, 0, 0, 0.5);
}
```

**Implementation:**
```javascript
// Sync audio timing with text highlighting
class WordSyncEngine {
  constructor(text, audioTiming) {
    this.words = this.parseWords(text);
    this.timing = audioTiming; // [{ word: "The", start: 0.0, end: 0.2 }]
    this.currentIndex = 0;
  }
  
  updateHighlight(currentTime) {
    // Find current word based on audio position
    const wordIndex = this.timing.findIndex(
      t => currentTime >= t.start && currentTime < t.end
    );
    
    if (wordIndex !== this.currentIndex) {
      this.unhighlightWord(this.currentIndex);
      this.highlightWord(wordIndex);
      this.currentIndex = wordIndex;
      
      // Auto-scroll to keep current word visible
      this.scrollIntoView(wordIndex);
    }
  }
  
  highlightWord(index) {
    const wordElement = document.querySelector(`[data-word-id="${index}"]`);
    wordElement.classList.add('current');
  }
}
```

#### 3.4.3 Tap-to-Jump Navigation

**Feature:** User taps any word in the text, audio jumps to that position

```javascript
// Click handler for word navigation
document.querySelectorAll('.word').forEach(word => {
  word.addEventListener('click', function() {
    const wordIndex = parseInt(this.dataset.wordId);
    const startTime = wordTimings[wordIndex].start;
    
    // Jump audio to this position
    audioPlayer.seek(startTime);
    
    // Update UI
    updateProgressBar(startTime);
    highlightWord(wordIndex);
  });
});
```

#### 3.4.4 Table of Contents Panel

**Slide-out TOC:**
```html
<!-- TOC Drawer -->
<aside id="toc-drawer" class="drawer">
  <header>
    <h2>Table of Contents</h2>
    <button class="close-btn">×</button>
  </header>
  
  <nav>
    <ul class="chapter-list">
      <li data-chapter="0" data-start-time="0">
        <span class="chapter-number">1</span>
        <span class="chapter-title">Introduction</span>
        <span class="chapter-duration">12:30</span>
      </li>
      <!-- More chapters... -->
    </ul>
  </nav>
</aside>
```

**Behavior:**
- Tap chapter → audio jumps to start
- Show current chapter indicator
- Display estimated duration per chapter
- Smooth scroll animation when opening

### 3.5 Playback Controls

#### 3.5.1 Control Panel

**Primary Controls:**
- Play/Pause (spacebar)
- Skip backward 15s (left arrow)
- Skip forward 15s (right arrow)
- Playback speed selector (0.5x - 2.0x)

**Secondary Controls:**
(In expanded menu)
- Voice selector dropdown
- Volume slider
- Chapter skip (previous/next)
- Loop current chapter
- Sleep timer

#### 3.5.2 Progress Bar

**Features:**
- Seekable progress bar
- Current time / Total duration
- Chapter markers (visual indicators)
- Buffering indicator
- Click/drag to seek

```javascript
// Progress bar implementation
class ProgressBar {
  constructor(audioPlayer) {
    this.player = audioPlayer;
    this.bar = document.querySelector('.progress-bar');
    this.initDragHandlers();
  }
  
  initDragHandlers() {
    this.bar.addEventListener('click', (e) => {
      const percent = e.offsetX / this.bar.offsetWidth;
      const seekTime = percent * this.player.duration;
      this.player.seek(seekTime);
    });
  }
  
  update() {
    const percent = (this.player.currentTime / this.player.duration) * 100;
    this.bar.style.setProperty('--progress', `${percent}%`);
  }
}
```

#### 3.5.3 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause |
| ← | Skip back 15s |
| → | Skip forward 15s |
| ↑ | Increase speed |
| ↓ | Decrease speed |
| M | Mute/Unmute |
| C | Toggle TOC |
| S | Settings menu |
| 1-9 | Jump to 10%-90% |

### 3.6 Reading Position Auto-Save

#### 3.6.1 Position Tracking

**What to Save:**
```json
{
  "document_id": "uuid",
  "last_position": {
    "word_index": 1234,
    "audio_time": 145.5,
    "chapter_id": 2,
    "percentage": 0.23
  },
  "timestamp": "2025-10-10T08:23:00Z",
  "device_info": "mobile/Chrome"
}
```

**Save Triggers:**
- Every 5 seconds during playback
- On pause
- On voice switch
- On chapter change
- On browser close/tab close

**Implementation:**
```python
# Backend: SQLite schema
CREATE TABLE reading_positions (
    id INTEGER PRIMARY KEY,
    document_id TEXT NOT NULL,
    word_index INTEGER,
    audio_time REAL,
    chapter_id INTEGER,
    percentage REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

# Auto-save endpoint
@app.post("/api/documents/{doc_id}/position")
async def save_position(doc_id: str, position: PositionData):
    await db.execute(
        """INSERT OR REPLACE INTO reading_positions 
           (document_id, word_index, audio_time, chapter_id, percentage)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, position.word_index, position.audio_time, 
         position.chapter_id, position.percentage)
    )
```

#### 3.6.2 Resume Functionality

**On Document Load:**
```javascript
// Frontend: Auto-resume
async function loadDocument(docId) {
  const doc = await fetch(`/api/documents/${docId}`).then(r => r.json());
  const position = await fetch(`/api/documents/${docId}/position`).then(r => r.json());
  
  if (position && position.percentage > 0.05) {
    // Show resume dialog
    showResumeDialog({
      message: `Continue from ${Math.round(position.percentage * 100)}%?`,
      chapterTitle: doc.chapters[position.chapter_id].title,
      onConfirm: () => {
        seekToPosition(position);
      },
      onCancel: () => {
        startFromBeginning();
      }
    });
  }
}
```

### 3.7 Document Cache Management

#### 3.7.1 Cache Strategy

**Storage Location:**
- Backend: `./cache/documents/`
- Structure:
  ```
  cache/
  ├── documents/
  │   ├── doc-uuid-1/
  │   │   ├── text.md
  │   │   ├── metadata.json
  │   │   └── audio/
  │   │       ├── chapter-1.mp3
  │   │       └── chapter-2.mp3
  ```

**Cache Rules:**
- Keep last 5 accessed documents
- LRU eviction (Least Recently Used)
- Clear cache button in settings
- Manually pin important documents (prevent eviction)

#### 3.7.2 Cache Management

```python
# Backend: Cache manager
class DocumentCache:
    MAX_ITEMS = 5
    
    async def add_document(self, doc_id: str, files: dict):
        """Add document to cache, evict if needed."""
        cache_size = await self.get_cache_size()
        
        if cache_size >= self.MAX_ITEMS:
            # Evict LRU document (excluding pinned)
            lru_doc = await self.get_lru_document()
            await self.evict_document(lru_doc.id)
        
        # Save new document
        await self.save_to_cache(doc_id, files)
        await self.update_access_time(doc_id)
    
    async def evict_document(self, doc_id: str):
        """Remove document from cache."""
        cache_path = f"./cache/documents/{doc_id}"
        shutil.rmtree(cache_path)
        await db.execute(
            "UPDATE documents SET cached=0 WHERE id=?", (doc_id,)
        )
```

**UI for Cache Management:**
```html
<!-- Settings > Storage -->
<section class="cache-manager">
  <h3>Cached Documents (3/5)</h3>
  
  <ul class="cached-docs">
    <li class="doc-item">
      <span class="doc-title">Autumn Leaves Essay</span>
      <span class="doc-size">2.3 MB</span>
      <button class="pin-btn" title="Pin">📌</button>
      <button class="delete-btn" title="Remove">🗑️</button>
    </li>
    <!-- More items... -->
  </ul>
  
  <button class="clear-all-btn">Clear All Cache</button>
  <p class="cache-info">Total: 12.5 MB / 100 MB</p>
</section>
```

### 3.8 Cloud Storage Integration

#### 3.8.1 Supported Services

**Initial Support:**
- Google Drive
- Microsoft OneDrive

**Future Consideration:**
- Dropbox
- iCloud Drive
- Local network storage (SMB/NFS)

#### 3.8.2 OAuth Flow

```python
# Backend: OAuth configuration
OAUTH_CONFIGS = {
    "google_drive": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/drive.file"],
        "redirect_uri": "http://localhost:5000/oauth/callback/google"
    },
    "onedrive": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": ["Files.ReadWrite"],
        "redirect_uri": "http://localhost:5000/oauth/callback/microsoft"
    }
}

@app.get("/api/cloud/connect/{provider}")
async def initiate_oauth(provider: str):
    """Start OAuth flow."""
    config = OAUTH_CONFIGS[provider]
    auth_url = f"{config['auth_url']}?client_id={CLIENT_ID}&redirect_uri={config['redirect_uri']}&scope={config['scopes']}"
    return {"auth_url": auth_url}
```

#### 3.8.3 File Organization

**Cloud Storage Structure:**
```
/epub2tts-reader/
├── document-uuid-1/
│   ├── processed_text.md
│   └── audio_kokoro_bf_lily.mp3
├── document-uuid-2/
│   ├── processed_text.md
│   └── audio_elevenlabs_bella.mp3
└── metadata.json
```

**Sync Strategy:**
- Upload after TTS generation completes
- Background upload (non-blocking)
- Progress indicator
- Retry on failure (exponential backoff)
- Download on-demand when device changes

```python
# Backend: Upload to cloud
async def upload_to_cloud(doc_id: str, provider: str):
    """Upload processed document to cloud storage."""
    files = await get_document_files(doc_id)
    
    if provider == "google_drive":
        drive = GoogleDriveAPI(access_token)
        folder_id = await drive.ensure_folder("epub2tts-reader")
        
        for filename, content in files.items():
            await drive.upload_file(
                name=filename,
                content=content,
                parent_id=folder_id,
                folder=doc_id
            )
    
    # Update database
    await db.execute(
        "UPDATE documents SET cloud_synced=1, cloud_provider=? WHERE id=?",
        (provider, doc_id)
    )
```

### 3.9 Logging & Analytics

#### 3.9.1 Log Categories

**User Actions:**
- Document uploaded
- TTS voice selected
- Playback started/paused/resumed
- Chapter navigated
- Voice switched mid-playback
- Settings changed
- Cloud sync initiated

**System Events:**
- Processing job started/completed/failed
- Model loaded (Kokoro)
- API call made (ElevenLabs/Hume)
- Cache eviction occurred
- Error encountered

**Analytics Metrics:**
- Document completion rate
- Average listening speed
- Most used voices
- Processing time per format
- Error frequency
- Cloud sync success rate

#### 3.9.2 Logging Implementation

```python
# Backend: Structured logging
import structlog

logger = structlog.get_logger()

# Configure output
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

# Usage
logger.info("document_uploaded",
    document_id=doc_id,
    format="pdf",
    size_mb=2.3,
    user_agent="Mobile Safari"
)

logger.info("tts_generation_completed",
    document_id=doc_id,
    voice="bf_lily",
    duration_seconds=123.4,
    processing_time=8.7,
    engine="kokoro"
)

logger.info("playback_session",
    document_id=doc_id,
    session_duration=1834.2,  # seconds
    completion_percentage=0.67,
    voice_switches=2,
    chapter_jumps=3
)
```

**SQLite Schema:**
```sql
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    document_id TEXT,
    details JSON,
    user_agent TEXT,
    ip_address TEXT
);

CREATE INDEX idx_log_timestamp ON activity_log(timestamp);
CREATE INDEX idx_log_event_type ON activity_log(event_type);
CREATE INDEX idx_log_document ON activity_log(document_id);
```

#### 3.9.3 Analytics Dashboard

**Endpoint for Stats:**
```python
@app.get("/api/analytics/summary")
async def get_analytics_summary(days: int = 30):
    """Get usage analytics for past N days."""
    return {
        "period_days": days,
        "total_documents": await count_documents(days),
        "total_listening_hours": await sum_listening_time(days),
        "completion_rate": await avg_completion_rate(days),
        "popular_voices": await get_voice_usage(days),
        "format_breakdown": await get_format_stats(days),
        "error_rate": await calculate_error_rate(days)
    }
```

**UI Dashboard:**
```html
<!-- Settings > Analytics -->
<section class="analytics-dashboard">
  <h3>Usage Statistics (Last 30 Days)</h3>
  
  <div class="stat-grid">
    <div class="stat-card">
      <span class="stat-value">24</span>
      <span class="stat-label">Documents Processed</span>
    </div>
    
    <div class="stat-card">
      <span class="stat-value">12.5 hrs</span>
      <span class="stat-label">Total Listening Time</span>
    </div>
    
    <div class="stat-card">
      <span class="stat-value">68%</span>
      <span class="stat-label">Avg Completion Rate</span>
    </div>
  </div>
  
  <div class="chart-container">
    <canvas id="voice-usage-chart"></canvas>
  </div>
  
  <button class="export-logs-btn">Export Logs (CSV)</button>
</section>
```

---

## 4. Technical Implementation Details

### 4.1 Backend Architecture (FastAPI)

#### 4.1.1 Project Structure

```
epub2tts-web-reader/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # SQLite connection
│   │   ├── models/
│   │   │   ├── document.py
│   │   │   ├── position.py
│   │   │   └── log.py
│   │   ├── routers/
│   │   │   ├── documents.py     # Upload, process, retrieve
│   │   │   ├── tts.py           # TTS generation
│   │   │   ├── cloud.py         # Cloud sync
│   │   │   └── analytics.py    # Logs and stats
│   │   ├── services/
│   │   │   ├── omniparser.py    # Universal document parser
│   │   │   ├── tts_engine.py    # TTS abstraction layer
│   │   │   ├── cache_manager.py
│   │   │   └── cloud_storage.py
│   │   └── utils/
│   │       ├── validators.py
│   │       └── helpers.py
│   ├── cache/                   # Document cache
│   ├── uploads/                 # Temporary uploads
│   └── models/                  # Kokoro WebGPU models
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── main.css
│   │   ├── reader.css
│   │   └── mobile.css
│   ├── js/
│   │   ├── app.js
│   │   ├── components/
│   │   │   ├── reader.js
│   │   │   ├── player.js
│   │   │   └── toc.js
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── kokoro-engine.js
│   │   │   └── word-sync.js
│   │   └── utils/
│   │       └── helpers.js
│   ├── manifest.json            # PWA manifest
│   └── sw.js                    # Service worker (reach goal)
├── tests/
├── docs/
├── requirements.txt
└── README.md
```

#### 4.1.2 Key API Endpoints

**Documents:**
```python
POST   /api/documents/upload          # Upload file
POST   /api/documents/from-url        # Fetch from URL
GET    /api/documents/{doc_id}        # Get document
DELETE /api/documents/{doc_id}        # Delete document
GET    /api/documents                 # List all documents
```

**Text Processing:**
```python
POST   /api/process/{doc_id}          # Start processing job
GET    /api/process/{job_id}/status   # Check job status
```

**TTS:**
```python
POST   /api/tts/generate              # Generate audio
GET    /api/tts/voices                # List available voices
POST   /api/tts/preview               # Generate preview (first 30s)
```

**Reading Position:**
```python
POST   /api/documents/{doc_id}/position      # Save position
GET    /api/documents/{doc_id}/position      # Get last position
```

**Cloud Storage:**
```python
GET    /api/cloud/connect/{provider}         # Initiate OAuth
POST   /api/cloud/upload/{doc_id}            # Upload to cloud
GET    /api/cloud/download/{doc_id}          # Download from cloud
GET    /api/cloud/status                     # Check connection status
```

**Analytics:**
```python
GET    /api/analytics/summary                # Get stats
GET    /api/analytics/logs                   # Get logs (paginated)
POST   /api/analytics/export                 # Export logs as CSV
```

**WebSocket:**
```python
WS     /ws                                    # Real-time updates
```

#### 4.1.3 WebSocket Events

**Server → Client:**
```json
// Processing progress
{
  "type": "processing_progress",
  "job_id": "uuid",
  "progress": 0.45,
  "stage": "extracting_text",
  "message": "Extracting text from PDF..."
}

// TTS generation progress
{
  "type": "tts_progress",
  "job_id": "uuid",
  "chapter": 2,
  "total_chapters": 10,
  "progress": 0.2
}

// Processing complete
{
  "type": "processing_complete",
  "doc_id": "uuid",
  "download_url": "/api/documents/uuid/audio"
}
```

**Client → Server:**
```json
// Subscribe to job updates
{
  "type": "subscribe",
  "job_id": "uuid"
}

// Ping (keep-alive)
{
  "type": "ping"
}
```

### 4.2 Frontend Architecture (Vanilla JS)

#### 4.2.1 Web Components

**Custom Elements:**
```javascript
// Reader component
class ReaderView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }
  
  connectedCallback() {
    this.render();
    this.setupEventListeners();
  }
  
  render() {
    this.shadowRoot.innerHTML = `
      <style>
        /* Component styles */
      </style>
      <div class="reader-container">
        <!-- Reader content -->
      </div>
    `;
  }
}

customElements.define('reader-view', ReaderView);
```

**Component List:**
- `<upload-zone>` - File upload interface
- `<reader-view>` - Main reading panel
- `<audio-player>` - Playback controls
- `<toc-drawer>` - Table of contents
- `<settings-panel>` - Settings interface
- `<voice-selector>` - Voice selection dropdown
- `<progress-bar>` - Seekable progress indicator

#### 4.2.2 State Management

```javascript
// Simple state management (no framework)
class AppState {
  constructor() {
    this.state = {
      currentDocument: null,
      isPlaying: false,
      currentWord: 0,
      selectedVoice: 'bf_lily',
      playbackSpeed: 1.0,
      ttsMode: 'local', // 'local' or 'api'
      cloudConnected: false
    };
    
    this.listeners = [];
  }
  
  setState(updates) {
    this.state = { ...this.state, ...updates };
    this.notifyListeners();
  }
  
  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }
  
  notifyListeners() {
    this.listeners.forEach(listener => listener(this.state));
  }
}

// Global state instance
const appState = new AppState();
```

#### 4.2.3 Kokoro WebGPU Integration

**Research Tasks for Claude Code:**
1. Investigate WebGPU support for running Kokoro TTS
2. Explore model format conversion (PyTorch → ONNX → WebGPU)
3. Evaluate alternatives:
   - ONNX Runtime Web
   - WebNN API
   - Transformers.js (Hugging Face)
4. Benchmark performance on target devices (mobile browsers)
5. Assess model size vs. quality trade-offs
6. Determine caching strategy for model weights

**Expected Implementation Pattern:**
```javascript
// Pseudocode - actual implementation TBD
class KokoroWebGPU {
  async initialize() {
    // Check WebGPU support
    if (!navigator.gpu) {
      throw new Error("WebGPU not supported");
    }
    
    // Request GPU adapter
    const adapter = await navigator.gpu.requestAdapter();
    const device = await adapter.requestDevice();
    
    // Load model from cache or download
    const modelWeights = await this.loadModel();
    
    // Initialize inference pipeline
    this.pipeline = await this.createPipeline(device, modelWeights);
  }
  
  async synthesize(text, voice, params) {
    // Tokenize text
    const tokens = this.tokenize(text);
    
    // Run inference on GPU
    const audioData = await this.pipeline.run({
      tokens: tokens,
      voice_id: this.getVoiceId(voice),
      speed: params.speed,
      pitch: params.pitch
    });
    
    // Convert to Web Audio API format
    return this.createAudioBuffer(audioData);
  }
}
```

### 4.3 Progressive Web App (PWA) Setup

#### 4.3.1 Manifest Configuration

```json
// frontend/manifest.json
{
  "name": "epub2tts Reader",
  "short_name": "Reader",
  "description": "Self-hosted text-to-speech reader with local AI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#4CAF50",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "categories": ["productivity", "education"],
  "screenshots": [
    {
      "src": "/screenshots/reader-mobile.png",
      "sizes": "540x720",
      "type": "image/png"
    }
  ]
}
```

#### 4.3.2 Service Worker (Reach Goal)

```javascript
// frontend/sw.js
const CACHE_NAME = 'epub2tts-reader-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/css/main.css',
  '/js/app.js',
  '/js/components/reader.js',
  '/js/services/kokoro-engine.js',
  '/manifest.json'
];

// Install event - cache assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    })
  );
});
```

#### 4.3.3 Offline Functionality

**What Works Offline:**
- Browse cached documents
- Read previously loaded text
- Play cached audio
- Adjust playback settings

**What Requires Connection:**
- Upload new documents
- API-based TTS (ElevenLabs/Hume)
- Cloud sync
- Web scraping (URL input)

### 4.4 Responsive Design

#### 4.4.1 Breakpoints

```css
/* Mobile first approach */
/* Base styles: 320px - 767px */

/* Tablet */
@media (min-width: 768px) {
  .reader-container {
    max-width: 700px;
    margin: 0 auto;
  }
  
  .controls {
    padding: 1.5rem;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .app-container {
    display: grid;
    grid-template-columns: 300px 1fr 300px;
    gap: 2rem;
  }
  
  .toc-drawer {
    position: static;
    display: block;
  }
}

/* Large desktop */
@media (min-width: 1440px) {
  .reader-container {
    max-width: 900px;
  }
}
```

#### 4.4.2 Touch Interactions

```javascript
// Swipe gestures for mobile
class SwipeHandler {
  constructor(element) {
    this.element = element;
    this.startX = 0;
    this.startY = 0;
    
    this.element.addEventListener('touchstart', this.handleStart.bind(this));
    this.element.addEventListener('touchend', this.handleEnd.bind(this));
  }
  
  handleStart(e) {
    this.startX = e.touches[0].clientX;
    this.startY = e.touches[0].clientY;
  }
  
  handleEnd(e) {
    const endX = e.changedTouches[0].clientX;
    const endY = e.changedTouches[0].clientY;
    
    const deltaX = endX - this.startX;
    const deltaY = endY - this.startY;
    
    // Swipe right → open TOC
    if (deltaX > 100 && Math.abs(deltaY) < 50) {
      this.openTOC();
    }
    
    // Swipe left → close TOC
    if (deltaX < -100 && Math.abs(deltaY) < 50) {
      this.closeTOC();
    }
  }
}
```

---

## 5. Implementation Phases

### Phase 1: MVP Core (Weeks 1-3)

**Goals:**
- Basic working web interface
- Single document upload (EPUB only)
- Kokoro TTS integration (research WebGPU approach)
- Simple text display with playback
- Basic controls (play/pause/seek)

**Deliverables:**
- FastAPI backend with upload endpoint
- Frontend with file upload UI
- Kokoro integration (fallback to existing Python if WebGPU not ready)
- Audio playback with basic controls
- SQLite database setup

**Success Criteria:**
- User can upload EPUB
- Audio generates successfully
- Can play/pause/seek audio

### Phase 2: Enhanced Reader UI (Weeks 4-5)

**Goals:**
- Word-by-word highlighting
- Tap-to-jump navigation
- Table of contents panel
- Progress saving

**Deliverables:**
- Word synchronization engine
- Click handlers for navigation
- TOC drawer component
- Position auto-save

**Success Criteria:**
- Text highlights in sync with audio
- Can tap words to jump
- TOC navigation works
- Position restores on page reload

### Phase 3: Multi-Format Support (Week 6)

**Goals:**
- Omniparser development
- Support PDF, DOCX, TXT, Markdown, HTML
- URL scraping

**Deliverables:**
- Omniparser service (potentially separate repo)
- Format-specific parsers
- Web scraping with Trafilatura
- Unified markdown output

**Success Criteria:**
- All formats process correctly
- URLs extract main content
- Output quality matches EPUB

### Phase 4: Advanced Features (Weeks 7-8)

**Goals:**
- Live voice switching
- Advanced voice parameters
- Chapter navigation
- Cache management

**Deliverables:**
- Voice selector with live switching
- Advanced parameters menu (speed, pitch, etc.)
- Chapter skip buttons
- Cache UI and management logic

**Success Criteria:**
- Voice switches without position loss
- Parameters adjust audio appropriately
- Cache management works correctly

### Phase 5: Cloud Integration (Weeks 9-10)

**Goals:**
- OAuth for Google Drive/OneDrive
- Upload/download to cloud
- Sync status indicators

**Deliverables:**
- OAuth flow implementation
- Cloud storage API clients
- Background upload service
- Sync UI

**Success Criteria:**
- Can connect to cloud accounts
- Files sync successfully
- Downloads work on different devices

### Phase 6: Analytics & Polish (Weeks 11-12)

**Goals:**
- Comprehensive logging
- Analytics dashboard
- UI polish and bug fixes
- Performance optimization

**Deliverables:**
- Structured logging system
- Analytics endpoints
- Dashboard UI
- Performance improvements

**Success Criteria:**
- Logs capture all events
- Dashboard shows accurate data
- App runs smoothly on Raspberry Pi

### Phase 7: PWA & Offline (Reach Goal)

**Goals:**
- Service worker implementation
- Offline functionality
- Install prompt
- Background sync

**Deliverables:**
- Service worker with caching
- Offline UI states
- PWA manifest optimized
- Background sync for uploads

**Success Criteria:**
- Works offline after initial load
- Can install to home screen
- Uploads resume after connectivity restored

---

## 6. Technical Specifications

### 6.1 Performance Requirements

**Raspberry Pi Targets:**
- Page load: < 3 seconds on Pi 4/5
- Document processing: < 30 seconds for 100-page book
- TTS generation: Real-time or faster (1.0x+)
- Memory usage: < 1GB RAM total
- Concurrent users: 3-5 simultaneous (household use)

**Browser Targets:**
- Initial load: < 5 seconds (including model download)
- UI responsiveness: 60fps scrolling
- Word highlight latency: < 50ms
- Audio buffering: No gaps in playback

### 6.2 Browser Compatibility

**Primary Support:**
- Chrome/Edge 100+ (WebGPU support)
- Safari 16+ (iOS/macOS)
- Firefox 110+

**Graceful Degradation:**
- Older browsers → fallback to API TTS only
- No WebGPU → display upgrade message
- Slow connections → progressive enhancement

### 6.3 Security Considerations

**Network Security:**
- Recommend Tailscale for remote access
- HTTPS only in production
- CORS configuration for local network
- Rate limiting on API endpoints

**File Upload Security:**
- File type validation (magic bytes)
- Virus scanning (ClamAV optional)
- Sandboxed processing
- Size limits enforced

**Data Privacy:**
- No analytics sent externally
- All processing local
- Cloud sync opt-in only
- Clear data retention policy

### 6.4 Accessibility

**WCAG 2.1 AA Compliance:**
- Keyboard navigation fully supported
- Screen reader compatible
- High contrast mode
- Font size adjustment
- Focus indicators
- ARIA labels on controls

**Features:**
```html
<!-- Example: Accessible audio controls -->
<button 
  aria-label="Play audio" 
  aria-pressed="false"
  class="play-btn"
  tabindex="0">
  <svg aria-hidden="true"><!-- Icon --></svg>
  <span class="sr-only">Play</span>
</button>
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Backend:**
- Document parser tests (all formats)
- TTS engine tests (mocked)
- Cache manager tests
- Database operations

**Frontend:**
- Component rendering
- State management
- Audio synchronization
- Storage utilities

### 7.2 Integration Tests

- Full upload → process → TTS → playback flow
- Cloud sync end-to-end
- WebSocket communication
- OAuth flows

### 7.3 Performance Tests

- Load testing (Apache Bench)
- Memory profiling (Python)
- Browser performance (Lighthouse)
- Raspberry Pi stress tests

### 7.4 User Testing

- Usability testing with 5+ users
- Mobile device testing (iOS/Android)
- Accessibility audit
- Cross-browser verification

---

## 8. Deployment

### 8.1 Raspberry Pi Setup

**System Requirements:**
- Raspberry Pi 4 (4GB RAM) or Pi 5
- 32GB+ SD card (or SSD recommended)
- Raspberry Pi OS (64-bit)
- Python 3.10+
- Nginx (reverse proxy)

**Installation Script:**
```bash
#!/bin/bash
# setup-pi.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip nginx git

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/AutumnsGrove/epub2tts-web-reader.git
cd epub2tts-web-reader

# Install Python dependencies
uv sync

# Setup systemd service
sudo cp deployment/epub2tts.service /etc/systemd/system/
sudo systemctl enable epub2tts
sudo systemctl start epub2tts

# Configure nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/epub2tts
sudo ln -s /etc/nginx/sites-available/epub2tts /etc/nginx/sites-enabled/
sudo systemctl restart nginx

echo "Setup complete! Access at http://raspberrypi.local"
```

### 8.2 Docker Deployment (Alternative)

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies
RUN pip install uv && uv sync

# Expose port
EXPOSE 5000

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./cache:/app/cache
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=sqlite:///data/epub2tts.db
    restart: unless-stopped
```

---

## 9. Future Enhancements (Post-MVP)

### 9.1 Voice Cloning

- Integrate voice cloning (Coqui TTS, RVC)
- User uploads voice samples
- Generate custom voice model
- Use in Kokoro or API services

### 9.2 Multi-User Support

- User authentication system
- Separate libraries per user
- Shared family library option
- Usage quotas

### 9.3 Mobile Native Apps

- React Native wrapper
- Better native integrations
- Background audio support
- Lock screen controls

### 9.4 Advanced Features

- Smart highlights (key phrases)
- Note-taking while listening
- Export to podcast formats
- Social sharing (progress, quotes)
- Reading challenges/goals
- Speed reading mode (visual metronome)

### 9.5 AI Enhancements

- Automatic chapter summarization
- Key points extraction
- Quiz generation
- Personalized recommendations

---

## 10. Known Limitations & Trade-offs

### 10.1 Technical Constraints

**WebGPU Availability:**
- Not all browsers support WebGPU yet
- Fallback to API TTS may be necessary
- Performance varies by device/GPU

**Raspberry Pi Performance:**
- Concurrent user limit (3-5)
- Processing time for large documents
- Storage constraints

**Mobile Browser Limitations:**
- Background audio handling varies
- Power consumption concerns
- Storage quotas (IndexedDB)

### 10.2 Design Decisions

**No Framework:**
- More code to maintain
- Steeper learning curve initially
- Greater control and performance

**Self-Hosted Only (Initially):**
- User responsible for setup
- No centralized support
- Privacy benefits

**Cache Limit (5 Documents):**
- May frustrate heavy users
- Balance between storage and usability
- Can be adjusted in config

---

## 11. Success Metrics

### 11.1 MVP Success Criteria

- [ ] Single EPUB processes successfully
- [ ] Kokoro TTS generates audio
- [ ] Audio plays with word highlighting
- [ ] Position saves and restores
- [ ] Works on Raspberry Pi 4

### 11.2 Phase Completion Metrics

**Phase 1-3:**
- All formats parse correctly (95%+ success rate)
- Processing time < 1 minute for typical documents
- Zero crashes during normal operation

**Phase 4-6:**
- Voice switching works smoothly
- Cloud sync success rate > 98%
- Analytics capture all events

**Phase 7 (Reach Goal):**
- Offline mode functional
- PWA installable
- Lighthouse score > 90

### 11.3 User Experience Goals

- User can start listening within 2 minutes of upload
- < 5% error rate during processing
- 90%+ user satisfaction (informal survey)
- Runs stable for 24+ hours continuous operation

---

## 12. Documentation Requirements

### 12.1 User Documentation

- Quick start guide
- Format compatibility chart
- Voice selection guide
- Cloud sync setup (Google Drive/OneDrive)
- Troubleshooting common issues
- FAQ

### 12.2 Developer Documentation

- Architecture overview
- API reference
- Database schema
- Component documentation
- Contributing guidelines
- Testing guide

### 12.3 Deployment Documentation

- Raspberry Pi setup guide
- Docker deployment
- Nginx configuration
- Tailscale setup
- SSL certificate setup
- Backup and restore procedures

---

## 13. Open Questions for Claude Code

### 13.1 WebGPU Research

**Primary Questions:**
1. What's the best approach for running Kokoro TTS in browser?
   - ONNX Runtime Web + WebGPU
   - WebNN API (if stable enough)
   - Transformers.js (Hugging Face)
   - Custom WebGPU implementation

2. Model conversion process:
   - Convert PyTorch → ONNX → optimized format
   - Quantization options (8-bit, 4-bit)
   - Trade-offs in quality vs. size

3. Performance benchmarks:
   - Mobile device testing (iPhone, Android)
   - Desktop browser testing
   - Raspberry Pi browser testing

4. Fallback strategies:
   - When to use server-side TTS
   - Progressive enhancement approach
   - User communication about capabilities

### 13.2 Omniparser Architecture

**Questions:**
1. Should Omniparser be a separate package?
   - Separate repo on PyPI
   - Submodule in main project
   - Integrated directly

2. Parser priority:
   - Which formats need most work?
   - External libraries vs. custom implementation
   - OCR integration level

3. Quality metrics:
   - How to measure extraction quality?
   - Automated testing approach
   - Benchmark datasets

### 13.3 Caching Strategy

**Questions:**
1. Audio format for caching:
   - MP3 (smaller, lossy)
   - Opus (smallest, good quality)
   - WAV (largest, lossless)

2. Chunking strategy:
   - Cache by chapter or full document?
   - Pre-generate vs. on-demand
   - Streaming vs. full download

3. Eviction policies:
   - LRU confirmed?
   - Consider document size in eviction
   - User-specified priorities

---

## 14. Risk Assessment

### 14.1 Technical Risks

**High Risk:**
- WebGPU compatibility/stability
  - *Mitigation:* Robust fallback to API TTS
  - *Contingency:* Server-side Kokoro processing

**Medium Risk:**
- Raspberry Pi performance under load
  - *Mitigation:* Extensive Pi testing, queue management
  - *Contingency:* Recommend Pi 5 or higher-spec hardware

**Low Risk:**
- Cloud OAuth implementation
  - *Mitigation:* Well-documented OAuth libraries
  - *Contingency:* Start with one provider (Google Drive)

### 14.2 Project Risks

**Scope Creep:**
- Many exciting features possible
- *Mitigation:* Strict phase adherence, MVP focus
- *Action:* Document "future enhancements" separately

**Timeline:**
- 12-week estimate is aggressive
- *Mitigation:* Weekly progress reviews
- *Action:* Mark reach goals clearly

---

## 15. Conclusion

This specification provides a comprehensive roadmap for expanding epub2tts into a full-featured web reader application. The project builds on the existing CLI tool while adding a modern, mobile-first web interface with advanced features like live voice switching, word-by-word highlighting, and optional cloud sync.

**Key Priorities:**
1. Maintain privacy-first, self-hosted architecture
2. Ensure Raspberry Pi compatibility
3. Deliver smooth, mobile-like UX
4. Support multiple document formats
5. Provide flexible TTS options (local + API)

**Next Steps:**
1. Pass this specification to Claude Code
2. Begin Phase 1 MVP development
3. Research WebGPU Kokoro implementation
4. Set up development environment
5. Create initial project structure

**Success Depends On:**
- Clear communication between planning and implementation
- Regular testing on target hardware (Pi 4/5)
- User feedback during development
- Realistic timeline management
- Focus on core features before enhancements

---

## Appendix A: API Reference Schema

### Document Object
```json
{
  "id": "uuid-v4",
  "title": "Document Title",
  "author": "Author Name",
  "format": "pdf",
  "upload_date": "2025-10-10T08:23:00Z",
  "word_count": 50000,
  "estimated_duration": 3600,
  "processing_status": "completed",
  "cached": true,
  "cloud_synced": false,
  "last_position": {
    "word_index": 1234,
    "percentage": 0.23,
    "updated_at": "2025-10-10T12:00:00Z"
  },
  "chapters": [
    {
      "id": 0,
      "title": "Chapter 1",
      "start_pos": 0,
      "end_pos": 5000,
      "duration": 360
    }
  ]
}
```

### TTS Request
```json
{
  "text": "Text to synthesize...",
  "voice": "bf_lily",
  "engine": "kokoro",
  "parameters": {
    "speed": 1.0,
    "pitch": 0,
    "temperature": 0.7
  }
}
```

### Log Entry
```json
{
  "timestamp": "2025-10-10T08:23:00Z",
  "event_type": "playback_started",
  "document_id": "uuid",
  "details": {
    "voice": "bf_lily",
    "chapter": 2,
    "position": 0.23
  }
}
```

---

## Appendix B: Color Palette & Design Tokens

```css
:root {
  /* Primary Colors */
  --color-primary: #4CAF50;
  --color-primary-dark: #388E3C;
  --color-primary-light: #81C784;
  
  /* Neutral Colors */
  --color-bg: #FFFFFF;
  --color-bg-alt: #F5F5F5;
  --color-text: #212121;
  --color-text-secondary: #757575;
  
  /* Accent Colors */
  --color-accent: #FF9800;
  --color-error: #F44336;
  --color-success: #4CAF50;
  
  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  
  /* Typography */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
  
  /* Reader Specific */
  --reader-font: 'Georgia', 'Times New Roman', serif;
  --reader-line-height: 1.6;
  --reader-font-size: 1.125rem;
  
  /* Borders & Shadows */
  --border-radius: 8px;
  --box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
```

---

**End of Specification Document**

*This is a living document and will be updated as the project evolves.*