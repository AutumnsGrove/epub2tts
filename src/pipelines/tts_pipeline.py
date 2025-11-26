"""
TTS Pipeline for Kokoro integration.

This module provides the TTS pipeline for converting text to speech
using the Kokoro TTS model with advanced features and optimizations.
"""

import logging
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import soundfile as sf
from pydub import AudioSegment
from tqdm import tqdm

from utils.config import TTSConfig
from utils.logger import PerformanceLogger, ProgressLogger
from ui.progress_tracker import (
    ProgressTracker, PipelineType, EventType,
    create_start_event, create_progress_event, create_complete_event, create_error_event
)

logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    """Result of TTS processing."""
    success: bool
    audio_path: Optional[str] = None
    duration: float = 0.0
    sample_rate: int = 22050
    text_processed: str = ""
    error_message: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class AudioChunk:
    """Represents a chunk of audio with metadata."""
    text: str
    audio_data: np.ndarray
    sample_rate: int
    duration: float
    chunk_id: str


class KokoroTTSPipeline:
    """
    Pipeline for Kokoro TTS model integration with advanced features.
    """

    def __init__(self, config: TTSConfig, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize Kokoro TTS pipeline.

        Args:
            config: TTS configuration object
            progress_tracker: Optional progress tracking system

        Raises:
            RuntimeError: If Kokoro model cannot be loaded
        """
        self.config = config
        self.progress_tracker = progress_tracker
        self.model = None
        self.voice_embeddings: Dict[str, Any] = {}
        self.is_initialized = False

        logger.info(f"Initializing Kokoro TTS pipeline with model: {config.model}")
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the Kokoro TTS model."""
        try:
            logger.info(f"Loading Kokoro model: {self.config.model}")

            # Try to load MLX Kokoro model first
            if self.config.use_mlx:
                try:
                    self.model = MLXKokoroModel(self.config)
                    logger.info("Using MLX-optimized Kokoro model")
                except (ImportError, RuntimeError) as e:
                    logger.error(f"MLX Kokoro not available: {e}")
                    raise RuntimeError("TTS model unavailable - MLX Kokoro failed to load")
            else:
                logger.error("MLX disabled in config - TTS requires MLX")
                raise RuntimeError("TTS model unavailable - MLX is required but disabled")

            self.is_initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Kokoro model: {e}")
            raise RuntimeError(f"Cannot initialize TTS model: {e}")

    def process_chunk(self, text: str, output_path: str, chunk_id: str = "") -> TTSResult:
        """
        Process a single text chunk through Kokoro TTS.

        Args:
            text: Text to convert to speech
            output_path: Path for output audio file
            chunk_id: Optional identifier for this chunk

        Returns:
            TTSResult with processing information
        """
        if not self.is_initialized:
            return TTSResult(
                success=False,
                error_message="TTS model not initialized"
            )

        start_time = time.time()

        # Emit start event
        if self.progress_tracker:
            self.progress_tracker.emit_event(create_start_event(
                PipelineType.TTS,
                total_items=1,
                current_item=chunk_id or "Unknown chunk"
            ))

        try:
            with PerformanceLogger(f"TTS chunk processing: {chunk_id}"):
                # Preprocess text for TTS
                processed_text = self._preprocess_text(text)

                if not processed_text.strip():
                    logger.warning(f"Empty text after preprocessing: {chunk_id}")
                    return TTSResult(
                        success=False,
                        error_message="Empty text after preprocessing"
                    )

                # Generate audio
                audio_data = self.model.synthesize(
                    processed_text,
                    voice=self.config.voice,
                    speed=self.config.speed,
                    pitch=self.config.pitch
                )

                # Save audio file
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                if self.config.output_format.lower() == 'wav':
                    sf.write(
                        str(output_path),
                        audio_data,
                        self.config.sample_rate
                    )
                elif self.config.output_format.lower() == 'mp3':
                    # Convert to MP3 using pydub
                    self._save_as_mp3(audio_data, output_path)
                else:
                    raise ValueError(f"Unsupported output format: {self.config.output_format}")

                duration = len(audio_data) / self.config.sample_rate
                processing_time = time.time() - start_time

                logger.debug(
                    f"TTS chunk completed: {chunk_id} "
                    f"({duration:.2f}s audio, {processing_time:.2f}s processing)"
                )

                # Emit completion event
                if self.progress_tracker:
                    self.progress_tracker.emit_event(create_complete_event(
                        PipelineType.TTS,
                        current_item=chunk_id or "Unknown chunk",
                        duration=duration,
                        processing_time=processing_time,
                        file_size=output_path.stat().st_size if output_path.exists() else 0
                    ))

                return TTSResult(
                    success=True,
                    audio_path=str(output_path),
                    duration=duration,
                    sample_rate=self.config.sample_rate,
                    text_processed=processed_text,
                    processing_time=processing_time
                )

        except Exception as e:
            error_msg = f"TTS processing failed for chunk {chunk_id}: {e}"
            logger.error(error_msg)

            # Emit error event
            if self.progress_tracker:
                self.progress_tracker.emit_event(create_error_event(
                    PipelineType.TTS,
                    error_message=error_msg,
                    current_item=chunk_id or "Unknown chunk"
                ))

            return TTSResult(
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

    def batch_process(
        self,
        text_chunks: List[Dict[str, str]],
        output_dir: Path,
        parallel: bool = True
    ) -> List[TTSResult]:
        """
        Process multiple text chunks with progress tracking.

        Args:
            text_chunks: List of dictionaries with 'text' and 'id' keys
            output_dir: Output directory for audio files
            parallel: Whether to use parallel processing

        Returns:
            List of TTSResult objects
        """
        if not self.is_initialized:
            logger.error("TTS model not initialized")
            return []

        logger.info(f"Starting batch TTS processing: {len(text_chunks)} chunks")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Emit start event for batch processing
        if self.progress_tracker:
            self.progress_tracker.emit_event(create_start_event(
                PipelineType.TTS,
                total_items=len(text_chunks),
                current_item=f"Batch processing {len(text_chunks)} chunks"
            ))

        results = []
        progress = ProgressLogger("TTS processing", len(text_chunks))

        if parallel and len(text_chunks) > 1 and not getattr(self.model, 'force_sequential', False):
            # Parallel processing (only if model allows it)
            max_workers = min(2, len(text_chunks))  # Reduced for Metal stability
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_chunk = {}
                for chunk in text_chunks:
                    chunk_id = chunk.get('id', f"chunk_{len(future_to_chunk)}")
                    output_path = output_dir / f"{chunk_id}.{self.config.output_format}"

                    future = executor.submit(
                        self.process_chunk,
                        chunk['text'],
                        str(output_path),
                        chunk_id
                    )
                    future_to_chunk[future] = chunk

                # Collect results
                for future in as_completed(future_to_chunk):
                    result = future.result()
                    results.append(result)
                    progress.update()

                    # Emit progress event
                    if self.progress_tracker:
                        self.progress_tracker.emit_event(create_progress_event(
                            PipelineType.TTS,
                            completed_items=len(results),
                            total_items=len(text_chunks),
                            current_item=f"Processed {len(results)}/{len(text_chunks)} chunks"
                        ))

        else:
            # Sequential processing
            for i, chunk in enumerate(text_chunks):
                chunk_id = chunk.get('id', f"chunk_{i}")
                output_path = output_dir / f"{chunk_id}.{self.config.output_format}"

                result = self.process_chunk(
                    chunk['text'],
                    str(output_path),
                    chunk_id
                )
                results.append(result)
                progress.update()

                # Emit progress event
                if self.progress_tracker:
                    self.progress_tracker.emit_event(create_progress_event(
                        PipelineType.TTS,
                        completed_items=len(results),
                        total_items=len(text_chunks),
                        current_item=f"Processed {len(results)}/{len(text_chunks)} chunks"
                    ))

        progress.finish()

        # Log summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        logger.info(
            f"Batch TTS processing completed: "
            f"{len(successful)} successful, {len(failed)} failed"
        )

        return results

    def merge_audio_files(
        self,
        audio_files: List[str],
        output_path: str,
        crossfade_ms: int = 100
    ) -> bool:
        """
        Merge multiple audio files into a single audiobook.

        Args:
            audio_files: List of audio file paths to merge
            output_path: Output path for merged audio
            crossfade_ms: Crossfade duration between files in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Merging {len(audio_files)} audio files to {output_path}")

            if not audio_files:
                logger.warning("No audio files to merge")
                return False

            # Load first audio file
            combined = AudioSegment.from_file(audio_files[0])

            # Add remaining files with crossfade
            for audio_file in audio_files[1:]:
                if not Path(audio_file).exists():
                    logger.warning(f"Audio file not found: {audio_file}")
                    continue

                next_audio = AudioSegment.from_file(audio_file)

                if crossfade_ms > 0:
                    combined = combined.append(next_audio, crossfade=crossfade_ms)
                else:
                    combined = combined + next_audio

            # Export merged audio
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_path.suffix.lower() == '.mp3':
                combined.export(str(output_path), format="mp3", bitrate="192k")
            elif output_path.suffix.lower() == '.wav':
                combined.export(str(output_path), format="wav")
            else:
                # Default to mp3
                combined.export(str(output_path), format="mp3", bitrate="192k")

            duration_minutes = len(combined) / 1000 / 60
            logger.info(f"Audio merge completed: {duration_minutes:.1f} minutes")

            return True

        except Exception as e:
            logger.error(f"Failed to merge audio files: {e}")
            return False

    def process_chapters(
        self,
        chapters: List[Dict[str, str]],
        output_dir: Path,
        merge_final: bool = True
    ) -> Dict[str, Any]:
        """
        Process chapters and optionally merge into final audiobook.

        Args:
            chapters: List of chapter dictionaries with 'title', 'content', etc.
            output_dir: Output directory
            merge_final: Whether to merge chapters into single audiobook

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing {len(chapters)} chapters for TTS")

        # Prepare text chunks from chapters
        text_chunks = []
        for i, chapter in enumerate(chapters):
            # Create meaningful chapter ID based on actual chapter number if available
            chapter_num = chapter.get('chapter_num', i + 1)
            chapter_title = chapter.get('title', f'Chapter {chapter_num}')

            # Clean and shorten title for filename
            clean_title = "".join(c for c in chapter_title if c.isalnum() or c in ' -_')
            clean_title = clean_title.replace(' ', '_')[:20]  # Limit length

            chunk_id = f"chapter_{chapter_num:03d}_{clean_title}"

            text_chunks.append({
                'id': chunk_id,
                'text': chapter['content'],
                'title': chapter_title,
                'chapter_num': chapter_num
            })

        # Process all chunks
        chapter_dir = output_dir / "chapters"
        results = self.batch_process(text_chunks, chapter_dir, parallel=True)

        # Collect successful audio files
        successful_results = [r for r in results if r.success]
        audio_files = [r.audio_path for r in successful_results]

        processing_summary = {
            'total_chapters': len(chapters),
            'successful_chapters': len(successful_results),
            'failed_chapters': len(results) - len(successful_results),
            'total_audio_duration': sum(r.duration for r in successful_results),
            'chapter_files': audio_files,
            'merged_file': None
        }

        # Merge into final audiobook if requested and we have audio files
        if merge_final and audio_files:
            merged_file = output_dir / f"audiobook.{self.config.output_format}"
            if self.merge_audio_files(audio_files, str(merged_file)):
                processing_summary['merged_file'] = str(merged_file)
                logger.info(f"Final audiobook created: {merged_file}")
            else:
                logger.error("Failed to create merged audiobook")

        return processing_summary

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for optimal TTS synthesis.

        Removes epub2tts markers and cleans text for Kokoro TTS.
        Note: Kokoro does NOT support SSML tags, so we strip markers entirely
        rather than converting them to SSML.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text optimized for TTS
        """
        # Remove or replace TTS-unfriendly patterns
        processed = text

        # Handle pause markers - REMOVE entirely (Kokoro doesn't support SSML)
        # Pauses are natural from punctuation; adding silence can be done post-processing
        processed = re.sub(r'\[PAUSE:\s*[\d.]+\]', ' ', processed)

        # Handle emphasis markers - keep the text content, remove markers
        # Kokoro doesn't support SSML emphasis tags
        processed = re.sub(r'\[EMPHASIS_STRONG:\s*([^\]]+)\]', r'\1', processed)
        processed = re.sub(r'\[EMPHASIS_MILD:\s*([^\]]+)\]', r'\1', processed)

        # Handle dialogue markers - remove entirely
        processed = re.sub(r'\[DIALOGUE_START\]', '', processed)
        processed = re.sub(r'\[DIALOGUE_END\]', '', processed)

        # Handle chapter markers - convert to spoken text
        processed = re.sub(r'\[CHAPTER_START:\s*([^\]]+)\]', r'Chapter: \1. ', processed)

        # Handle image descriptions - convert to spoken description
        processed = re.sub(r'\[IMAGE:\s*([^\]]+)\]', r'Image description: \1. ', processed)
        processed = re.sub(r'\[IMAGE DESCRIPTION:\s*([^\]]+)\]', r'Image description: \1. ', processed)

        # Handle header markers
        processed = re.sub(r'\[HEADER_END\]', '. ', processed)

        # Remove any remaining bracket markers that weren't caught
        processed = re.sub(r'\[[A-Z_]+(?::\s*[^\]]+)?\]', ' ', processed)

        # Clean up extra whitespace
        processed = re.sub(r'\s+', ' ', processed).strip()

        return processed

    def _save_as_mp3(self, audio_data: np.ndarray, output_path: Path) -> None:
        """Save audio data as MP3 file."""
        # First save as temporary WAV
        temp_wav = output_path.with_suffix('.temp.wav')
        sf.write(str(temp_wav), audio_data, self.config.sample_rate)

        # Convert to MP3
        audio = AudioSegment.from_wav(str(temp_wav))
        mp3_path = output_path.with_suffix('.mp3')
        audio.export(str(mp3_path), format="mp3", bitrate="192k")

        # Clean up temp file
        temp_wav.unlink()

    def get_voice_info(self) -> Dict[str, Any]:
        """Get information about available voices."""
        if not self.is_initialized:
            return {"error": "Model not initialized"}

        return {
            "current_voice": self.config.voice,
            "available_voices": self.model.get_available_voices() if hasattr(self.model, 'get_available_voices') else [],
            "sample_rate": self.config.sample_rate,
            "output_format": self.config.output_format
        }


class MLXKokoroModel:
    """Real Kokoro model using direct Kokoro library with MLX backend."""

    def __init__(self, config: TTSConfig):
        """Initialize MLX Kokoro model."""
        try:
            # Suppress phonemizer warnings that are common with TTS models
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning, module="phonemizer")
            warnings.filterwarnings("ignore", message=".*word count mismatch.*")
            warnings.filterwarnings("ignore", message=".*phonemizer.*")

            self.config = config
            self.model_path = config.model_path
            self.voice = config.voice

            # Check if we have a local model with safetensors
            local_model_available = self._check_local_model()

            # Try to import Kokoro directly first (preferred for local models)
            try:
                from kokoro import KPipeline
                if local_model_available:
                    logger.info(f"Local Kokoro model found at: {self.model_path}")
                    # Initialize with language code 'a' and repo_id pointing to local model
                    self.pipeline = KPipeline('a', repo_id=self.model_path)
                    self.use_mlx_audio = False
                    logger.info("Using direct Kokoro backend with local model")
                else:
                    logger.warning("Local model not found, trying HuggingFace path")
                    # For HuggingFace models, use the model path if it looks like a repo
                    if self.model_path.startswith('hexgrad/') or '/' in self.model_path:
                        self.pipeline = KPipeline('a', repo_id=self.model_path)
                    else:
                        self.pipeline = KPipeline('a')
                    self.use_mlx_audio = False
                    logger.info("Using direct Kokoro backend with HuggingFace model")
            except ImportError as e:
                logger.warning(f"Direct Kokoro not available: {e}")
                # Fall back to MLX-Audio if available
                try:
                    from mlx_audio.tts.generate import generate_audio
                    self.generate_func = generate_audio
                    self.use_mlx_audio = True
                    if local_model_available:
                        logger.warning("MLX-Audio doesn't support local models, may have issues")
                    logger.info("Using MLX-Audio backend (HuggingFace models only)")
                except ImportError as e2:
                    logger.error(f"Neither Kokoro nor MLX-Audio available: {e}, {e2}")
                    raise RuntimeError("No TTS backend available")
            except Exception as e:
                logger.error(f"Error initializing Kokoro pipeline: {e}")
                # Try to fall back to MLX-Audio
                try:
                    from mlx_audio.tts.generate import generate_audio
                    self.generate_func = generate_audio
                    self.use_mlx_audio = True
                    logger.info("Falling back to MLX-Audio backend")
                except ImportError:
                    raise RuntimeError(f"Kokoro initialization failed and no fallback available: {e}")

            # Metal framework stability settings
            self.force_sequential = True  # Force sequential processing for MLX
            self.max_retries = 3
            self.degradation_level = 0  # 0=MLX, 1=Direct, 2=Mock
            self.metal_error_count = 0

            logger.info("Initialized MLX Kokoro model successfully")
        except ImportError as e:
            logger.error(f"Failed to import Kokoro libraries: {e}")
            raise RuntimeError("Kokoro TTS not available")
        except Exception as e:
            logger.error(f"Unexpected error during Kokoro initialization: {e}")
            raise RuntimeError(f"Kokoro TTS initialization failed: {e}")

    def _check_local_model(self) -> bool:
        """Check if local model files exist."""
        from pathlib import Path

        model_path = Path(self.model_path)

        # Check for safetensors file
        if model_path.is_dir():
            safetensors_files = list(model_path.glob("*.safetensors"))
            if safetensors_files:
                logger.info(f"Found safetensors files: {[f.name for f in safetensors_files]}")
                return True
            else:
                logger.warning(f"No safetensors files found in {model_path}")
                return False
        elif model_path.is_file() and model_path.suffix == '.safetensors':
            logger.info(f"Direct safetensors file: {model_path}")
            return True
        else:
            logger.info(f"Model path {model_path} doesn't appear to be a local model")
            return False

    def synthesize(
        self,
        text: str,
        voice: str = "bf_lily",
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> np.ndarray:
        """
        Generate audio using Kokoro model with Metal framework stability.

        Args:
            text: Text to synthesize
            voice: Voice to use (default: bf_lily)
            speed: Speech speed multiplier
            pitch: Pitch adjustment (note: may not be supported)

        Returns:
            Audio data as numpy array
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Clear GPU resources before synthesis to prevent Metal errors
                self._cleanup_metal_resources()

                # Prefer direct Kokoro for local models
                if self.degradation_level == 0 and not self.use_mlx_audio:
                    return self._try_direct_kokoro(text, voice, speed, pitch)
                elif attempt == 0 and self.degradation_level == 0 and self.use_mlx_audio:
                    return self._try_mlx_audio(text, voice, speed, pitch)
                elif self.degradation_level <= 1:
                    return self._try_direct_kokoro(text, voice, speed, pitch)
                else:
                    raise RuntimeError("All TTS methods failed")

            except Exception as e:
                if self._handle_metal_error(e):
                    logger.warning(f"Metal error handled, degrading to level {self.degradation_level}")
                    continue

                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries:
                    logger.error("All synthesis attempts failed")
                    raise RuntimeError(f"TTS synthesis failed after {self.max_retries + 1} attempts: {e}")

                # Wait before retry with exponential backoff
                import time
                time.sleep(2 ** attempt)

        # This shouldn't be reached, but just in case
        raise RuntimeError("TTS synthesis failed unexpectedly")

    def _cleanup_metal_resources(self) -> None:
        """Clean up Metal/GPU resources to prevent framework errors."""
        try:
            import gc

            # Try to clear MLX memory if available
            try:
                import mlx.core as mx
                # Force synchronization before cleanup
                mx.eval([])
                # Clear any pending operations
                mx.clear_cache()
                # Small delay to allow Metal framework to finish pending operations
                time.sleep(0.1)
            except (ImportError, AttributeError) as e:
                logger.debug(f"MLX memory cleanup not available: {e}")

            # Force garbage collection
            gc.collect()

            # Additional delay for Metal framework stability
            time.sleep(0.05)

        except Exception as e:
            logger.debug(f"Resource cleanup warning: {e}")

    def _handle_metal_error(self, error: Exception) -> bool:
        """Handle Metal framework specific errors."""
        error_str = str(error)
        metal_keywords = ["MTLCommandBuffer", "Metal", "failed assertion", "Completed handler", "commit call"]

        if any(keyword in error_str for keyword in metal_keywords):
            logger.error(f"Metal framework error detected: {error_str[:100]}...")
            self.metal_error_count += 1

            # Immediate cleanup on Metal errors
            try:
                self._cleanup_metal_resources()
            except:
                pass

            if self.metal_error_count >= 3:
                raise RuntimeError("Too many Metal framework errors, TTS unavailable")
            else:
                self.degradation_level = 1  # Switch to direct Kokoro
                self.use_mlx_audio = False
                logger.warning("Metal error, switching to CPU-only processing")

            return True
        return False

    def _try_mlx_audio(self, text: str, voice: str, speed: float, pitch: float) -> np.ndarray:
        """Try MLX-Audio synthesis with improved file handling."""
        logger.debug(f"Attempting MLX-Audio synthesis: '{text[:50]}...'")

        # MLX-Audio expects HuggingFace repo format, not local paths
        # Skip MLX-Audio if we're using local models
        if self.model_path.startswith('./') or self.model_path.startswith('/'):
            logger.debug("Local model path detected, skipping MLX-Audio")
            raise RuntimeError("MLX-Audio does not support local model paths")

        # Create dedicated output directory
        from pathlib import Path
        import tempfile
        import os
        import time
        import glob

        # Use a dedicated temp directory that's isolated from main directory
        with tempfile.TemporaryDirectory(prefix="mlx_audio_") as temp_dir:
            temp_dir_path = Path(temp_dir)
            output_path = temp_dir_path / f"audio_{hash(text)}.wav"

            try:
                # Change to temp directory to contain any files created by MLX-Audio
                original_cwd = os.getcwd()
                os.chdir(temp_dir)

                try:
                    audio_data = self.generate_func(
                        text=text,
                        model_path=self.model_path,
                        voice=voice,
                        speed=speed,
                        output_path=str(output_path) if hasattr(self.generate_func, '__code__') and 'output_path' in self.generate_func.__code__.co_varnames else None
                    )

                    # MLX-Audio may return None and save to file instead
                    if audio_data is None:
                        logger.debug("MLX-Audio returned None, looking for generated file")

                        # Check specific output path first
                        if output_path.exists():
                            import soundfile as sf
                            audio_data, sample_rate = sf.read(str(output_path))
                            logger.debug(f"Loaded audio from specified path: {audio_data.shape}, {sample_rate}Hz")
                        else:
                            # Look for recently created audio files in temp directory only
                            audio_files = list(temp_dir_path.glob("audio_*.wav"))
                            if audio_files:
                                latest_file = max(audio_files, key=lambda x: x.stat().st_ctime)
                                # Check if file was created recently (within last 10 seconds)
                                if time.time() - latest_file.stat().st_ctime < 10:
                                    logger.debug(f"Loading audio from MLX-Audio generated file: {latest_file}")
                                    import soundfile as sf
                                    audio_data, sample_rate = sf.read(str(latest_file))
                                    logger.debug(f"Loaded audio: {audio_data.shape}, {sample_rate}Hz")
                                else:
                                    audio_data = None
                            else:
                                audio_data = None

                    if audio_data is None:
                        raise RuntimeError("MLX-Audio failed to generate audio data")

                    # Convert to numpy array if needed
                    if not isinstance(audio_data, np.ndarray):
                        audio_data = np.array(audio_data)

                    logger.debug("MLX-Audio synthesis successful")
                    return audio_data.astype(np.float32)

                finally:
                    # Always restore original working directory
                    os.chdir(original_cwd)

            except Exception as e:
                logger.warning(f"MLX-Audio synthesis failed: {e}")
                raise

    def _try_direct_kokoro(self, text: str, voice: str, speed: float, pitch: float) -> np.ndarray:
        """Try direct Kokoro synthesis with improved text handling."""
        logger.debug(f"Using direct Kokoro: '{text[:50]}...'")

        # Initialize direct Kokoro if not already done
        if not hasattr(self, 'pipeline'):
            from kokoro import KPipeline
            logger.info("Initializing direct Kokoro pipeline for fallback")
            # Initialize with language code and repo_id if local model available
            from pathlib import Path
            if Path(self.model_path).exists():
                self.pipeline = KPipeline('a', repo_id=self.model_path)
            else:
                self.pipeline = KPipeline('a')  # 'a' for autodetect

        # Clean and chunk text to avoid tokenization issues
        cleaned_text = self._clean_text_for_tts(text)

        # Split very long text into smaller chunks to avoid index errors
        max_chunk_length = 500  # chars
        if len(cleaned_text) > max_chunk_length:
            chunks = self._split_text_for_synthesis(cleaned_text, max_chunk_length)
            audio_segments = []
            failed_chunks = 0
            total_chunks = len(chunks)

            logger.info(f"Processing {total_chunks} text chunks (each ~{max_chunk_length} chars)")

            for chunk_idx, chunk in enumerate(chunks):
                if chunk.strip():  # Skip empty chunks
                    try:
                        voice_pack = self.pipeline.load_voice(voice)
                        ps, tokens = self.pipeline.g2p(chunk.strip())

                        # Check if phonemes/tokens are reasonable length
                        if len(tokens) > 2000:  # Arbitrary safety limit
                            logger.warning(f"Chunk {chunk_idx+1}/{total_chunks}: tokens too long ({len(tokens)}), skipping")
                            failed_chunks += 1
                            continue

                        output = self.pipeline.infer(self.pipeline.model, ps, voice_pack)
                        chunk_audio = output.audio.numpy() if hasattr(output.audio, 'numpy') else output.audio
                        audio_segments.append(chunk_audio)
                        logger.debug(f"Chunk {chunk_idx+1}/{total_chunks}: generated {len(chunk_audio)} samples")
                    except IndexError as e:
                        logger.warning(f"Chunk {chunk_idx+1}/{total_chunks}: index error - '{chunk[:30]}...' - {e}")
                        failed_chunks += 1
                        continue
                    except Exception as e:
                        logger.warning(f"Chunk {chunk_idx+1}/{total_chunks}: error - '{chunk[:30]}...' - {e}")
                        failed_chunks += 1
                        continue
                else:
                    logger.debug(f"Chunk {chunk_idx+1}/{total_chunks}: empty, skipping")

            # Log summary
            success_count = len(audio_segments)
            logger.info(f"TTS chunk processing: {success_count}/{total_chunks} succeeded, {failed_chunks} failed")

            if not audio_segments:
                raise RuntimeError(f"No audio segments generated successfully (0/{total_chunks} chunks)")

            if failed_chunks > 0:
                logger.warning(f"Some chunks failed: {failed_chunks}/{total_chunks} - audio may be incomplete")

            # Concatenate audio segments
            audio_data = np.concatenate(audio_segments)
        else:
            voice_pack = self.pipeline.load_voice(voice)
            ps, tokens = self.pipeline.g2p(cleaned_text)

            # Check if phonemes/tokens are reasonable length
            if len(tokens) > 2000:  # Arbitrary safety limit
                raise RuntimeError(f"Text tokens too long ({len(tokens)}) for synthesis")

            output = self.pipeline.infer(self.pipeline.model, ps, voice_pack)
            audio_data = output.audio.numpy() if hasattr(output.audio, 'numpy') else output.audio

        # Adjust speed if needed
        if speed != 1.0:
            from scipy import signal
            audio_data = signal.resample(audio_data, int(len(audio_data) / speed))

        # Convert to numpy array if needed
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)

        return audio_data.astype(np.float32)

    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text to avoid TTS tokenization issues."""

        # Remove problematic characters that can cause tokenization issues
        cleaned = text

        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Remove or replace problematic punctuation that confuses tokenizers
        cleaned = re.sub(r'[^\w\s\.\,\!\?\;\:\-\'\"]', ' ', cleaned)

        # Remove multiple punctuation marks in a row
        cleaned = re.sub(r'[\.]{3,}', '...', cleaned)
        cleaned = re.sub(r'[!]{2,}', '!', cleaned)
        cleaned = re.sub(r'[\?]{2,}', '?', cleaned)

        # Ensure proper spacing around punctuation
        cleaned = re.sub(r'([\.!?])\s*([A-Z])', r'\1 \2', cleaned)

        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

    def _split_text_for_synthesis(self, text: str, max_length: int) -> List[str]:
        """Split text into smaller chunks for synthesis."""

        chunks = []
        current_chunk = ""

        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            # If adding this sentence would exceed max length, start new chunk
            if len(current_chunk) + len(sentence) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Sentence itself is too long, split by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > max_length:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                # Word itself is too long, truncate it
                                chunks.append(word[:max_length])
                        else:
                            temp_chunk += " " + word if temp_chunk else word
                    if temp_chunk:
                        current_chunk = temp_chunk
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        # Add final chunk if exists
        if current_chunk:
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def get_available_voices(self) -> List[str]:
        """Get list of available voices."""
        # Get voices from the MLX model directory if available
        try:
            voices_dir = Path(self.model_path) / "voices"
            if voices_dir.exists():
                voices = [f.stem for f in voices_dir.glob("*.pt")]
                return sorted(voices)
        except Exception:
            pass

        # Default voices list
        return ["bf_lily", "af_heart", "bf_emma", "am_adam", "af_sarah", "bf_grace"]


def create_tts_pipeline(config: TTSConfig, progress_tracker: Optional[ProgressTracker] = None):
    """
    Factory function to create TTS pipeline based on configuration and available resources.

    Args:
        config: TTS configuration
        progress_tracker: Optional progress tracking system

    Returns:
        Initialized TTS pipeline (KokoroTTSPipeline, ElevenLabsTTSPipeline, or HumeTTSPipeline)

    Raises:
        RuntimeError: If no TTS engine is available
    """
    from utils.secrets import has_elevenlabs_api_key, has_hume_api_key

    # Determine which engine to use
    requested_engine = getattr(config, 'engine', 'kokoro')

    if requested_engine == 'elevenlabs':
        # User explicitly requested ElevenLabs
        if has_elevenlabs_api_key():
            try:
                from pipelines.elevenlabs_tts import create_elevenlabs_tts_pipeline
                logger.info("Creating ElevenLabs TTS pipeline (user requested)")
                return create_elevenlabs_tts_pipeline(config, progress_tracker)
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs TTS: {e}")
                logger.info("Falling back to Kokoro TTS")
                # Fall back to Kokoro
                return KokoroTTSPipeline(config, progress_tracker)
        else:
            logger.warning(
                "ElevenLabs TTS requested but no API key found. "
                "Add 'elevenlabs_api_key' to secrets.json or set ELEVENLABS_API_KEY environment variable. "
                "Falling back to Kokoro TTS."
            )
            return KokoroTTSPipeline(config, progress_tracker)

    elif requested_engine == 'hume':
        # User explicitly requested Hume
        if has_hume_api_key():
            try:
                from pipelines.hume_tts_pipeline import create_hume_tts_pipeline
                logger.info("Creating Hume TTS pipeline (user requested)")
                return create_hume_tts_pipeline(config, progress_tracker)
            except Exception as e:
                logger.error(f"Failed to initialize Hume TTS: {e}")
                logger.info("Falling back to Kokoro TTS")
                return KokoroTTSPipeline(config, progress_tracker)
        else:
            logger.warning(
                "Hume TTS requested but no API key found. "
                "Add 'hume_api_key' to secrets.json or set HUME_API_KEY environment variable. "
                "Falling back to Kokoro TTS."
            )
            return KokoroTTSPipeline(config, progress_tracker)

    elif requested_engine == 'kokoro':
        # User explicitly requested Kokoro
        logger.info("Creating Kokoro TTS pipeline (user requested)")
        return KokoroTTSPipeline(config, progress_tracker)

    else:
        # Default to Kokoro TTS (preferred local engine)
        logger.info("Using Kokoro TTS (default engine)")
        return KokoroTTSPipeline(config, progress_tracker)