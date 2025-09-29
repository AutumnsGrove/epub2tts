"""
ElevenLabs TTS Pipeline for epub2tts.

This module provides a TTS pipeline for converting text to speech
using the ElevenLabs API with advanced features and optimizations.
"""

import logging
import os
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from tqdm import tqdm

# ElevenLabs imports
from elevenlabs.client import ElevenLabs, AsyncElevenLabs
from elevenlabs import Voice, VoiceSettings

from utils.config import TTSConfig
from utils.logger import PerformanceLogger, ProgressLogger
from utils.secrets import load_secrets
from ui.progress_tracker import (
    ProgressTracker, PipelineType, EventType,
    create_start_event, create_progress_event, create_complete_event, create_error_event
)

logger = logging.getLogger(__name__)


@dataclass
class ElevenLabsTTSResult:
    """Result of ElevenLabs TTS processing."""
    success: bool
    audio_path: Optional[str] = None
    duration: float = 0.0
    text_processed: str = ""
    error_message: Optional[str] = None
    processing_time: float = 0.0
    characters_processed: int = 0
    api_calls_made: int = 0


@dataclass
class ElevenLabsConfig:
    """Configuration for ElevenLabs TTS."""
    api_key: str
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # Default voice
    model_id: str = "eleven_multilingual_v2"  # Recommended model
    output_format: str = "mp3_44100_128"
    stability: float = 0.5
    similarity_boost: float = 0.5
    style: float = 0.0
    use_speaker_boost: bool = True
    max_chunk_chars: int = 2500  # ElevenLabs character limit per request
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 2.0


class ElevenLabsTTSPipeline:
    """
    Pipeline for ElevenLabs TTS API integration with advanced features.
    """

    def __init__(self, config: Optional[ElevenLabsConfig] = None, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize ElevenLabs TTS pipeline.

        Args:
            config: ElevenLabs configuration object
            progress_tracker: Optional progress tracking system

        Raises:
            RuntimeError: If API key is not available or client cannot be initialized
        """
        self.progress_tracker = progress_tracker
        self.client = None
        self.config = config or self._load_default_config()
        self.is_initialized = False

        # API usage tracking
        self.total_characters_processed = 0
        self.total_api_calls = 0
        self.session_start_time = time.time()

        logger.info("Initializing ElevenLabs TTS pipeline")
        self._initialize_client()

    def _load_default_config(self) -> ElevenLabsConfig:
        """Load default configuration with API key from secrets."""
        secrets = load_secrets()
        api_key = secrets.get("elevenlabs_api_key", os.getenv("ELEVENLABS_API_KEY", ""))

        if not api_key:
            raise RuntimeError(
                "ElevenLabs API key not found. Please add 'elevenlabs_api_key' to secrets.json "
                "or set ELEVENLABS_API_KEY environment variable."
            )

        return ElevenLabsConfig(api_key=api_key)

    def _initialize_client(self) -> None:
        """Initialize the ElevenLabs client."""
        try:
            self.client = ElevenLabs(api_key=self.config.api_key)

            # Test the connection by listing voices
            try:
                voices_response = self.client.voices.search()
                logger.info(f"Connected to ElevenLabs API. Available voices: {len(voices_response.voices)}")
                self.is_initialized = True
            except Exception as e:
                if "authentication" in str(e).lower():
                    raise RuntimeError("Invalid ElevenLabs API key")
                else:
                    raise RuntimeError(f"Failed to connect to ElevenLabs API: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs client: {e}")
            raise RuntimeError(f"Cannot initialize ElevenLabs TTS: {e}")

    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices from ElevenLabs."""
        if not self.is_initialized:
            return []

        try:
            voices_response = self.client.voices.search()
            voices = []
            for voice in voices_response.voices:
                voices.append({
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": getattr(voice, 'category', 'Unknown'),
                    "description": getattr(voice, 'description', '')
                })
            return voices
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for ElevenLabs TTS.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        max_chars = self.config.max_chunk_chars

        if len(text) <= max_chars:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Handle very long sentences - split by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 <= max_chars:
                            temp_chunk += " " + word if temp_chunk else word
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                # Truncate extremely long words
                                chunks.append(word[:max_chars])
                    if temp_chunk:
                        current_chunk = temp_chunk

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def process_chunk(self, text: str, output_path: str, chunk_id: str = "") -> ElevenLabsTTSResult:
        """
        Process a single text chunk through ElevenLabs TTS.

        Args:
            text: Text to convert to speech
            output_path: Path for output audio file
            chunk_id: Optional identifier for this chunk

        Returns:
            ElevenLabsTTSResult with processing information
        """
        if not self.is_initialized:
            return ElevenLabsTTSResult(
                success=False,
                error_message="ElevenLabs client not initialized"
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
            with PerformanceLogger(f"ElevenLabs TTS chunk processing: {chunk_id}"):
                # Preprocess text
                processed_text = self._preprocess_text(text)

                if not processed_text.strip():
                    logger.warning(f"Empty text after preprocessing: {chunk_id}")
                    return ElevenLabsTTSResult(
                        success=False,
                        error_message="Empty text after preprocessing"
                    )

                # Create voice settings
                voice_settings = VoiceSettings(
                    stability=self.config.stability,
                    similarity_boost=self.config.similarity_boost,
                    style=self.config.style,
                    use_speaker_boost=self.config.use_speaker_boost
                )

                # Generate audio with retry logic
                audio_data = self._generate_audio_with_retry(
                    processed_text, voice_settings
                )

                # Save audio file
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                self._save_audio(audio_data, output_path)

                # Calculate duration (estimate based on average speaking rate)
                # ElevenLabs doesn't provide duration info, so we estimate
                estimated_duration = self._estimate_audio_duration(processed_text)

                processing_time = time.time() - start_time

                # Update tracking
                self.total_characters_processed += len(processed_text)
                self.total_api_calls += 1

                logger.debug(
                    f"ElevenLabs TTS chunk completed: {chunk_id} "
                    f"({estimated_duration:.2f}s estimated, {processing_time:.2f}s processing)"
                )

                # Emit completion event
                if self.progress_tracker:
                    self.progress_tracker.emit_event(create_complete_event(
                        PipelineType.TTS,
                        current_item=chunk_id or "Unknown chunk",
                        duration=estimated_duration,
                        processing_time=processing_time,
                        file_size=output_path.stat().st_size if output_path.exists() else 0
                    ))

                return ElevenLabsTTSResult(
                    success=True,
                    audio_path=str(output_path),
                    duration=estimated_duration,
                    text_processed=processed_text,
                    processing_time=processing_time,
                    characters_processed=len(processed_text),
                    api_calls_made=1
                )

        except Exception as e:
            error_msg = f"ElevenLabs TTS processing failed for chunk {chunk_id}: {e}"
            logger.error(error_msg)

            # Emit error event
            if self.progress_tracker:
                self.progress_tracker.emit_event(create_error_event(
                    PipelineType.TTS,
                    error_message=error_msg,
                    current_item=chunk_id or "Unknown chunk"
                ))

            return ElevenLabsTTSResult(
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

    def _generate_audio_with_retry(self, text: str, voice_settings: VoiceSettings) -> bytes:
        """Generate audio with retry logic and rate limit handling."""
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                audio = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=self.config.voice_id,
                    model_id=self.config.model_id,
                    voice_settings=voice_settings,
                    output_format=self.config.output_format
                )
                return audio

            except Exception as e:
                last_exception = e
                error_str = str(e).lower()

                if "rate limit" in error_str or "too many requests" in error_str:
                    wait_time = self.config.rate_limit_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue

                elif "authentication" in error_str or "unauthorized" in error_str:
                    logger.error("Authentication failed - check API key")
                    raise

                elif "quota" in error_str or "insufficient" in error_str:
                    logger.error("API quota exceeded")
                    raise

                elif "invalid voice" in error_str:
                    logger.error(f"Invalid voice ID: {self.config.voice_id}")
                    raise

                else:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    time.sleep(self.config.retry_delay * (attempt + 1))

        raise last_exception

    def _save_audio(self, audio_data: bytes, output_path: Path) -> None:
        """Save audio data to file."""
        with open(output_path, 'wb') as f:
            f.write(audio_data)

    def _estimate_audio_duration(self, text: str) -> float:
        """Estimate audio duration based on text length."""
        # Average speaking rate is about 150-160 words per minute
        words = len(text.split())
        estimated_duration = (words / 150) * 60  # seconds
        return max(estimated_duration, 0.5)  # Minimum 0.5 seconds

    def batch_process(
        self,
        text_chunks: List[Dict[str, str]],
        output_dir: Path,
        parallel: bool = False  # ElevenLabs rate limits make parallel risky
    ) -> List[ElevenLabsTTSResult]:
        """
        Process multiple text chunks with progress tracking.

        Args:
            text_chunks: List of dictionaries with 'text' and 'id' keys
            output_dir: Output directory for audio files
            parallel: Whether to use parallel processing (not recommended for ElevenLabs)

        Returns:
            List of ElevenLabsTTSResult objects
        """
        if not self.is_initialized:
            logger.error("ElevenLabs client not initialized")
            return []

        logger.info(f"Starting batch ElevenLabs TTS processing: {len(text_chunks)} chunks")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Emit start event for batch processing
        if self.progress_tracker:
            self.progress_tracker.emit_event(create_start_event(
                PipelineType.TTS,
                total_items=len(text_chunks),
                current_item=f"Batch processing {len(text_chunks)} chunks"
            ))

        results = []
        progress = ProgressLogger("ElevenLabs TTS processing", len(text_chunks))

        # Sequential processing is recommended for ElevenLabs due to rate limits
        for i, chunk in enumerate(text_chunks):
            chunk_id = chunk.get('id', f"chunk_{i}")
            output_path = output_dir / f"{chunk_id}.mp3"  # ElevenLabs typically outputs MP3

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

            # Small delay between requests to respect rate limits
            if i < len(text_chunks) - 1:  # Don't delay after last chunk
                time.sleep(0.5)

        progress.finish()

        # Log summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        logger.info(
            f"Batch ElevenLabs TTS processing completed: "
            f"{len(successful)} successful, {len(failed)} failed. "
            f"Total characters: {sum(r.characters_processed for r in successful)}, "
            f"Total API calls: {sum(r.api_calls_made for r in successful)}"
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
            logger.info(f"Merging {len(audio_files)} ElevenLabs audio files to {output_path}")

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

            # Export as MP3 with good quality
            combined.export(str(output_path), format="mp3", bitrate="192k")

            duration_minutes = len(combined) / 1000 / 60
            logger.info(f"ElevenLabs audio merge completed: {duration_minutes:.1f} minutes")

            return True

        except Exception as e:
            logger.error(f"Failed to merge ElevenLabs audio files: {e}")
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
        logger.info(f"Processing {len(chapters)} chapters with ElevenLabs TTS")

        # Prepare text chunks from chapters, splitting long chapters if needed
        text_chunks = []
        for i, chapter in enumerate(chapters):
            chapter_num = chapter.get('chapter_num', i + 1)
            chapter_title = chapter.get('title', f'Chapter {chapter_num}')
            chapter_content = chapter['content']

            # Clean title for filename
            clean_title = "".join(c for c in chapter_title if c.isalnum() or c in ' -_')
            clean_title = clean_title.replace(' ', '_')[:20]

            # Split long chapters into smaller chunks
            content_chunks = self.chunk_text(chapter_content)

            for j, chunk in enumerate(content_chunks):
                if len(content_chunks) > 1:
                    chunk_id = f"chapter_{chapter_num:03d}_{clean_title}_part_{j+1:02d}"
                else:
                    chunk_id = f"chapter_{chapter_num:03d}_{clean_title}"

                text_chunks.append({
                    'id': chunk_id,
                    'text': chunk,
                    'title': chapter_title,
                    'chapter_num': chapter_num,
                    'part': j + 1 if len(content_chunks) > 1 else 1,
                    'total_parts': len(content_chunks)
                })

        # Process all chunks
        chapter_dir = output_dir / "chapters"
        results = self.batch_process(text_chunks, chapter_dir, parallel=False)

        # Collect successful audio files
        successful_results = [r for r in results if r.success]
        audio_files = [r.audio_path for r in successful_results]

        # Calculate statistics
        total_chars = sum(r.characters_processed for r in successful_results)
        total_api_calls = sum(r.api_calls_made for r in successful_results)
        total_duration = sum(r.duration for r in successful_results)

        processing_summary = {
            'total_chapters': len(chapters),
            'total_chunks': len(text_chunks),
            'successful_chunks': len(successful_results),
            'failed_chunks': len(results) - len(successful_results),
            'total_audio_duration': total_duration,
            'total_characters_processed': total_chars,
            'total_api_calls': total_api_calls,
            'chapter_files': audio_files,
            'merged_file': None
        }

        # Merge into final audiobook if requested and we have audio files
        if merge_final and audio_files:
            merged_file = output_dir / "audiobook_elevenlabs.mp3"
            if self.merge_audio_files(audio_files, str(merged_file)):
                processing_summary['merged_file'] = str(merged_file)
                logger.info(f"Final ElevenLabs audiobook created: {merged_file}")
            else:
                logger.error("Failed to create merged ElevenLabs audiobook")

        # Log session statistics
        session_duration = time.time() - self.session_start_time
        logger.info(
            f"ElevenLabs TTS session completed: "
            f"{total_chars} characters, {total_api_calls} API calls, "
            f"{session_duration:.1f}s session time"
        )

        return processing_summary

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for optimal ElevenLabs TTS synthesis.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text optimized for ElevenLabs TTS
        """
        processed = text

        # Handle pause markers (ElevenLabs supports SSML)
        processed = re.sub(r'\[PAUSE: ([\d.]+)\]', r'<break time="\1s"/>', processed)

        # Handle emphasis markers
        processed = re.sub(r'\[EMPHASIS_STRONG: ([^\]]+)\]', r'<emphasis level="strong">\1</emphasis>', processed)
        processed = re.sub(r'\[EMPHASIS_MILD: ([^\]]+)\]', r'<emphasis level="moderate">\1</emphasis>', processed)

        # Handle dialogue markers
        processed = re.sub(r'\[DIALOGUE_START\]', '', processed)
        processed = re.sub(r'\[DIALOGUE_END\]', '', processed)

        # Handle chapter markers
        processed = re.sub(r'\[CHAPTER_START: ([^\]]+)\]', r'Chapter: \1. ', processed)

        # Handle image descriptions
        processed = re.sub(r'\[IMAGE: ([^\]]+)\]', r'Image description: \1. ', processed)

        # Clean up extra whitespace
        processed = re.sub(r'\s+', ' ', processed).strip()

        return processed

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics for this session."""
        session_duration = time.time() - self.session_start_time

        return {
            "session_duration_seconds": session_duration,
            "total_characters_processed": self.total_characters_processed,
            "total_api_calls": self.total_api_calls,
            "average_chars_per_call": (
                self.total_characters_processed / self.total_api_calls
                if self.total_api_calls > 0 else 0
            ),
            "processing_rate_chars_per_second": (
                self.total_characters_processed / session_duration
                if session_duration > 0 else 0
            )
        }


def create_elevenlabs_tts_pipeline(
    config: Optional[ElevenLabsConfig] = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> ElevenLabsTTSPipeline:
    """
    Factory function to create ElevenLabs TTS pipeline.

    Args:
        config: ElevenLabs configuration
        progress_tracker: Optional progress tracking system

    Returns:
        Initialized ElevenLabs TTS pipeline
    """
    return ElevenLabsTTSPipeline(config, progress_tracker)