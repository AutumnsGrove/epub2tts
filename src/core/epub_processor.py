"""
Main EPUB processing module.

This module orchestrates the entire EPUB to text conversion process,
integrating Pandoc extraction, text cleaning, and chapter segmentation.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import shutil

from core.pandoc_wrapper import PandocConverter, PandocError
from core.text_cleaner import TextCleaner, Chapter, CleaningStats
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of EPUB processing operation."""
    success: bool
    text_content: str
    chapters: List[Chapter]
    metadata: Dict[str, Any]
    image_info: List[Dict[str, Any]]
    cleaning_stats: CleaningStats
    error_message: Optional[str] = None
    processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        result_dict = asdict(self)
        # Convert chapters to dictionaries
        result_dict['chapters'] = [asdict(chapter) for chapter in self.chapters]
        result_dict['cleaning_stats'] = asdict(self.cleaning_stats)
        return result_dict

    def save_to_json(self, output_path: Path) -> None:
        """Save result to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Processing result saved to {output_path}")


class EPUBProcessor:
    """
    Main processor for EPUB to text conversion.
    """

    def __init__(self, config: Config):
        """
        Initialize EPUB processor with configuration.

        Args:
            config: Configuration object
        """
        self.config = config
        self.pandoc = PandocConverter(config.processing.pandoc_path)
        self.cleaner = TextCleaner()

        # Create temp directory if needed
        self.temp_dir = Path(config.processing.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"EPUB processor initialized with temp dir: {self.temp_dir}")

    def process_epub(self, epub_path: Path, output_dir: Optional[Path] = None) -> ProcessingResult:
        """
        Process EPUB file through complete pipeline.

        Args:
            epub_path: Path to EPUB file
            output_dir: Optional output directory for results

        Returns:
            ProcessingResult with all extracted and processed data
        """
        import time
        start_time = time.time()

        logger.info(f"Starting EPUB processing: {epub_path}")

        if not epub_path.exists():
            error_msg = f"EPUB file not found: {epub_path}"
            logger.error(error_msg)
            return ProcessingResult(
                success=False,
                text_content="",
                chapters=[],
                metadata={},
                image_info=[],
                cleaning_stats=CleaningStats(0, 0, 0, 0, 1),
                error_message=error_msg
            )

        temp_media_dir = None

        try:
            # Step 1: Extract metadata
            logger.info("Extracting metadata...")
            metadata = self.pandoc.extract_metadata(epub_path)

            # Step 2: Convert to markdown
            logger.info("Converting EPUB to markdown...")
            markdown_content, temp_media_dir = self.pandoc.extract_to_markdown(
                epub_path,
                extract_images=self.config.image_description.enabled
            )

            # Step 3: Extract image information
            image_info = []
            if self.config.image_description.enabled:
                logger.info("Extracting image information...")
                image_info = self.pandoc.extract_images_info(epub_path)

            # Step 4: Clean text
            logger.info("Cleaning text...")
            cleaned_text = self.cleaner.clean_text(markdown_content)
            cleaning_stats = self.cleaner.get_cleaning_stats()

            # Step 5: Segment chapters
            logger.info("Segmenting chapters...")
            chapters = self.cleaner.segment_chapters(cleaned_text)

            # Step 6: Apply chapter-specific processing
            chapters = self._post_process_chapters(chapters)

            # Step 7: Save results if output directory specified
            copied_image_paths = {}
            if output_dir:
                copied_image_paths = self._save_results(
                    epub_path,
                    output_dir,
                    cleaned_text,
                    chapters,
                    metadata,
                    image_info,
                    temp_media_dir
                ) or {}

            processing_time = time.time() - start_time

            result = ProcessingResult(
                success=True,
                text_content=cleaned_text,
                chapters=chapters,
                metadata=metadata,
                image_info=image_info,
                cleaning_stats=cleaning_stats,
                processing_time=processing_time
            )

            logger.info(
                f"EPUB processing completed successfully in {processing_time:.2f}s: "
                f"{len(chapters)} chapters, {len(cleaned_text)} characters"
            )

            return result

        except Exception as e:
            error_msg = f"Error processing EPUB {epub_path}: {e}"
            logger.error(error_msg, exc_info=True)

            return ProcessingResult(
                success=False,
                text_content="",
                chapters=[],
                metadata={},
                image_info=[],
                cleaning_stats=CleaningStats(0, 0, 0, 0, 1),
                error_message=error_msg,
                processing_time=time.time() - start_time
            )

        finally:
            # Cleanup temporary files
            if temp_media_dir and temp_media_dir.exists():
                try:
                    shutil.rmtree(temp_media_dir)
                    logger.debug(f"Cleaned up temp media directory: {temp_media_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")

    def _post_process_chapters(self, chapters: List[Chapter]) -> List[Chapter]:
        """
        Apply post-processing to chapters.

        Args:
            chapters: List of chapters to process

        Returns:
            List of processed chapters
        """
        processed_chapters = []
        current_chapter_num = 1

        for chapter in chapters:
            # Filter out very short chapters if configured
            if chapter.word_count < self.config.chapters.min_words_per_chapter:
                logger.debug(f"Skipping short chapter: {chapter.title} ({chapter.word_count} words)")
                continue

            # Split very long chapters if configured
            if chapter.word_count > self.config.chapters.max_words_per_chunk:
                logger.info(f"Splitting long chapter: {chapter.title} ({chapter.word_count} words)")
                split_chapters = self._split_long_chapter(chapter, current_chapter_num)
                processed_chapters.extend(split_chapters)
                current_chapter_num += len(split_chapters)
            else:
                # Renumber chapter to sequential numbering
                renumbered_chapter = Chapter(
                    chapter_num=current_chapter_num,
                    title=chapter.title,
                    content=chapter.content,
                    word_count=chapter.word_count,
                    estimated_duration=chapter.estimated_duration,
                    confidence=chapter.confidence
                )
                processed_chapters.append(renumbered_chapter)
                current_chapter_num += 1

        return processed_chapters

    def _split_long_chapter(self, chapter: Chapter, starting_num: int) -> List[Chapter]:
        """
        Split a long chapter into smaller chunks.

        Args:
            chapter: Chapter to split
            starting_num: Starting chapter number for the chunks

        Returns:
            List of chapter chunks
        """
        max_words = self.config.chapters.max_words_per_chunk
        words = chapter.content.split()
        chunks = []

        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_content = ' '.join(chunk_words)

            # Create more descriptive titles for split chapters
            part_num = len(chunks) + 1
            if len(chunks) == 0 and len(words) <= max_words:
                # If it's the only chunk, don't add "Part 1"
                chunk_title = chapter.title
            else:
                chunk_title = f"{chapter.title} - Part {part_num}"

            chunk_num = starting_num + len(chunks)

            chunk = Chapter(
                chapter_num=chunk_num,
                title=chunk_title,
                content=chunk_content,
                word_count=len(chunk_words),
                estimated_duration=len(chunk_words) / 200.0,
                confidence=chapter.confidence
            )
            chunks.append(chunk)

        logger.debug(f"Split chapter into {len(chunks)} chunks (chapters {starting_num}-{starting_num + len(chunks) - 1})")
        return chunks

    def _save_results(
        self,
        epub_path: Path,
        output_dir: Path,
        text_content: str,
        chapters: List[Chapter],
        metadata: Dict[str, Any],
        image_info: List[Dict[str, Any]],
        temp_media_dir: Optional[Path] = None
    ) -> None:
        """
        Save processing results to output directory.

        Args:
            epub_path: Original EPUB file path
            output_dir: Output directory
            text_content: Cleaned text content
            chapters: List of chapters
            metadata: Book metadata
            image_info: Image information
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Base filename from EPUB
        base_name = epub_path.stem

        # Save full text
        if self.config.output.text_format == "plain":
            text_file = output_dir / f"{base_name}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)

        elif self.config.output.text_format == "json":
            json_file = output_dir / f"{base_name}.json"
            result_data = {
                'metadata': metadata,
                'text': text_content,
                'chapters': [asdict(chapter) for chapter in chapters],
                'images': image_info
            }
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

        # Save individual chapters if configured
        if self.config.output.save_intermediate:
            chapters_dir = output_dir / f"{base_name}_chapters"
            chapters_dir.mkdir(exist_ok=True)

            for chapter in chapters:
                chapter_file = chapters_dir / f"chapter_{chapter.chapter_num:03d}.txt"
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {chapter.title}\n\n{chapter.content}")

        # Save metadata
        if self.config.output.create_metadata:
            metadata_file = output_dir / f"{base_name}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Generate table of contents
        if self.config.output.generate_toc:
            toc_file = output_dir / f"{base_name}_toc.txt"
            with open(toc_file, 'w', encoding='utf-8') as f:
                f.write("Table of Contents\n")
                f.write("=================\n\n")
                for chapter in chapters:
                    f.write(f"Chapter {chapter.chapter_num}: {chapter.title}\n")
                    f.write(f"  Words: {chapter.word_count}\n")
                    f.write(f"  Estimated duration: {chapter.estimated_duration:.1f} minutes\n\n")

        # Copy images if they were extracted - DO THIS BEFORE ANY CLEANUP
        copied_image_paths = {}
        if temp_media_dir and temp_media_dir.exists() and image_info:
            images_dir = output_dir / f"{base_name}_images"
            images_dir.mkdir(exist_ok=True)

            # Look for images in the media directory
            media_files = list(temp_media_dir.glob("**/*"))
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'}

            copied_count = 0
            for media_file in media_files:
                if media_file.is_file() and media_file.suffix.lower() in image_extensions:
                    dest_file = images_dir / media_file.name
                    shutil.copy2(media_file, dest_file)

                    # Track the mapping of old path to new path
                    copied_image_paths[str(media_file)] = str(dest_file)
                    copied_image_paths[media_file.name] = str(dest_file)

                    copied_count += 1
                    logger.debug(f"Copied image: {media_file.name} -> {dest_file}")

            if copied_count > 0:
                logger.info(f"Copied {copied_count} images to {images_dir}")

            # Update image_info with new persistent paths
            for info in image_info:
                old_path = info.get('file_path', '')
                filename = Path(old_path).name

                if filename in copied_image_paths:
                    info['file_path'] = copied_image_paths[filename]
                    info['local_path'] = copied_image_paths[filename]
                    logger.debug(f"Updated image path: {filename} -> {info['file_path']}")

        logger.info(f"Results saved to {output_dir}")

        # Return the updated image paths for the orchestrator
        return copied_image_paths

    def validate_epub(self, epub_path: Path) -> List[str]:
        """
        Validate EPUB file and return any issues found.

        Args:
            epub_path: Path to EPUB file

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check file exists
        if not epub_path.exists():
            issues.append(f"File does not exist: {epub_path}")
            return issues

        # Check file extension
        if epub_path.suffix.lower() != '.epub':
            issues.append(f"File does not have .epub extension: {epub_path}")

        # Check file size
        try:
            file_size = epub_path.stat().st_size
            if file_size == 0:
                issues.append("File is empty")
            elif file_size < 1024:  # Less than 1KB
                issues.append("File is suspiciously small")
        except Exception as e:
            issues.append(f"Cannot read file stats: {e}")

        # Try to extract metadata to validate format
        try:
            metadata = self.pandoc.extract_metadata(epub_path)
            if not metadata:
                issues.append("No metadata found - file may be corrupted")
        except PandocError as e:
            issues.append(f"Pandoc validation failed: {e}")
        except Exception as e:
            issues.append(f"Unexpected validation error: {e}")

        return issues

    def get_processing_info(self, epub_path: Path) -> Dict[str, Any]:
        """
        Get information about EPUB without full processing.

        Args:
            epub_path: Path to EPUB file

        Returns:
            Dictionary with basic information
        """
        try:
            # Get file stats
            file_stats = epub_path.stat()

            # Get metadata
            metadata = self.pandoc.extract_metadata(epub_path)

            # Quick text extraction for size estimation
            markdown_content, temp_media_dir = self.pandoc.extract_to_markdown(
                epub_path, extract_images=False
            )

            # Cleanup temp directory
            if temp_media_dir and temp_media_dir.exists():
                shutil.rmtree(temp_media_dir)

            # Estimate processing metrics
            text_length = len(markdown_content)
            estimated_words = len(markdown_content.split())
            estimated_processing_time = text_length / 10000  # Rough estimate

            info = {
                'file_size': file_stats.st_size,
                'file_modified': file_stats.st_mtime,
                'metadata': metadata,
                'estimated_text_length': text_length,
                'estimated_word_count': estimated_words,
                'estimated_processing_time': estimated_processing_time,
                'estimated_audio_duration': estimated_words / 200.0  # minutes
            }

            return info

        except Exception as e:
            logger.error(f"Error getting EPUB info: {e}")
            return {'error': str(e)}