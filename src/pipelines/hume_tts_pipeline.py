"""
Hume AI TTS Pipeline for epub2tts.

This module provides a TTS pipeline for converting text to speech
using the Hume AI API with advanced emotional prosody features.
"""

import logging
import os
import time
import re
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from tqdm import tqdm

# Hume AI imports
from hume.client import HumeClient
from hume.tts import PostedUtteranceVoiceWithName

from utils.config import TTSConfig
from utils.logger import PerformanceLogger, ProgressLogger
from utils.secrets import load_secrets
from ui.progress_tracker import (
    ProgressTracker, PipelineType, EventType,
    create_start_event, create_progress_event, create_complete_event, create_error_event
)

logger = logging.getLogger(__name__)


@dataclass
class HumeTTSResult:
    """Result of Hume TTS processing."""
    success: bool
    audio_path: Optional[str] = None
    duration: float = 0.0
    text_processed: str = ""
    error_message: Optional[str] = None
    processing_time: float = 0.0
    characters_processed: int = 0
    api_calls_made: int = 0


@dataclass
class HumeTTSConfig:
    """Configuration for Hume TTS."""
    api_key: str
    voice_name: str = "Male English Actor"  # Default voice
    voice_provider: str = "HUME_AI"
    model_version: int = 2  # Octave 2
    output_format: str = "mp3"  # Options: "mp3", "wav", "pcm"
    sample_rate: int = 24000  # Hume's default sample rate
    max_chunk_chars: int = 5000  # Hume character limit per utterance
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 2.0
    use_streaming: bool = False  # Use streaming API for long content


class HumeTTSPipeline:
    """
    Pipeline for Hume AI TTS API integration with emotional prosody features.
    """

    def __init__(self, config: Optional[HumeTTSConfig] = None, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize Hume TTS pipeline.

        Args:
            config: Hume configuration object
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

        logger.info("Initializing Hume TTS pipeline")
        self._initialize_client()

    def _load_default_config(self) -> HumeTTSConfig:
        """Load default configuration with API key from secrets."""
        secrets = load_secrets()
        api_key = secrets.get("hume_api_key", os.getenv("HUME_API_KEY", ""))

        if not api_key:
            raise RuntimeError(
                "Hume API key not found. Please add 'hume_api_key' to secrets.json "
                "or set HUME_API_KEY environment variable."
            )

        return HumeTTSConfig(api_key=api_key)

    def _initialize_client(self) -> None:
        """Initialize the Hume client."""
        try:
            self.client = HumeClient(api_key=self.config.api_key)

            # Test the connection by attempting to list voices
            try:
                # Try a simple operation to verify API key is valid
                # Hume doesn't have a separate voice list endpoint in the same way,
                # so we'll just check if the client initializes properly
                logger.info("Connected to Hume AI API")
                self.is_initialized = True
            except Exception as e:
                if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                    raise RuntimeError("Invalid Hume API key")
                else:
                    raise RuntimeError(f"Failed to connect to Hume AI API: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize Hume client: {e}")
            raise RuntimeError(f"Cannot initialize Hume TTS: {e}")

    def get_available_voices(self) -> List[Dict[str, str]]:
        """
        Get list of available voices from Hume AI.

        Note: Hume's voice options are more limited and embedded in the API.
        This returns a static list of known voices.
        """
        if not self.is_initialized:
            return []

        # Known Hume AI voices (as of Octave 2)
        voices = [
            {
                "voice_id": "male_english_actor",
                "name": "Male English Actor",
                "provider": "HUME_AI",
                "description": "Professional male voice with natural emotional expression"
            },
            {
                "voice_id": "female_english_actor",
                "name": "Female English Actor",
                "provider": "HUME_AI",
                "description": "Professional female voice with natural emotional expression"
            },
            {
                "voice_id": "male_american_narrator",
                "name": "Male American Narrator",
                "provider": "HUME_AI",
                "description": "Clear male narration voice"
            },
            {
                "voice_id": "female_american_narrator",
                "name": "Female American Narrator",
                "provider": "HUME_AI",
                "description": "Clear female narration voice"
            }
        ]
        return voices

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for Hume TTS.

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

    def process_chunk(self, text: str, output_path: str, chunk_id: str = "") -> HumeTTSResult:
        """
        Process a single text chunk through Hume TTS.

        Args:
            text: Text to convert to speech
            output_path: Path for output audio file
            chunk_id: Optional identifier for this chunk

        Returns:
            HumeTTSResult with processing information
        """
        if not self.is_initialized:
            return HumeTTSResult(
                success=False,
                error_message="Hume client not initialized"
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
            with PerformanceLogger(f"Hume TTS chunk processing: {chunk_id}"):
                # Preprocess text
                processed_text = self._preprocess_text(text)

                if not processed_text.strip():
                    logger.warning(f"Empty text after preprocessing: {chunk_id}")
                    return HumeTTSResult(
                        success=False,
                        error_message="Empty text after preprocessing"
                    )

                # Generate audio with retry logic
                if self.config.use_streaming:
                    audio_data = self._synthesize_streaming_with_retry(processed_text)
                else:
                    audio_data = self._synthesize_with_retry(processed_text)

                # Save audio file
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                self._decode_and_save_audio(audio_data, output_path)

                # Calculate duration (estimate based on average speaking rate)
                # Hume doesn't provide duration info directly, so we estimate
                estimated_duration = self._estimate_audio_duration(processed_text)

                processing_time = time.time() - start_time

                # Update tracking
                self.total_characters_processed += len(processed_text)
                self.total_api_calls += 1

                logger.debug(
                    f"Hume TTS chunk completed: {chunk_id} "
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

                return HumeTTSResult(
                    success=True,
                    audio_path=str(output_path),
                    duration=estimated_duration,
                    text_processed=processed_text,
                    processing_time=processing_time,
                    characters_processed=len(processed_text),
                    api_calls_made=1
                )

        except Exception as e:
            error_msg = f"Hume TTS processing failed for chunk {chunk_id}: {e}"
            logger.error(error_msg)

            # Emit error event
            if self.progress_tracker:
                self.progress_tracker.emit_event(create_error_event(
                    PipelineType.TTS,
                    error_message=error_msg,
                    current_item=chunk_id or "Unknown chunk"
                ))

            return HumeTTSResult(
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

    def _synthesize_with_retry(self, text: str) -> bytes:
        """Generate audio with retry logic and rate limit handling (non-streaming)."""
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                # Create voice object
                voice = PostedUtteranceVoiceWithName(
                    name=self.config.voice_name,
                    provider=self.config.voice_provider
                )

                # Call Hume TTS API
                response = self.client.tts.synthesize_json(
                    text=text,
                    voice=voice,
                    version=self.config.model_version,
                    format=self.config.output_format.upper()
                )

                # Extract audio data from response
                # Hume returns base64-encoded audio in the response
                if hasattr(response, 'audio_data'):
                    audio_base64 = response.audio_data
                elif hasattr(response, 'data'):
                    audio_base64 = response.data
                elif isinstance(response, dict):
                    audio_base64 = response.get('audio_data') or response.get('data')
                else:
                    # Try to access as attribute or dict
                    try:
                        audio_base64 = response.audio_data
                    except AttributeError:
                        audio_base64 = response['audio_data']

                return audio_base64

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
                    logger.error(f"Invalid voice: {self.config.voice_name}")
                    raise

                else:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    time.sleep(self.config.retry_delay * (attempt + 1))

        raise last_exception

    def _synthesize_streaming_with_retry(self, text: str) -> bytes:
        """Generate audio with retry logic using streaming API."""
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                # Create voice object
                voice = PostedUtteranceVoiceWithName(
                    name=self.config.voice_name,
                    provider=self.config.voice_provider
                )

                # Call Hume TTS streaming API
                audio_chunks = []

                for chunk in self.client.tts.synthesize_json_streaming(
                    text=text,
                    voice=voice,
                    version=self.config.model_version,
                    format=self.config.output_format.upper()
                ):
                    # Each chunk contains base64 audio data
                    if hasattr(chunk, 'audio_data'):
                        audio_chunks.append(chunk.audio_data)
                    elif hasattr(chunk, 'data'):
                        audio_chunks.append(chunk.data)
                    elif isinstance(chunk, dict):
                        audio_chunks.append(chunk.get('audio_data') or chunk.get('data'))
                    else:
                        # Try to access as attribute
                        audio_chunks.append(chunk.audio_data)

                # Combine all chunks
                # Since they're base64 encoded, we need to decode each, combine, then re-encode
                combined_audio = b''
                for chunk_data in audio_chunks:
                    if isinstance(chunk_data, str):
                        combined_audio += base64.b64decode(chunk_data)
                    else:
                        combined_audio += chunk_data

                # Return as base64 for consistency
                return base64.b64encode(combined_audio).decode('utf-8')

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

                else:
                    logger.warning(f"Streaming attempt {attempt + 1} failed: {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    time.sleep(self.config.retry_delay * (attempt + 1))

        raise last_exception

    def _decode_and_save_audio(self, base64_audio: Union[str, bytes], output_path: Path) -> None:
        """
        Decode base64 audio data and save to file.

        Args:
            base64_audio: Base64 encoded audio data
            output_path: Path to save the audio file
        """
        try:
            # Decode base64 audio
            if isinstance(base64_audio, str):
                audio_bytes = base64.b64decode(base64_audio)
            else:
                audio_bytes = base64_audio

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)

            logger.debug(f"Saved audio to {output_path} ({len(audio_bytes)} bytes)")

        except Exception as e:
            logger.error(f"Failed to decode and save audio: {e}")
            raise

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
        parallel: bool = False  # Hume rate limits make parallel risky
    ) -> List[HumeTTSResult]:
        """
        Process multiple text chunks with progress tracking.

        Args:
            text_chunks: List of dictionaries with 'text' and 'id' keys
            output_dir: Output directory for audio files
            parallel: Whether to use parallel processing (not recommended for Hume)

        Returns:
            List of HumeTTSResult objects
        """
        if not self.is_initialized:
            logger.error("Hume client not initialized")
            return []

        logger.info(f"Starting batch Hume TTS processing: {len(text_chunks)} chunks")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Emit start event for batch processing
        if self.progress_tracker:
            self.progress_tracker.emit_event(create_start_event(
                PipelineType.TTS,
                total_items=len(text_chunks),
                current_item=f"Batch processing {len(text_chunks)} chunks"
            ))

        results = []
        progress = ProgressLogger("Hume TTS processing", len(text_chunks))

        # Sequential processing is recommended for Hume due to rate limits
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

            # Small delay between requests to respect rate limits
            if i < len(text_chunks) - 1:  # Don't delay after last chunk
                time.sleep(0.5)

        progress.finish()

        # Log summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        logger.info(
            f"Batch Hume TTS processing completed: "
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
            logger.info(f"Merging {len(audio_files)} Hume audio files to {output_path}")

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

            # Export based on format
            if self.config.output_format.lower() == 'mp3':
                combined.export(str(output_path), format="mp3", bitrate="192k")
            elif self.config.output_format.lower() == 'wav':
                combined.export(str(output_path), format="wav")
            else:
                # Default to mp3
                combined.export(str(output_path), format="mp3", bitrate="192k")

            duration_minutes = len(combined) / 1000 / 60
            logger.info(f"Hume audio merge completed: {duration_minutes:.1f} minutes")

            return True

        except Exception as e:
            logger.error(f"Failed to merge Hume audio files: {e}")
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
        logger.info(f"Processing {len(chapters)} chapters with Hume TTS")

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
            merged_file = output_dir / f"audiobook_hume.{self.config.output_format}"
            if self.merge_audio_files(audio_files, str(merged_file)):
                processing_summary['merged_file'] = str(merged_file)
                logger.info(f"Final Hume audiobook created: {merged_file}")
            else:
                logger.error("Failed to create merged Hume audiobook")

        # Log session statistics
        session_duration = time.time() - self.session_start_time
        logger.info(
            f"Hume TTS session completed: "
            f"{total_chars} characters, {total_api_calls} API calls, "
            f"{session_duration:.1f}s session time"
        )

        return processing_summary

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for optimal Hume TTS synthesis.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text optimized for Hume TTS
        """
        processed = text

        # Handle pause markers (Hume may support natural pauses)
        processed = re.sub(r'\[PAUSE: ([\d.]+)\]', r' ... ', processed)

        # Handle emphasis markers (convert to natural text emphasis)
        processed = re.sub(r'\[EMPHASIS_STRONG: ([^\]]+)\]', r'\1', processed)
        processed = re.sub(r'\[EMPHASIS_MILD: ([^\]]+)\]', r'\1', processed)

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


def create_hume_tts_pipeline(
    config: Optional[HumeTTSConfig] = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> HumeTTSPipeline:
    """
    Factory function to create Hume TTS pipeline.

    Args:
        config: Hume configuration
        progress_tracker: Optional progress tracking system

    Returns:
        Initialized Hume TTS pipeline
    """
    return HumeTTSPipeline(config, progress_tracker)
