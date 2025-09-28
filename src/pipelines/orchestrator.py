"""
Pipeline orchestrator for epub2tts.

This module coordinates the execution of all processing pipelines:
text extraction, cleaning, TTS generation, and image description.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import time
import json
import concurrent.futures
import threading

from core.epub_processor import EPUBProcessor, ProcessingResult
from core.text_cleaner import Chapter
from pipelines.tts_pipeline import KokoroTTSPipeline, TTSResult, create_tts_pipeline
from pipelines.image_pipeline import ImageDescriptionPipeline, ImageDescription, create_image_pipeline
from utils.config import Config
from utils.logger import PerformanceLogger, LoggerMixin
from ui.progress_tracker import ProgressTracker
from ui import TerminalUIManager, UIConfig, create_ui_manager

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Combined result from all pipeline stages."""
    epub_processing: ProcessingResult
    tts_results: Optional[Dict[str, Any]] = None
    image_descriptions: List[ImageDescription] = None
    total_processing_time: float = 0.0
    pipeline_stages: Dict[str, float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'epub_processing': self.epub_processing.to_dict(),
            'tts_results': self.tts_results,
            'image_descriptions': [asdict(desc) for desc in (self.image_descriptions or [])],
            'total_processing_time': self.total_processing_time,
            'pipeline_stages': self.pipeline_stages or {}
        }
        return result


class PipelineOrchestrator(LoggerMixin):
    """
    Orchestrates the complete epub2tts processing pipeline.
    """

    def __init__(self, config: Config, progress_tracker: Optional[ProgressTracker] = None, ui_manager: Optional[TerminalUIManager] = None):
        """
        Initialize pipeline orchestrator.

        Args:
            config: Application configuration
            progress_tracker: Optional progress tracking system
            ui_manager: Optional terminal UI manager for user interface
        """
        self.config = config
        self.progress_tracker = progress_tracker
        self.ui_manager = ui_manager
        self.epub_processor = EPUBProcessor(config)

        # Initialize pipelines based on configuration
        self.tts_pipeline: Optional[KokoroTTSPipeline] = None
        self.image_pipeline: Optional[ImageDescriptionPipeline] = None

        if config.tts.model:
            try:
                self.tts_pipeline = create_tts_pipeline(config.tts, progress_tracker)
                self.logger.info("TTS pipeline initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize TTS pipeline: {e}")

        if config.image_description.enabled:
            try:
                self.image_pipeline = create_image_pipeline(config.image_description, progress_tracker)
                self.logger.info("Image description pipeline initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize image pipeline: {e}")

    def process_epub_complete(
        self,
        epub_path: Path,
        output_dir: Path,
        enable_tts: bool = False,
        enable_images: bool = True
    ) -> PipelineResult:
        """
        Process EPUB through complete pipeline.

        Args:
            epub_path: Path to EPUB file
            output_dir: Output directory
            enable_tts: Whether to generate TTS audio
            enable_images: Whether to process images

        Returns:
            PipelineResult with all processing results
        """
        start_time = time.time()
        stage_times = {}

        self.logger.info(f"Starting complete pipeline processing: {epub_path}")

        try:
            # Stage 1: EPUB Processing (text extraction and cleaning)
            stage_start = time.time()
            with PerformanceLogger("EPUB text processing"):
                epub_result = self.epub_processor.process_epub(epub_path, output_dir)

            if not epub_result.success:
                self.logger.error(f"EPUB processing failed: {epub_result.error_message}")
                return PipelineResult(
                    epub_processing=epub_result,
                    total_processing_time=time.time() - start_time,
                    pipeline_stages={'epub_processing': time.time() - stage_start}
                )

            stage_times['epub_processing'] = time.time() - stage_start
            self.logger.info(f"EPUB processing completed: {len(epub_result.chapters)} chapters")

            # Stage 2 & 3: Parallel Image Processing and TTS Generation
            image_descriptions = []
            tts_results = None

            # Prepare parallel tasks
            futures = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Start image processing if enabled
                if enable_images and self.image_pipeline and epub_result.image_info:
                    self.logger.info("🖼️  Starting image processing in parallel...")
                    futures['images'] = executor.submit(
                        self._process_images_parallel,
                        epub_result.image_info
                    )

                # Start TTS generation if enabled
                if enable_tts and self.tts_pipeline:
                    self.logger.info("🔊 Starting TTS generation in parallel...")
                    futures['tts'] = executor.submit(
                        self._generate_tts_audio_parallel,
                        epub_result.chapters,
                        output_dir
                    )

                # Wait for both tasks to complete and collect results
                if 'images' in futures:
                    try:
                        image_result = futures['images'].result()
                        if image_result['success']:
                            image_descriptions = image_result['descriptions']
                            self.logger.info(f"✅ Image processing completed: {len(image_descriptions)} descriptions")
                        stage_times['image_processing'] = image_result['processing_time']
                    except Exception as e:
                        self.logger.error(f"Image processing failed: {e}")
                        stage_times['image_processing'] = 0

                if 'tts' in futures:
                    try:
                        tts_result = futures['tts'].result()
                        if tts_result['success']:
                            tts_results = tts_result['results']
                            self.logger.info("✅ TTS generation completed")
                        stage_times['tts_generation'] = tts_result['processing_time']
                    except Exception as e:
                        self.logger.error(f"TTS generation failed: {e}")
                        stage_times['tts_generation'] = 0

            # Integrate image descriptions into text if available
            if image_descriptions:
                self.logger.info("🔗 Integrating image descriptions into text...")
                epub_result = self._integrate_image_descriptions(
                    epub_result,
                    image_descriptions
                )

            # Stage 4: Final output and metadata
            stage_start = time.time()
            self._generate_final_outputs(
                epub_result,
                image_descriptions,
                tts_results,
                output_dir
            )
            stage_times['final_output'] = time.time() - stage_start

            total_time = time.time() - start_time

            result = PipelineResult(
                epub_processing=epub_result,
                tts_results=tts_results,
                image_descriptions=image_descriptions,
                total_processing_time=total_time,
                pipeline_stages=stage_times
            )

            self.logger.info(
                f"Complete pipeline finished successfully in {total_time:.2f}s"
            )

            return result

        except Exception as e:
            error_msg = f"Pipeline processing failed: {e}"
            self.logger.error(error_msg, exc_info=True)

            # Return partial result with error
            return PipelineResult(
                epub_processing=ProcessingResult(
                    success=False,
                    text_content="",
                    chapters=[],
                    metadata={},
                    image_info=[],
                    cleaning_stats=None,
                    error_message=error_msg
                ),
                total_processing_time=time.time() - start_time,
                pipeline_stages=stage_times
            )

    def _integrate_image_descriptions(
        self,
        epub_result: ProcessingResult,
        image_descriptions: List[ImageDescription]
    ) -> ProcessingResult:
        """
        Integrate image descriptions into the text content.

        Args:
            epub_result: Original EPUB processing result
            image_descriptions: List of image descriptions

        Returns:
            Updated ProcessingResult with integrated descriptions
        """
        self.logger.debug("Integrating image descriptions into text")

        # Create mapping of image paths to descriptions
        desc_map = {
            Path(desc.image_path).name: desc.description
            for desc in image_descriptions
            if desc.confidence > 0.5  # Only use high-confidence descriptions
        }

        # Update text content
        updated_text = epub_result.text_content
        for image_name, description in desc_map.items():
            # Replace image placeholders with descriptions
            placeholder_patterns = [
                f"[IMAGE: Image of {image_name}]",
                f"[IMAGE: {image_name}]",
                f"![{image_name}]",
                f"![Image of {image_name}]"
            ]

            for pattern in placeholder_patterns:
                if pattern in updated_text:
                    replacement = f"[IMAGE DESCRIPTION: {description}]"
                    updated_text = updated_text.replace(pattern, replacement)

        # Update chapters with integrated descriptions
        updated_chapters = []
        for chapter in epub_result.chapters:
            updated_content = chapter.content
            for image_name, description in desc_map.items():
                placeholder_patterns = [
                    f"[IMAGE: Image of {image_name}]",
                    f"[IMAGE: {image_name}]"
                ]

                for pattern in placeholder_patterns:
                    if pattern in updated_content:
                        replacement = f"[IMAGE DESCRIPTION: {description}]"
                        updated_content = updated_content.replace(pattern, replacement)

            # Create updated chapter
            updated_chapter = Chapter(
                chapter_num=chapter.chapter_num,
                title=chapter.title,
                content=updated_content,
                word_count=len(updated_content.split()),
                estimated_duration=len(updated_content.split()) / 200.0,
                confidence=chapter.confidence
            )
            updated_chapters.append(updated_chapter)

        # Create updated result
        updated_result = ProcessingResult(
            success=epub_result.success,
            text_content=updated_text,
            chapters=updated_chapters,
            metadata=epub_result.metadata,
            image_info=epub_result.image_info,
            cleaning_stats=epub_result.cleaning_stats,
            error_message=epub_result.error_message,
            processing_time=epub_result.processing_time
        )

        self.logger.info(f"Integrated {len(desc_map)} image descriptions into text")
        return updated_result

    def _process_images_parallel(self, image_info_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process images in parallel - wrapper for use with ThreadPoolExecutor.

        Args:
            image_info_list: List of image information dictionaries

        Returns:
            Dictionary with success status, descriptions, and processing time
        """
        start_time = time.time()

        try:
            # Ensure images have been copied to permanent location
            # Wait a moment for any file operations to complete
            time.sleep(0.1)

            # Validate that image files exist before processing
            valid_image_info = []
            for image_info in image_info_list:
                image_path = image_info.get('file_path', '')
                if image_path and Path(image_path).exists():
                    valid_image_info.append(image_info)
                    self.logger.debug(f"Validated image path: {image_path}")
                else:
                    self.logger.warning(f"Image file not found: {image_path}")

            if not valid_image_info:
                self.logger.warning("No valid image files found for processing")
                return {
                    'success': False,
                    'descriptions': [],
                    'processing_time': time.time() - start_time
                }

            # Process images
            with PerformanceLogger("Image description generation"):
                image_result = self.image_pipeline.batch_process_images(
                    valid_image_info,
                    parallel=True
                )

                if image_result.success:
                    return {
                        'success': True,
                        'descriptions': image_result.descriptions,
                        'processing_time': time.time() - start_time
                    }
                else:
                    return {
                        'success': False,
                        'descriptions': [],
                        'processing_time': time.time() - start_time
                    }

        except Exception as e:
            self.logger.error(f"Image processing error: {e}", exc_info=True)
            return {
                'success': False,
                'descriptions': [],
                'processing_time': time.time() - start_time
            }

    def _generate_tts_audio_parallel(
        self,
        chapters: List[Chapter],
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Generate TTS audio in parallel - wrapper for use with ThreadPoolExecutor.

        Args:
            chapters: List of chapters to process
            output_dir: Output directory for audio files

        Returns:
            Dictionary with success status, results, and processing time
        """
        start_time = time.time()

        try:
            with PerformanceLogger("TTS audio generation"):
                tts_results = self._generate_tts_audio(chapters, output_dir)

                return {
                    'success': tts_results is not None,
                    'results': tts_results,
                    'processing_time': time.time() - start_time
                }

        except Exception as e:
            self.logger.error(f"TTS generation error: {e}", exc_info=True)
            return {
                'success': False,
                'results': None,
                'processing_time': time.time() - start_time
            }

    def _generate_tts_audio(
        self,
        chapters: List[Chapter],
        output_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Generate TTS audio for chapters.

        Args:
            chapters: List of chapters to process
            output_dir: Output directory for audio files

        Returns:
            TTS processing results or None if failed
        """
        if not self.tts_pipeline:
            self.logger.warning("TTS pipeline not available")
            return None

        try:
            # Prepare chapters for TTS
            chapter_dicts = []
            for chapter in chapters:
                chapter_dicts.append({
                    'title': chapter.title,
                    'content': chapter.content,
                    'chapter_num': chapter.chapter_num
                })

            # Process through TTS pipeline
            tts_results = self.tts_pipeline.process_chapters(
                chapter_dicts,
                output_dir / "audio",
                merge_final=True
            )

            self.logger.info(
                f"TTS generation completed: "
                f"{tts_results['successful_chapters']}/{tts_results['total_chapters']} chapters"
            )

            return tts_results

        except Exception as e:
            self.logger.error(f"TTS generation failed: {e}")
            return None

    def _generate_final_outputs(
        self,
        epub_result: ProcessingResult,
        image_descriptions: List[ImageDescription],
        tts_results: Optional[Dict[str, Any]],
        output_dir: Path
    ) -> None:
        """
        Generate final output files and metadata.

        Args:
            epub_result: EPUB processing result
            image_descriptions: Image descriptions
            tts_results: TTS processing results
            output_dir: Output directory
        """
        self.logger.debug("Generating final outputs")

        # Create comprehensive metadata
        metadata = {
            'book_metadata': epub_result.metadata,
            'processing_stats': {
                'total_chapters': len(epub_result.chapters),
                'total_text_length': len(epub_result.text_content),
                'total_word_count': sum(ch.word_count for ch in epub_result.chapters),
                'images_processed': len(image_descriptions) if image_descriptions else 0,
                'tts_enabled': tts_results is not None,
                'cleaning_stats': asdict(epub_result.cleaning_stats) if epub_result.cleaning_stats else None
            },
            'pipeline_info': {
                'epub2tts_version': '0.1.0',
                'processing_timestamp': time.time(),
                'config_used': {
                    'text_format': self.config.output.text_format,
                    'tts_model': self.config.tts.model if tts_results else None,
                    'image_model': self.config.image_description.model if image_descriptions else None
                }
            }
        }

        if tts_results:
            metadata['tts_results'] = tts_results

        if image_descriptions:
            metadata['image_descriptions'] = [
                {
                    'image_file': Path(desc.image_path).name,
                    'description': desc.description,
                    'confidence': desc.confidence,
                    'model_used': desc.model_used
                }
                for desc in image_descriptions
            ]

        # Save comprehensive metadata
        metadata_file = output_dir / "processing_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Generate processing report
        self._generate_processing_report(
            epub_result,
            image_descriptions,
            tts_results,
            output_dir
        )

        self.logger.info(f"Final outputs generated in {output_dir}")

    def _generate_processing_report(
        self,
        epub_result: ProcessingResult,
        image_descriptions: List[ImageDescription],
        tts_results: Optional[Dict[str, Any]],
        output_dir: Path
    ) -> None:
        """Generate human-readable processing report."""
        report_file = output_dir / "processing_report.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("EPUB to TTS Processing Report\n")
            f.write("=" * 40 + "\n\n")

            # Book information
            f.write("📖 Book Information:\n")
            for key, value in epub_result.metadata.items():
                if value:
                    f.write(f"  {key.title()}: {value}\n")
            f.write("\n")

            # Text processing stats
            f.write("📄 Text Processing:\n")
            f.write(f"  Chapters extracted: {len(epub_result.chapters)}\n")
            f.write(f"  Total text length: {len(epub_result.text_content):,} characters\n")
            f.write(f"  Total word count: {sum(ch.word_count for ch in epub_result.chapters):,} words\n")

            if epub_result.cleaning_stats:
                stats = epub_result.cleaning_stats
                f.write(f"  Text cleaning: {stats.characters_removed:,} characters removed\n")
                f.write(f"  Compression ratio: {stats.compression_ratio:.1%}\n")
            f.write("\n")

            # Chapter breakdown
            f.write("📚 Chapters:\n")
            for chapter in epub_result.chapters:
                f.write(f"  {chapter.chapter_num}. {chapter.title}\n")
                f.write(f"     Words: {chapter.word_count:,}, Duration: {chapter.estimated_duration:.1f} min\n")
            f.write("\n")

            # Image processing
            if image_descriptions:
                f.write("🖼️  Image Processing:\n")
                f.write(f"  Images processed: {len(image_descriptions)}\n")
                high_confidence = len([d for d in image_descriptions if d.confidence > 0.7])
                f.write(f"  High confidence descriptions: {high_confidence}\n")
                avg_confidence = sum(d.confidence for d in image_descriptions) / len(image_descriptions)
                f.write(f"  Average confidence: {avg_confidence:.2f}\n")
                f.write("\n")

            # TTS results
            if tts_results:
                f.write("🔊 TTS Generation:\n")
                f.write(f"  Chapters processed: {tts_results['successful_chapters']}/{tts_results['total_chapters']}\n")
                f.write(f"  Total audio duration: {tts_results['total_audio_duration']:.1f} minutes\n")
                if tts_results.get('merged_file'):
                    f.write(f"  Merged audiobook: {Path(tts_results['merged_file']).name}\n")
                f.write("\n")

            f.write("✅ Processing completed successfully!\n")

    def start_ui(self) -> bool:
        """
        Start the UI manager if available.

        Returns:
            True if UI was started successfully, False otherwise
        """
        if self.ui_manager and not self.ui_manager.is_running:
            return self.ui_manager.start()
        return False

    def stop_ui(self) -> None:
        """Stop the UI manager if running."""
        if self.ui_manager and self.ui_manager.is_running:
            self.ui_manager.stop()

    def cleanup(self) -> None:
        """Clean up all pipeline resources."""
        if self.tts_pipeline:
            # TTS cleanup if needed
            pass

        if self.image_pipeline:
            self.image_pipeline.cleanup()

        self.logger.debug("Pipeline orchestrator cleaned up")

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get status of all pipelines."""
        return {
            'epub_processor': True,  # Always available
            'tts_pipeline': self.tts_pipeline is not None,
            'image_pipeline': self.image_pipeline is not None,
            'tts_model': self.config.tts.model if self.tts_pipeline else None,
            'image_model': self.config.image_description.model if self.image_pipeline else None
        }