"""
Main EPUB processing module.

This module orchestrates the entire EPUB to text conversion process,
using OmniParser for EPUB extraction and text cleaning for TTS optimization.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import shutil

from omniparser import parse_document
from omniparser.models import Document as OmniDocument
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
    Main processor for EPUB to text conversion using OmniParser.
    """

    def __init__(self, config: Config, progress_tracker=None):
        """
        Initialize EPUB processor with OmniParser and text cleaning.

        Args:
            config: Configuration object
            progress_tracker: Optional progress tracker for UI updates
        """
        self.config = config
        self.progress_tracker = progress_tracker

        # Initialize text cleaner for epub2tts-specific cleaning
        self.cleaner = TextCleaner()

        # Create temp directory if needed
        self.temp_dir = Path(config.processing.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"EPUB processor initialized with OmniParser and temp dir: {self.temp_dir}")

    def _omni_to_epub2tts_chapter(self, omni_chapter, chapter_num: int) -> Chapter:
        """
        Convert OmniParser Chapter to epub2tts Chapter.

        Args:
            omni_chapter: OmniParser chapter object
            chapter_num: Chapter number

        Returns:
            epub2tts Chapter object
        """
        estimated_duration = omni_chapter.word_count / 200.0  # 200 WPM
        return Chapter(
            chapter_num=chapter_num,
            title=omni_chapter.title,
            content=omni_chapter.content,
            word_count=omni_chapter.word_count,
            estimated_duration=estimated_duration,
            confidence=1.0  # OmniParser has high confidence from TOC
        )

    def _omni_metadata_to_dict(self, omni_metadata) -> Dict[str, Any]:
        """
        Convert OmniParser Metadata to dictionary.

        Args:
            omni_metadata: OmniParser metadata object

        Returns:
            Metadata dictionary
        """
        return {
            'title': omni_metadata.title,
            'author': omni_metadata.author,
            'authors': omni_metadata.authors or [omni_metadata.author] if omni_metadata.author else [],
            'publisher': omni_metadata.publisher,
            'publication_date': str(omni_metadata.publication_date) if omni_metadata.publication_date else None,
            'language': omni_metadata.language,
            'identifier': omni_metadata.isbn,
            'description': omni_metadata.description,
            'subjects': omni_metadata.tags or [],
            'original_format': 'epub',
            'file_size': omni_metadata.file_size
        }

    def _omni_images_to_list(self, omni_images) -> List[Dict[str, Any]]:
        """
        Convert OmniParser ImageReferences to list of dicts.

        Args:
            omni_images: List of OmniParser image references

        Returns:
            List of image info dictionaries
        """
        return [
            {
                'file_path': img.file_path,
                'alt_text': img.alt_text or '',
                'position': img.position,
                'format': img.format
            }
            for img in omni_images
        ]

    def process_epub(self, epub_path: Path, output_dir: Optional[Path] = None) -> ProcessingResult:
        """
        Process EPUB file using OmniParser.

        Args:
            epub_path: Path to EPUB file
            output_dir: Optional output directory for results

        Returns:
            ProcessingResult with all extracted and processed data
        """
        logger.info(f"Starting EPUB processing with OmniParser: {epub_path}")
        start_time = time.time()

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

        try:
            # Parse with OmniParser
            logger.info(f"Parsing EPUB with OmniParser: {epub_path}")
            omni_doc = parse_document(epub_path)

            # Convert chapters
            logger.info(f"Converting {len(omni_doc.chapters)} chapters from OmniParser format")
            chapters = [
                self._omni_to_epub2tts_chapter(ch, idx + 1)
                for idx, ch in enumerate(omni_doc.chapters)
            ]

            # Apply epub2tts text cleaning to full content
            logger.info("Applying epub2tts text cleaning...")
            cleaned_content = self.cleaner.clean_text(omni_doc.content)
            cleaning_stats = self.cleaner.get_cleaning_stats()

            # Clean chapter content too
            logger.info("Cleaning individual chapter content...")
            for chapter in chapters:
                chapter.content = self.cleaner.clean_text(chapter.content)

            # Convert metadata
            metadata_dict = self._omni_metadata_to_dict(omni_doc.metadata)

            # Convert images
            image_info = self._omni_images_to_list(omni_doc.images)

            # Apply chapter post-processing
            chapters = self._post_process_chapters(chapters)

            processing_time = time.time() - start_time

            result = ProcessingResult(
                success=True,
                text_content=cleaned_content,
                chapters=chapters,
                metadata=metadata_dict,
                image_info=image_info,
                cleaning_stats=cleaning_stats,
                error_message=None,
                processing_time=processing_time
            )

            # Save results if output directory specified
            if output_dir:
                self._save_results(
                    epub_path,
                    output_dir,
                    result.text_content,
                    result.chapters,
                    result.metadata,
                    result.image_info
                )

            logger.info(
                f"Successfully processed {epub_path} in {processing_time:.2f}s: "
                f"{len(chapters)} chapters, {len(cleaned_content)} characters"
            )
            return result

        except Exception as e:
            error_msg = f"Error processing EPUB {epub_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            processing_time = time.time() - start_time

            return ProcessingResult(
                success=False,
                text_content="",
                chapters=[],
                metadata={},
                image_info=[],
                cleaning_stats=CleaningStats(0, 0, 0, 0, 1),
                error_message=error_msg,
                processing_time=processing_time
            )

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
        image_info: List[Dict[str, Any]]
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

        # Copy images from OmniParser's extracted paths if they exist
        if image_info:
            images_dir = output_dir / f"{base_name}_images"
            images_dir.mkdir(exist_ok=True)

            copied_count = 0
            for info in image_info:
                source_path = Path(info.get('file_path', ''))
                if source_path.exists() and source_path.is_file():
                    dest_file = images_dir / source_path.name
                    shutil.copy2(source_path, dest_file)

                    # Update paths to the permanent location
                    info['file_path'] = str(dest_file)
                    info['local_path'] = str(dest_file)
                    copied_count += 1
                    logger.debug(f"Copied image: {source_path.name} -> {dest_file}")

            if copied_count > 0:
                logger.info(f"Copied {copied_count} images to {images_dir}")

        logger.info(f"Results saved to {output_dir}")

    def validate_epub(self, epub_path: Path) -> List[str]:
        """
        Validate EPUB file using OmniParser.

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

        # Try to parse with OmniParser to validate format
        try:
            omni_doc = parse_document(epub_path)
            if not omni_doc.metadata or not omni_doc.metadata.title:
                issues.append("No title metadata found - file may be corrupted")
            if not omni_doc.content or len(omni_doc.content.strip()) == 0:
                issues.append("No text content found - file may be corrupted")
        except Exception as e:
            issues.append(f"OmniParser validation failed: {e}")

        return issues

    def get_processing_info(self, epub_path: Path) -> Dict[str, Any]:
        """
        Get information about EPUB using OmniParser without full processing.

        Args:
            epub_path: Path to EPUB file

        Returns:
            Dictionary with basic information
        """
        try:
            # Get file stats
            file_stats = epub_path.stat()

            # Parse with OmniParser for quick metadata extraction
            omni_doc = parse_document(epub_path)

            # Convert metadata
            metadata = self._omni_metadata_to_dict(omni_doc.metadata)

            # Get content metrics
            text_length = len(omni_doc.content)
            estimated_words = omni_doc.metadata.word_count or len(omni_doc.content.split())
            estimated_processing_time = text_length / 10000  # Rough estimate

            info = {
                'file_size': file_stats.st_size,
                'file_modified': file_stats.st_mtime,
                'metadata': metadata,
                'chapter_count': len(omni_doc.chapters),
                'image_count': len(omni_doc.images),
                'estimated_text_length': text_length,
                'estimated_word_count': estimated_words,
                'estimated_processing_time': estimated_processing_time,
                'estimated_audio_duration': estimated_words / 200.0  # minutes at 200 WPM
            }

            return info

        except Exception as e:
            logger.error(f"Error getting EPUB info: {e}")
            return {'error': str(e)}