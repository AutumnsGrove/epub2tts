# Terminal UI Enhancement Plan
**Date Created**: 2025-09-28
**Status**: Planning Phase
**Priority**: Future Enhancement

## Overview
Implement a sophisticated terminal UI with a fixed-height split-window layout for real-time progress tracking of audio generation and image parsing processes, preventing terminal output from constantly scrolling down.

## Current State Analysis

### Existing Output System
- Standard logging output via Python's logging module
- Sequential text output that pushes content down
- Basic progress indication through log messages
- No visual separation between different pipeline processes

### Current Progress Tracking
- **TTS Pipeline**: Basic chunk processing logs in `src/pipelines/tts_pipeline.py`
- **Image Pipeline**: File-by-file processing logs in `src/pipelines/image_pipeline.py`
- **Orchestrator**: High-level coordination in `src/pipelines/orchestrator.py`

## Feature Specification

### 1. UI Layout Design

#### Terminal Window Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ epub2tts convert ./book.epub --tts --images --ui-mode split                 │  ← Original command stays here
├─────────────────────────────────────────────────────────────────────────────┤
│ ╔═══════════════════════════════╦═══════════════════════════════════════════╗ │
│ ║ Audio Generation              ║ Image Processing                          ║ │
│ ║ ─────────────────────────────╫─────────────────────────────────────────║ │
│ ║ Chapter: 5/12                 ║ Images Found: 127                         ║ │
│ ║ Section: 3/7                  ║ Processed: 89                             ║ │
│ ║ Files Generated: 43           ║ Descriptions: 89                          ║ │
│ ║ Current: ch05_s03.mp3         ║ Current: fig_5_3.png                      ║ │
│ ║ Time: 00:12:34                ║ Time: 00:08:12                            ║ │
│ ║ Speed: 2.3x realtime          ║ Avg Time: 5.5s/img                       ║ │
│ ║                               ║                                           ║ │
│ ║ [████████░░░░░░░░] 53%       ║ [██████████████░░] 70%                   ║ │
│ ║                               ║                                           ║ │
│ ║ Recent Activity:              ║ Recent Activity:                          ║ │
│ ║ ✓ ch05_s01.mp3 completed      ║ ✓ fig_5_1.png → "Graph showing..."        ║ │
│ ║ ✓ ch05_s02.mp3 completed      ║ ✓ fig_5_2.png → "Diagram of..."           ║ │
│ ║ ⚡ ch05_s03.mp3 processing...  ║ ⚡ fig_5_3.png processing...               ║ │
│ ║                               ║                                           ║ │
│ ╚═══════════════════════════════╩═══════════════════════════════════════════╝ │
│                                                                             │
│ Overall Progress: [████████████░░░░░░░░] 61% | ETA: 00:14:22               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Responsive Layout Options
- **Full Width**: Automatic column sizing based on terminal width
- **Minimum Width**: Graceful degradation for narrow terminals
- **Height Management**: Fixed height (configurable, default 20 lines)

### 2. Progress Tracking Requirements

#### Audio Generation Metrics
- **Chapter Progress**: Current chapter / total chapters
- **Section Progress**: Current section within chapter / total sections
- **File Metrics**: Files generated, current file being processed
- **Performance**: Processing speed (realtime multiplier), time elapsed
- **Queue Status**: Files pending, estimated completion time
- **Quality Metrics**: Success rate, error count

#### Image Processing Metrics
- **Discovery**: Total images found in EPUB
- **Processing**: Images processed, descriptions generated
- **Current Status**: Current image file being processed
- **Performance**: Average time per image, total time elapsed
- **Quality Metrics**: Success rate, skipped images, error count

#### Overall System Metrics
- **Combined Progress**: Overall completion percentage
- **ETA**: Estimated time to completion
- **Resource Usage**: CPU/Memory if relevant
- **Pipeline Status**: Which pipelines are active/idle

### 3. Technology Stack Analysis

#### Option A: Rich Library (Recommended)
**Pros:**
- Already imported in the project
- Excellent table and layout support
- Built-in progress bars and live updates
- Good documentation and community support
- Lightweight and performant

**Cons:**
- Less sophisticated than full TUI frameworks
- Limited input handling capabilities

**Implementation Approach:**
```python
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
```

#### Option B: Textual Framework
**Pros:**
- Full-featured TUI framework
- Advanced widget system
- Better input handling
- More sophisticated layouts

**Cons:**
- Additional dependency
- Heavier framework
- Steeper learning curve
- May be overkill for this use case

#### Option C: Custom ncurses Implementation
**Pros:**
- Maximum control and customization
- Lightweight

**Cons:**
- Complex implementation
- Platform compatibility issues
- Maintenance overhead

**Recommendation:** Rich Library - provides the right balance of features and simplicity.

### 4. Architecture Design

#### Core Components

##### A. Progress Tracker (`src/ui/progress_tracker.py`)
```python
@dataclass
class ProgressEvent:
    pipeline: str  # 'tts' or 'image'
    event_type: str  # 'start', 'progress', 'complete', 'error'
    data: Dict[str, Any]
    timestamp: float

class ProgressTracker:
    """Thread-safe progress tracking system."""

    def __init__(self):
        self.events: Queue[ProgressEvent] = Queue()
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.callbacks: List[Callable] = []

    def emit_event(self, event: ProgressEvent):
        """Emit progress event to all subscribers."""

    def subscribe(self, callback: Callable):
        """Subscribe to progress events."""

    def get_stats(self, pipeline: str) -> Dict[str, Any]:
        """Get current statistics for a pipeline."""
```

##### B. Terminal UI Manager (`src/ui/terminal_ui.py`)
```python
class TerminalUIManager:
    """Manages the split-window terminal UI."""

    def __init__(self, config: UIConfig, progress_tracker: ProgressTracker):
        self.config = config
        self.tracker = progress_tracker
        self.layout = self._create_layout()
        self.live_display = None

    def start(self):
        """Start the live UI display."""

    def stop(self):
        """Stop the UI and restore terminal."""

    def _create_layout(self) -> Layout:
        """Create the split-window layout."""

    def _update_audio_panel(self) -> Panel:
        """Generate audio progress panel."""

    def _update_image_panel(self) -> Panel:
        """Generate image progress panel."""

    def _update_overall_progress(self) -> Panel:
        """Generate overall progress panel."""
```

##### C. Configuration System Updates (`src/utils/config.py`)
```python
@dataclass
class UIConfig:
    """UI configuration settings."""
    mode: str = "classic"  # "classic" or "split-window"
    window_height: int = 20
    update_frequency: int = 100  # milliseconds
    show_stats: bool = True
    show_progress_bars: bool = True
    column_width: str = "auto"  # or specific pixel value
    show_recent_activity: bool = True
    recent_activity_lines: int = 3
```

### 5. Integration Points

#### A. Pipeline Modifications

##### TTS Pipeline Updates (`src/pipelines/tts_pipeline.py`)
```python
class KokoroTTSPipeline:
    def __init__(self, config: TTSConfig, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker

    def process_text_chunk(self, text: str, output_path: str, chunk_id: str = None) -> TTSResult:
        # Emit start event
        if self.progress_tracker:
            self.progress_tracker.emit_event(ProgressEvent(
                pipeline='tts',
                event_type='start',
                data={'chunk_id': chunk_id, 'output_path': output_path}
            ))

        # ... existing processing logic ...

        # Emit completion event
        if self.progress_tracker:
            self.progress_tracker.emit_event(ProgressEvent(
                pipeline='tts',
                event_type='complete',
                data={'chunk_id': chunk_id, 'duration': processing_time, 'file_size': file_size}
            ))
```

##### Image Pipeline Updates (`src/pipelines/image_pipeline.py`)
```python
class ImageDescriptionPipeline:
    def __init__(self, config: ImageConfig, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker

    def process_image(self, image_path: Path, context: str = "") -> ImageDescription:
        # Emit progress events similar to TTS pipeline
```

##### Orchestrator Updates (`src/pipelines/orchestrator.py`)
```python
class PipelineOrchestrator:
    def __init__(self, config: Config, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker
        # Initialize pipelines with progress tracker

    def process_epub_complete(self, epub_path: Path, output_dir: Path,
                            enable_tts: bool = False, enable_images: bool = True) -> PipelineResult:
        # Coordinate progress tracking across all pipelines
```

#### B. CLI Integration (`src/cli.py`)
```python
@click.option('--ui-mode', type=click.Choice(['classic', 'split-window']),
              default='classic', help='Terminal UI mode')
def process_epub(epub_path, output_dir, ui_mode, ...):
    """Main CLI entry point with UI mode support."""

    if ui_mode == 'split-window':
        progress_tracker = ProgressTracker()
        ui_manager = TerminalUIManager(config.ui, progress_tracker)

        # Start UI in separate thread
        ui_manager.start()

        try:
            # Process with progress tracking
            orchestrator = PipelineOrchestrator(config, progress_tracker)
            result = orchestrator.process_epub_complete(epub_path, output_dir, ...)
        finally:
            ui_manager.stop()
    else:
        # Classic mode - existing implementation
```

### 6. Implementation Timeline

#### Phase 1: Foundation (Week 1)
1. **Research and finalize UI library choice**
2. **Create progress tracking system**
3. **Implement basic layout structure**
4. **Add configuration system**

#### Phase 2: Integration (Week 2)
1. **Modify TTS pipeline for progress events**
2. **Modify image pipeline for progress events**
3. **Update orchestrator coordination**
4. **Implement UI manager**

#### Phase 3: Enhancement (Week 3)
1. **Add real-time statistics**
2. **Implement recent activity tracking**
3. **Add performance metrics**
4. **Create responsive layout system**

#### Phase 4: Testing & Polish (Week 4)
1. **Test with various EPUB sizes**
2. **Performance optimization**
3. **Error handling and edge cases**
4. **Documentation and examples**

### 7. Configuration Examples

#### Default Configuration
```yaml
ui:
  mode: "classic"
  window_height: 20
  update_frequency: 100
  show_stats: true
  show_progress_bars: true
  column_width: "auto"
  show_recent_activity: true
  recent_activity_lines: 3

  # Color scheme
  colors:
    progress_complete: "green"
    progress_incomplete: "white"
    error: "red"
    warning: "yellow"
    info: "blue"
```

#### Advanced Configuration
```yaml
ui:
  mode: "split-window"
  window_height: 25
  update_frequency: 50  # Higher frequency for smooth updates
  show_stats: true
  show_progress_bars: true
  column_width: "50%"  # Fixed split
  show_recent_activity: true
  recent_activity_lines: 5

  # Advanced features
  features:
    eta_calculation: true
    resource_monitoring: true
    detailed_timing: true
    error_highlighting: true
```

### 8. Error Handling & Edge Cases

#### Terminal Compatibility
- **Size Detection**: Handle terminals too small for split layout
- **Fallback Mode**: Auto-switch to classic mode if split not possible
- **Resize Handling**: Dynamic layout adjustment

#### Performance Considerations
- **Update Throttling**: Limit UI updates to prevent performance impact
- **Memory Management**: Clean up old progress events
- **Thread Safety**: Ensure safe access to shared progress data

#### Error States
- **Pipeline Failures**: Show error status in respective columns
- **Partial Completion**: Handle cases where one pipeline completes before other
- **Recovery**: Allow resuming from errors without UI corruption

### 9. Testing Strategy

#### Unit Tests
- Progress tracker event handling
- UI component rendering
- Configuration validation
- Error state handling

#### Integration Tests
- Full pipeline with UI enabled
- Various EPUB file sizes and types
- Error scenarios and recovery
- Terminal size variations

#### Performance Tests
- UI update frequency impact
- Memory usage with long-running processes
- Resource monitoring accuracy

### 10. Future Enhancements

#### Interactive Features
- **Pause/Resume**: Control pipeline execution
- **Priority Adjustment**: Change processing order
- **Real-time Config**: Adjust settings during execution

#### Advanced Visualizations
- **Waveform Preview**: Audio generation visualization
- **Image Thumbnails**: Show processed images
- **Processing Graph**: Visual pipeline flow

#### Export Options
- **Progress Reports**: Save processing statistics
- **Performance Analytics**: Export timing data
- **Error Logs**: Detailed error reporting

## Dependencies

### Required
- `rich>=12.0.0` - Terminal UI framework
- `threading` - Background UI updates
- `queue` - Thread-safe event passing

### Optional Enhancements
- `psutil` - System resource monitoring
- `colorama` - Cross-platform color support
- `keyboard` - Advanced input handling

## Success Criteria

1. **Functional**: Split-window layout displays correctly
2. **Real-time**: Progress updates without terminal scrolling
3. **Performant**: No significant impact on processing speed
4. **Responsive**: Works across different terminal sizes
5. **Reliable**: Graceful error handling and recovery
6. **Configurable**: Users can customize UI behavior
7. **Backward Compatible**: Classic mode still available

## Conclusion

This enhancement will significantly improve the user experience by providing clear, real-time visibility into the epub2tts processing pipeline without the distraction of constantly scrolling terminal output. The fixed-height split-window design maintains context while providing detailed progress information for both audio generation and image processing tasks.

The implementation leverages existing infrastructure while adding minimal dependencies and maintaining backward compatibility. The phased approach ensures steady progress with testable milestones at each stage.