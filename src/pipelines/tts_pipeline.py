"""
TTS Pipeline for Kokoro integration.

This module provides the TTS pipeline for converting text to speech
using the Kokoro TTS model with advanced features and optimizations.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import soundfile as sf
from pydub import AudioSegment
from tqdm import tqdm

from ..utils.config import TTSConfig
from ..utils.logger import PerformanceLogger, ProgressLogger

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

    def __init__(self, config: TTSConfig):
        """
        Initialize Kokoro TTS pipeline.

        Args:
            config: TTS configuration object

        Raises:
            RuntimeError: If Kokoro model cannot be loaded
        """
        self.config = config
        self.model = None
        self.voice_embeddings: Dict[str, Any] = {}
        self.is_initialized = False

        logger.info(f"Initializing Kokoro TTS pipeline with model: {config.model}")
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the Kokoro TTS model."""
        try:
            # Note: This is a placeholder for actual Kokoro model loading
            # In real implementation, this would load the actual Kokoro model
            logger.info(f"Loading Kokoro model from: {self.config.model_path}")

            # Simulate model loading
            if not Path(self.config.model_path).exists():
                logger.warning(f"Model path does not exist: {self.config.model_path}")
                logger.info("Using mock TTS for development/testing")
                self.model = MockKokoroModel(self.config)
            else:
                # Load actual Kokoro model here
                self.model = MockKokoroModel(self.config)  # Placeholder

            self.is_initialized = True
            logger.info("Kokoro TTS model initialized successfully")

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

        results = []
        progress = ProgressLogger("TTS processing", len(text_chunks))

        if parallel and len(text_chunks) > 1:
            # Parallel processing
            max_workers = min(4, len(text_chunks))  # Limit workers for memory
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
            chunk_id = f"chapter_{i+1:03d}_{chapter.get('title', 'untitled')}"
            # Clean chunk ID for filename
            chunk_id = "".join(c for c in chunk_id if c.isalnum() or c in '-_')

            text_chunks.append({
                'id': chunk_id,
                'text': chapter['content'],
                'title': chapter.get('title', f'Chapter {i+1}')
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

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text optimized for TTS
        """
        # Remove or replace TTS-unfriendly patterns
        processed = text

        # Handle pause markers
        import re
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


class MockKokoroModel:
    """Mock Kokoro model for development and testing."""

    def __init__(self, config: TTSConfig):
        """Initialize mock model."""
        self.config = config
        logger.info("Initialized mock Kokoro model for development")

    def synthesize(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> np.ndarray:
        """
        Generate mock audio data.

        Args:
            text: Text to synthesize
            voice: Voice to use
            speed: Speech speed
            pitch: Speech pitch

        Returns:
            Mock audio data as numpy array
        """
        # Generate simple sine wave as mock audio
        duration = len(text) * 0.05  # 50ms per character
        sample_rate = self.config.sample_rate

        # Adjust duration based on speed
        duration = duration / speed

        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # Generate a simple tone that varies based on text content
        frequency = 440 + (hash(text) % 200)  # Vary frequency based on text
        amplitude = 0.1  # Keep volume low

        audio_data = amplitude * np.sin(2 * np.pi * frequency * t * pitch)

        # Add some variation to make it less monotonic
        modulation = 0.1 * np.sin(2 * np.pi * 2 * t)
        audio_data = audio_data * (1 + modulation)

        return audio_data.astype(np.float32)

    def get_available_voices(self) -> List[str]:
        """Get list of available voices."""
        return ["default", "male", "female", "neutral"]


def create_tts_pipeline(config: TTSConfig) -> KokoroTTSPipeline:
    """
    Factory function to create TTS pipeline.

    Args:
        config: TTS configuration

    Returns:
        Initialized TTS pipeline
    """
    return KokoroTTSPipeline(config)