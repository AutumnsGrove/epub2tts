"""
ElevenLabs TTS Pipeline for epub2tts.

This module provides integration with ElevenLabs API for high-quality text-to-speech
synthesis as an alternative to the Kokoro TTS pipeline.
"""

import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Import ElevenLabs client
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

from utils.config import TTSConfig
from utils.secrets import get_elevenlabs_api_key
from utils.logger import PerformanceLogger, ProgressLogger
from ui.progress_tracker import (
    ProgressTracker, PipelineType, EventType,
    create_start_event, create_progress_event, create_complete_event, create_error_event
)

logger = logging.getLogger(__name__)


@dataclass
class ElevenLabsResult:
    """Result of ElevenLabs TTS processing."""
    success: bool
    audio_path: Optional[str] = None
    duration: float = 0.0
    characters_processed: int = 0
    text_processed: str = ""
    error_message: Optional[str] = None
    processing_time: float = 0.0
    voice_id: Optional[str] = None


class ElevenLabsTTSPipeline:
    """
    TTS pipeline using ElevenLabs API for high-quality speech synthesis.
    """

    def __init__(self, config: TTSConfig, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize ElevenLabs TTS pipeline.

        Args:
            config: TTS configuration object
            progress_tracker: Optional progress tracking system

        Raises:
            RuntimeError: If ElevenLabs API is not available or API key is missing
        """
        if not ELEVENLABS_AVAILABLE:
            raise RuntimeError("ElevenLabs library not available. Install with: pip install elevenlabs")

        self.config = config
        self.progress_tracker = progress_tracker
        self.client = None
        self.is_initialized = False

        # ElevenLabs specific settings
        self.voice_id = getattr(config, 'elevenlabs_voice_id', 'JBFqnCBsd6RMkjVDRZzb')  # George voice
        self.model_id = getattr(config, 'elevenlabs_model', 'eleven_multilingual_v2')
        self.stability = getattr(config, 'elevenlabs_stability', 0.75)
        self.similarity_boost = getattr(config, 'elevenlabs_similarity_boost', 0.75)
        self.style = getattr(config, 'elevenlabs_style', 0.0)
        self.max_chunk_chars = getattr(config, 'elevenlabs_max_chunk_chars', 2500)
        self.max_retries = 3
        self.retry_delay = 1.0  # Base delay for exponential backoff

        logger.info(f"Initializing ElevenLabs TTS pipeline with voice: {self.voice_id}")
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the ElevenLabs client."""
        try:
            api_key = get_elevenlabs_api_key()
            if not api_key:
                raise RuntimeError(
                    "ElevenLabs API key not found. Please add 'elevenlabs_api_key' to secrets.json "
                    "or set ELEVENLABS_API_KEY environment variable."
                )

            self.client = ElevenLabs(api_key=api_key)

            # Test the connection by getting voice info
            try:
                voice = self.client.voices.get(self.voice_id)
                logger.info(f"Connected to ElevenLabs API. Using voice: {voice.name}")
            except Exception as e:
                logger.warning(f"Could not verify voice {self.voice_id}: {e}")
                # Continue anyway - voice validation will happen during synthesis

            self.is_initialized = True
            logger.info("ElevenLabs TTS pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs client: {e}")
            raise RuntimeError(f"Cannot initialize ElevenLabs TTS: {e}")

    def process_chunk(self, text: str, output_path: str, chunk_id: str = "") -> ElevenLabsResult:
        """
        Process a single text chunk through ElevenLabs TTS.

        Args:
            text: Text to convert to speech
            output_path: Path for output audio file
            chunk_id: Optional identifier for this chunk

        Returns:
            ElevenLabsResult with processing information
        """
        if not self.is_initialized:
            return ElevenLabsResult(
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
                # Preprocess text for TTS
                processed_text = self._preprocess_text(text)

                if not processed_text.strip():
                    logger.warning(f"Empty text after preprocessing: {chunk_id}")
                    return ElevenLabsResult(
                        success=False,
                        error_message="Empty text after preprocessing"
                    )

                # Check if text needs chunking
                if len(processed_text) > self.max_chunk_chars:
                    logger.info(f"Text too long ({len(processed_text)} chars), chunking for {chunk_id}")
                    return self._process_long_text(processed_text, output_path, chunk_id)

                # Generate audio using ElevenLabs API
                audio_data = self._synthesize_with_retry(processed_text)

                # Save audio file
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # ElevenLabs returns audio data directly
                with open(output_path, 'wb') as f:
                    f.write(audio_data)

                # Calculate duration (approximate based on characters and speech rate)
                # Rough estimate: ~150 characters per minute for average speech
                estimated_duration = len(processed_text) / 150 * 60

                processing_time = time.time() - start_time

                logger.debug(
                    f"ElevenLabs TTS chunk completed: {chunk_id} "
                    f"({estimated_duration:.2f}s estimated audio, {processing_time:.2f}s processing)"
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

                return ElevenLabsResult(
                    success=True,
                    audio_path=str(output_path),
                    duration=estimated_duration,
                    characters_processed=len(processed_text),
                    text_processed=processed_text,
                    processing_time=processing_time,
                    voice_id=self.voice_id
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

            return ElevenLabsResult(
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

    def _synthesize_with_retry(self, text: str) -> bytes:
        """
        Synthesize text with retry logic for rate limiting and API errors.

        Args:
            text: Text to synthesize

        Returns:
            Audio data as bytes

        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Use ElevenLabs text_to_speech.convert method with voice settings
                audio_data = self.client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    text=text,
                    model_id=self.model_id,
                    voice_settings=VoiceSettings(
                        stability=self.stability,
                        similarity_boost=self.similarity_boost,
                        style=self.style,
                        use_speaker_boost=True
                    )
                )

                # Convert generator to bytes if needed
                if hasattr(audio_data, '__iter__') and not isinstance(audio_data, bytes):
                    audio_bytes = b''.join(audio_data)
                else:
                    audio_bytes = audio_data

                return audio_bytes

            except Exception as e:
                error_str = str(e).lower()

                # Handle rate limiting
                if "rate limit" in error_str or "429" in error_str:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, waiting {delay}s before retry {attempt + 1}")
                    time.sleep(delay)
                    continue

                # Handle quota exceeded
                elif "quota" in error_str or "insufficient credits" in error_str:
                    raise RuntimeError(f"ElevenLabs quota exceeded: {e}")

                # Handle authentication errors
                elif "unauthorized" in error_str or "invalid api key" in error_str:
                    raise RuntimeError(f"ElevenLabs authentication failed: {e}")

                # Handle invalid voice
                elif "voice" in error_str and "not found" in error_str:
                    raise RuntimeError(f"Invalid voice ID {self.voice_id}: {e}")

                # Other errors - retry with exponential backoff
                else:
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(f"ElevenLabs API error (attempt {attempt + 1}): {e}. Retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        raise

        raise RuntimeError(f"ElevenLabs synthesis failed after {self.max_retries + 1} attempts")

    def _process_long_text(self, text: str, output_path: str, chunk_id: str) -> ElevenLabsResult:
        """
        Process text that exceeds the character limit by splitting into chunks.

        Args:
            text: Long text to process
            output_path: Output path for final merged audio
            chunk_id: Chunk identifier

        Returns:
            ElevenLabsResult with merged audio
        """
        try:
            # Split text into smaller chunks
            chunks = self._split_text_for_api(text)
            logger.info(f"Split long text into {len(chunks)} chunks for {chunk_id}")

            audio_segments = []
            total_chars = 0
            start_time = time.time()

            # Process each chunk
            for i, chunk_text in enumerate(chunks):
                if not chunk_text.strip():
                    continue

                try:
                    audio_data = self._synthesize_with_retry(chunk_text)
                    audio_segments.append(audio_data)
                    total_chars += len(chunk_text)

                    # Add small delay between chunks to be respectful of API limits
                    time.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Failed to process chunk {i+1}/{len(chunks)} for {chunk_id}: {e}")
                    # Continue with remaining chunks
                    continue

            if not audio_segments:
                raise RuntimeError("No audio segments generated successfully")

            # Merge audio segments
            merged_audio = b''.join(audio_segments)

            # Save merged audio
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(merged_audio)

            # Calculate estimated duration
            estimated_duration = total_chars / 150 * 60  # ~150 chars per minute
            processing_time = time.time() - start_time

            logger.info(f"Successfully merged {len(audio_segments)} audio segments for {chunk_id}")

            return ElevenLabsResult(
                success=True,
                audio_path=str(output_path),
                duration=estimated_duration,
                characters_processed=total_chars,
                text_processed=text,
                processing_time=processing_time,
                voice_id=self.voice_id
            )

        except Exception as e:
            error_msg = f"Failed to process long text for {chunk_id}: {e}"
            logger.error(error_msg)
            return ElevenLabsResult(
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time if 'start_time' in locals() else 0
            )

    def _split_text_for_api(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for ElevenLabs API.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        chunks = []
        current_chunk = ""

        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            # If adding this sentence would exceed limit, start new chunk
            if len(current_chunk) + len(sentence) + 1 > self.max_chunk_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Sentence itself is too long, split by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > self.max_chunk_chars:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                # Word itself is too long, truncate it
                                chunks.append(word[:self.max_chunk_chars])
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

    def batch_process(
        self,
        text_chunks: List[Dict[str, str]],
        output_dir: Path,
        parallel: bool = False  # ElevenLabs API rate limits make parallel risky
    ) -> List[ElevenLabsResult]:
        """
        Process multiple text chunks.

        Args:
            text_chunks: List of dictionaries with 'text' and 'id' keys
            output_dir: Output directory for audio files
            parallel: Whether to use parallel processing (not recommended for ElevenLabs)

        Returns:
            List of ElevenLabsResult objects
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

        # For ElevenLabs, prefer sequential processing to respect rate limits
        for i, chunk in enumerate(text_chunks):
            chunk_id = chunk.get('id', f"chunk_{i}")
            output_path = output_dir / f"{chunk_id}.mp3"  # ElevenLabs outputs MP3

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

            # Add delay between chunks to respect rate limits
            if i < len(text_chunks) - 1:  # Don't delay after the last chunk
                time.sleep(1.0)

        progress.finish()

        # Log summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        total_chars = sum(r.characters_processed for r in successful)

        logger.info(
            f"Batch ElevenLabs TTS processing completed: "
            f"{len(successful)} successful, {len(failed)} failed, "
            f"{total_chars} characters processed"
        )

        return results

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
        logger.info(f"Processing {len(chapters)} chapters for ElevenLabs TTS")

        # Prepare text chunks from chapters
        text_chunks = []
        for i, chapter in enumerate(chapters):
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
        results = self.batch_process(text_chunks, chapter_dir, parallel=False)

        # Collect successful audio files
        successful_results = [r for r in results if r.success]
        audio_files = [r.audio_path for r in successful_results]
        total_chars = sum(r.characters_processed for r in successful_results)

        processing_summary = {
            'total_chapters': len(chapters),
            'successful_chapters': len(successful_results),
            'failed_chapters': len(results) - len(successful_results),
            'total_audio_duration': sum(r.duration for r in successful_results),
            'total_characters_processed': total_chars,
            'chapter_files': audio_files,
            'merged_file': None,
            'voice_id': self.voice_id,
            'model_id': self.model_id
        }

        # Merge into final audiobook if requested and we have audio files
        if merge_final and audio_files:
            try:
                from pydub import AudioSegment

                merged_file = output_dir / "audiobook.mp3"
                logger.info(f"Merging {len(audio_files)} audio files to {merged_file}")

                # Load first audio file
                combined = AudioSegment.from_mp3(audio_files[0])

                # Add remaining files
                for audio_file in audio_files[1:]:
                    if Path(audio_file).exists():
                        next_audio = AudioSegment.from_mp3(audio_file)
                        combined = combined + next_audio  # Simple concatenation

                # Export merged audio
                combined.export(str(merged_file), format="mp3", bitrate="192k")
                processing_summary['merged_file'] = str(merged_file)

                duration_minutes = len(combined) / 1000 / 60
                logger.info(f"ElevenLabs audiobook merge completed: {duration_minutes:.1f} minutes")

            except Exception as e:
                logger.error(f"Failed to merge ElevenLabs audio files: {e}")

        return processing_summary

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for optimal ElevenLabs TTS synthesis.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text optimized for ElevenLabs TTS
        """
        # Remove or replace TTS-unfriendly patterns
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

    def get_voice_info(self) -> Dict[str, Any]:
        """Get information about current voice and available voices."""
        if not self.is_initialized:
            return {"error": "ElevenLabs client not initialized"}

        try:
            # Get current voice info
            current_voice = self.client.voices.get(self.voice_id)

            # Get all available voices
            all_voices = self.client.voices.get_all()

            return {
                "current_voice": {
                    "voice_id": self.voice_id,
                    "name": current_voice.name,
                    "category": current_voice.category,
                    "description": getattr(current_voice, 'description', 'No description'),
                },
                "available_voices": [
                    {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "category": voice.category,
                        "preview_url": getattr(voice, 'preview_url', None)
                    }
                    for voice in all_voices.voices
                ],
                "current_settings": {
                    "model_id": self.model_id,
                    "stability": self.stability,
                    "similarity_boost": self.similarity_boost,
                    "style": self.style
                }
            }
        except Exception as e:
            logger.error(f"Failed to get voice info: {e}")
            return {"error": f"Failed to get voice info: {e}"}

    def get_available_voices(self) -> List[str]:
        """Get list of available voice IDs."""
        try:
            if not self.is_initialized:
                return []

            all_voices = self.client.voices.get_all()
            return [voice.voice_id for voice in all_voices.voices]
        except Exception as e:
            logger.error(f"Failed to get available voices: {e}")
            return []


def create_elevenlabs_tts_pipeline(config: TTSConfig, progress_tracker: Optional[ProgressTracker] = None) -> ElevenLabsTTSPipeline:
    """
    Factory function to create ElevenLabs TTS pipeline.

    Args:
        config: TTS configuration
        progress_tracker: Optional progress tracking system

    Returns:
        Initialized ElevenLabs TTS pipeline

    Raises:
        RuntimeError: If ElevenLabs is not available or API key is missing
    """
    return ElevenLabsTTSPipeline(config, progress_tracker)