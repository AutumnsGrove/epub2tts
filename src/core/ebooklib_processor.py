"""
Modern EPUB processing using EbookLib.

This module provides a more robust EPUB processing system using EbookLib
for native EPUB parsing, eliminating the brittleness of regex-based
chapter detection and providing accurate TOC-based chapter boundaries.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import shutil
import html
from html.parser import HTMLParser

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from core.text_cleaner import TextCleaner, Chapter, CleaningStats
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class EbookMetadata:
    """Enhanced metadata structure for EPUB files."""
    title: Optional[str] = None
    authors: List[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    language: Optional[str] = None
    identifier: Optional[str] = None
    description: Optional[str] = None
    subjects: List[str] = None
    rights: Optional[str] = None
    spine_length: int = 0
    has_toc: bool = False
    epub_version: Optional[str] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.subjects is None:
            self.subjects = []


@dataclass
class TocEntry:
    """Table of Contents entry with hierarchical structure."""
    title: str
    href: Optional[str] = None
    level: int = 1
    children: List['TocEntry'] = None
    item_id: Optional[str] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class HTMLTextExtractor(HTMLParser):
    """Extract clean text from HTML content."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        # Add paragraph breaks for block elements
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n\n')
        elif tag == 'br':
            self.text_parts.append('\n')

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in ('script', 'style'):
            # Clean and normalize whitespace
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self) -> str:
        """Get extracted text with normalized whitespace."""
        text = ' '.join(self.text_parts)
        # Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()


class EbookLibProcessor:
    """
    Modern EPUB processor using EbookLib for native parsing.
    """

    def __init__(self, config: Config):
        """
        Initialize EPUB processor with configuration.

        Args:
            config: Configuration object
        """
        self.config = config
        self.cleaner = TextCleaner()

        # Create temp directory if needed
        self.temp_dir = Path(config.processing.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"EbookLib processor initialized with temp dir: {self.temp_dir}")

    def process_epub(self, epub_path: Path, output_dir: Optional[Path] = None) -> 'ProcessingResult':
        """
        Process EPUB file using EbookLib.

        Args:
            epub_path: Path to EPUB file
            output_dir: Optional output directory for results

        Returns:
            ProcessingResult with all extracted and processed data
        """
        import time
        from core.epub_processor import ProcessingResult  # Import here to avoid circular import

        start_time = time.time()
        logger.info(f"Starting EbookLib processing: {epub_path}")

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
            # Step 1: Load EPUB
            logger.info("Loading EPUB with EbookLib...")
            book = epub.read_epub(str(epub_path))

            # Step 2: Extract metadata
            logger.info("Extracting metadata...")
            metadata = self._extract_metadata(book)

            # Step 3: Extract TOC structure
            logger.info("Extracting table of contents...")
            toc_structure = self._extract_toc_structure(book)

            # Step 4: Extract content with TOC-based chapter detection
            logger.info("Extracting content with native chapter detection...")
            text_content, chapters = self._extract_content_with_chapters(book, toc_structure)

            # Step 5: Extract images if enabled
            image_info = []
            if self.config.image_description.enabled:
                logger.info("Extracting image information...")
                image_info, temp_media_dir = self._extract_images(book, epub_path)

            # Step 6: Clean text
            logger.info("Cleaning text...")
            cleaned_text = self.cleaner.clean_text(text_content)
            cleaning_stats = self.cleaner.get_cleaning_stats()

            # Step 7: Apply final chapter processing
            logger.info("Post-processing chapters...")
            processed_chapters = self._post_process_chapters(chapters)

            # Step 8: Save results if output directory specified
            copied_image_paths = {}
            if output_dir:
                copied_image_paths = self._save_results(
                    epub_path,
                    output_dir,
                    cleaned_text,
                    processed_chapters,
                    metadata,
                    image_info,
                    temp_media_dir
                ) or {}

            processing_time = time.time() - start_time

            result = ProcessingResult(
                success=True,
                text_content=cleaned_text,
                chapters=processed_chapters,
                metadata=asdict(metadata),
                image_info=image_info,
                cleaning_stats=cleaning_stats,
                processing_time=processing_time
            )

            logger.info(
                f"EbookLib processing completed successfully in {processing_time:.2f}s: "
                f"{len(processed_chapters)} chapters, {len(cleaned_text)} characters"
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

    def _extract_metadata(self, book: epub.EpubBook) -> EbookMetadata:
        """
        Extract comprehensive metadata from EPUB.

        Args:
            book: EbookLib EPUB book object

        Returns:
            EbookMetadata object with extracted information
        """
        metadata = EbookMetadata()

        try:
            # Title
            title_meta = book.get_metadata('DC', 'title')
            if title_meta:
                metadata.title = title_meta[0][0] if title_meta[0] else None

            # Authors
            creator_meta = book.get_metadata('DC', 'creator')
            if creator_meta:
                metadata.authors = [creator[0] for creator in creator_meta if creator[0]]

            # Publisher
            publisher_meta = book.get_metadata('DC', 'publisher')
            if publisher_meta:
                metadata.publisher = publisher_meta[0][0] if publisher_meta[0] else None

            # Publication date
            date_meta = book.get_metadata('DC', 'date')
            if date_meta:
                metadata.publication_date = date_meta[0][0] if date_meta[0] else None

            # Language
            language_meta = book.get_metadata('DC', 'language')
            if language_meta:
                metadata.language = language_meta[0][0] if language_meta[0] else None

            # Identifier
            identifier_meta = book.get_metadata('DC', 'identifier')
            if identifier_meta:
                metadata.identifier = identifier_meta[0][0] if identifier_meta[0] else None

            # Description
            description_meta = book.get_metadata('DC', 'description')
            if description_meta:
                metadata.description = description_meta[0][0] if description_meta[0] else None

            # Subjects
            subject_meta = book.get_metadata('DC', 'subject')
            if subject_meta:
                metadata.subjects = [subject[0] for subject in subject_meta if subject[0]]

            # Rights
            rights_meta = book.get_metadata('DC', 'rights')
            if rights_meta:
                metadata.rights = rights_meta[0][0] if rights_meta[0] else None

            # Spine length
            metadata.spine_length = len(book.spine)

            # Check if TOC exists
            metadata.has_toc = len(book.toc) > 0

            # EPUB version (from OPF)
            try:
                opf_meta = book.get_metadata('OPF', 'meta')
                for meta in opf_meta:
                    if 'version' in str(meta):
                        metadata.epub_version = str(meta)
                        break
            except:
                pass

            logger.info(f"Extracted metadata: {metadata.title} by {', '.join(metadata.authors)}")

        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")

        return metadata

    def _extract_toc_structure(self, book: epub.EpubBook) -> List[TocEntry]:
        """
        Extract hierarchical table of contents structure.

        Args:
            book: EbookLib EPUB book object

        Returns:
            List of TocEntry objects representing the TOC structure
        """
        toc_entries = []

        try:
            def process_toc_item(item, level=1):
                """Recursively process TOC items."""
                if isinstance(item, epub.Link):
                    entry = TocEntry(
                        title=item.title,
                        href=item.href,
                        level=level,
                        item_id=getattr(item, 'uid', None)
                    )
                    return entry
                elif isinstance(item, tuple) and len(item) == 2:
                    # (Section, [items])
                    section, items = item
                    if isinstance(section, epub.Section):
                        section_entry = TocEntry(
                            title=section.title,
                            level=level
                        )
                        for sub_item in items:
                            child_entry = process_toc_item(sub_item, level + 1)
                            if child_entry:
                                section_entry.children.append(child_entry)
                        return section_entry
                elif isinstance(item, list):
                    # Direct list of items
                    entries = []
                    for sub_item in item:
                        child_entry = process_toc_item(sub_item, level)
                        if child_entry:
                            entries.append(child_entry)
                    return entries
                return None

            # Process the TOC
            for item in book.toc:
                entry = process_toc_item(item)
                if entry:
                    if isinstance(entry, list):
                        toc_entries.extend(entry)
                    else:
                        toc_entries.append(entry)

            logger.info(f"Extracted TOC structure with {len(toc_entries)} top-level entries")

        except Exception as e:
            logger.warning(f"Error extracting TOC structure: {e}")

        return toc_entries

    def _extract_content_with_chapters(self, book: epub.EpubBook, toc_structure: List[TocEntry]) -> Tuple[str, List[Chapter]]:
        """
        Extract content using TOC-based chapter detection.

        Args:
            book: EbookLib EPUB book object
            toc_structure: TOC structure for chapter boundaries

        Returns:
            Tuple of (full_text_content, list_of_chapters)
        """
        chapters = []
        full_text = []

        try:
            # Create mapping of href to spine order
            spine_order = {}
            for idx, (item_id, linear) in enumerate(book.spine):
                item = book.get_item_with_id(item_id)
                if item and hasattr(item, 'file_name'):
                    spine_order[item.file_name] = idx

            # If we have TOC structure, use it for chapter boundaries
            if toc_structure:
                chapters = self._extract_chapters_from_toc(book, toc_structure, spine_order)
            else:
                # Fallback: process spine items as chapters
                logger.info("No TOC structure found, processing spine items as chapters")
                chapters = self._extract_chapters_from_spine(book)

            # Build full text from chapters
            for chapter in chapters:
                full_text.append(f"\n\n[CHAPTER_START: {chapter.title}]\n\n")
                full_text.append(chapter.content)
                full_text.append("\n\n")

            full_text_content = ''.join(full_text)

            logger.info(f"Extracted {len(chapters)} chapters with {len(full_text_content)} total characters")

        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            # Fallback to simple extraction
            full_text_content = self._extract_simple_text(book)
            chapters = [Chapter(
                chapter_num=1,
                title="Full Text",
                content=full_text_content,
                word_count=len(full_text_content.split()),
                estimated_duration=len(full_text_content.split()) / 200.0
            )]

        return full_text_content, chapters

    def _extract_chapters_from_toc(self, book: epub.EpubBook, toc_structure: List[TocEntry], spine_order: Dict[str, int]) -> List[Chapter]:
        """
        Extract chapters based on TOC structure.

        Args:
            book: EbookLib EPUB book object
            toc_structure: TOC structure
            spine_order: Mapping of file names to spine order

        Returns:
            List of Chapter objects
        """
        chapters = []
        chapter_num = 1

        def process_toc_entries(entries: List[TocEntry], level_prefix: str = ""):
            nonlocal chapter_num

            for entry in entries:
                if entry.href:
                    # Extract content for this TOC entry
                    content = self._extract_content_for_href(book, entry.href)
                    if content.strip():
                        # Determine title with hierarchy
                        title = f"{level_prefix}{entry.title}" if level_prefix else entry.title

                        chapter = Chapter(
                            chapter_num=chapter_num,
                            title=title,
                            content=content,
                            word_count=len(content.split()),
                            estimated_duration=len(content.split()) / 200.0,
                            confidence=1.0  # High confidence for TOC-based detection
                        )
                        chapters.append(chapter)
                        chapter_num += 1

                # Process children with hierarchy indication
                if entry.children:
                    child_prefix = f"{entry.title} - " if not entry.href else ""
                    process_toc_entries(entry.children, level_prefix + child_prefix)

        process_toc_entries(toc_structure)
        return chapters

    def _extract_chapters_from_spine(self, book: epub.EpubBook) -> List[Chapter]:
        """
        Extract chapters from spine items when no TOC is available.

        Args:
            book: EbookLib EPUB book object

        Returns:
            List of Chapter objects
        """
        chapters = []

        for idx, (item_id, linear) in enumerate(book.spine):
            if linear == 'no':
                continue  # Skip non-linear items

            item = book.get_item_with_id(item_id)
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = self._extract_text_from_item(item)
                if content.strip():
                    # Try to extract a title from the content
                    title = self._extract_title_from_content(content) or f"Chapter {idx + 1}"

                    chapter = Chapter(
                        chapter_num=idx + 1,
                        title=title,
                        content=content,
                        word_count=len(content.split()),
                        estimated_duration=len(content.split()) / 200.0,
                        confidence=0.7  # Lower confidence for spine-based detection
                    )
                    chapters.append(chapter)

        return chapters

    def _extract_content_for_href(self, book: epub.EpubBook, href: str) -> str:
        """
        Extract text content for a specific href.

        Args:
            book: EbookLib EPUB book object
            href: HREF to extract content for

        Returns:
            Extracted text content
        """
        try:
            # Clean the href (remove fragments)
            clean_href = href.split('#')[0]

            # Find the item
            item = book.get_item_with_href(clean_href)
            if not item:
                # Try finding by file name
                for book_item in book.get_items():
                    if hasattr(book_item, 'file_name') and book_item.file_name == clean_href:
                        item = book_item
                        break

            if item:
                return self._extract_text_from_item(item)
            else:
                logger.warning(f"Could not find item for href: {href}")
                return ""

        except Exception as e:
            logger.warning(f"Error extracting content for href {href}: {e}")
            return ""

    def _extract_text_from_item(self, item) -> str:
        """
        Extract clean text from an EPUB item.

        Args:
            item: EPUB item object

        Returns:
            Extracted text content
        """
        try:
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                return ""

            # Get content as bytes and decode
            content_bytes = item.get_content()
            if isinstance(content_bytes, bytes):
                content_str = content_bytes.decode('utf-8', errors='ignore')
            else:
                content_str = str(content_bytes)

            # Parse HTML and extract text
            extractor = HTMLTextExtractor()
            extractor.feed(content_str)
            text = extractor.get_text()

            return text

        except Exception as e:
            logger.warning(f"Error extracting text from item: {e}")
            return ""

    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """
        Try to extract a title from content (first heading or significant line).

        Args:
            content: Text content

        Returns:
            Extracted title or None
        """
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:  # Reasonable title length
                # Check if it looks like a title
                if any(word in line.lower() for word in ['chapter', 'part', 'section']) or \
                   line[0].isupper() and not line.endswith('.'):
                    return line
        return None

    def _extract_simple_text(self, book: epub.EpubBook) -> str:
        """
        Simple text extraction as fallback.

        Args:
            book: EbookLib EPUB book object

        Returns:
            Extracted text content
        """
        text_parts = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = self._extract_text_from_item(item)
                if content.strip():
                    text_parts.append(content)
                    text_parts.append('\n\n')

        return ''.join(text_parts)

    def _extract_images(self, book: epub.EpubBook, epub_path: Path) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
        """
        Extract image information from EPUB.

        Args:
            book: EbookLib EPUB book object
            epub_path: Path to original EPUB file

        Returns:
            Tuple of (image_info_list, temp_media_directory)
        """
        images = []
        temp_media_dir = None

        try:
            # Create temporary directory for images
            temp_media_dir = Path(tempfile.mkdtemp(prefix="epub2tts_ebooklib_"))

            # Extract images
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    try:
                        # Save image to temp directory
                        image_path = temp_media_dir / item.file_name
                        image_path.parent.mkdir(parents=True, exist_ok=True)

                        with open(image_path, 'wb') as f:
                            f.write(item.get_content())

                        # Create image info
                        image_info = {
                            'file_path': str(image_path),
                            'relative_path': item.file_name,
                            'alt_text': '',  # Could be extracted from references
                            'context': '',
                            'file_size': len(item.get_content()),
                            'format': Path(item.file_name).suffix.lower(),
                            'media_type': getattr(item, 'media_type', '')
                        }
                        images.append(image_info)

                    except Exception as e:
                        logger.warning(f"Error extracting image {item.file_name}: {e}")

            logger.info(f"Extracted {len(images)} images to {temp_media_dir}")

        except Exception as e:
            logger.error(f"Error extracting images: {e}")

        return images, temp_media_dir

    def _post_process_chapters(self, chapters: List[Chapter]) -> List[Chapter]:
        """
        Apply post-processing to chapters (same as original implementation).

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
        Split a long chapter into smaller chunks (same as original implementation).

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
        metadata: EbookMetadata,
        image_info: List[Dict[str, Any]],
        temp_media_dir: Optional[Path] = None
    ) -> Optional[Dict[str, str]]:
        """
        Save processing results to output directory (adapted from original).

        Args:
            epub_path: Original EPUB file path
            output_dir: Output directory
            text_content: Cleaned text content
            chapters: List of chapters
            metadata: Book metadata
            image_info: Image information
            temp_media_dir: Temporary media directory

        Returns:
            Dictionary mapping old image paths to new paths
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
                'metadata': asdict(metadata),
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
                json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)

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

        # Copy images if they were extracted
        copied_image_paths = {}
        if temp_media_dir and temp_media_dir.exists() and image_info:
            images_dir = output_dir / f"{base_name}_images"
            images_dir.mkdir(exist_ok=True)

            copied_count = 0
            for info in image_info:
                try:
                    src_path = Path(info['file_path'])
                    if src_path.exists():
                        dest_file = images_dir / src_path.name
                        shutil.copy2(src_path, dest_file)

                        # Track the mapping
                        copied_image_paths[str(src_path)] = str(dest_file)
                        copied_image_paths[src_path.name] = str(dest_file)

                        # Update info with new path
                        info['file_path'] = str(dest_file)
                        info['local_path'] = str(dest_file)

                        copied_count += 1
                        logger.debug(f"Copied image: {src_path.name} -> {dest_file}")

                except Exception as e:
                    logger.warning(f"Error copying image {info.get('file_path', 'unknown')}: {e}")

            if copied_count > 0:
                logger.info(f"Copied {copied_count} images to {images_dir}")

        logger.info(f"Results saved to {output_dir}")
        return copied_image_paths

    def validate_epub(self, epub_path: Path) -> List[str]:
        """
        Validate EPUB file using EbookLib.

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

        # Try to load with EbookLib
        try:
            book = epub.read_epub(str(epub_path))

            # Basic validation
            if not book.get_items():
                issues.append("No items found in EPUB")

            if not book.spine:
                issues.append("No spine found in EPUB")

            # Check for required metadata
            title = book.get_metadata('DC', 'title')
            if not title:
                issues.append("No title metadata found")

        except Exception as e:
            issues.append(f"EbookLib validation failed: {e}")

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

            # Load EPUB for quick analysis
            book = epub.read_epub(str(epub_path))

            # Get metadata
            metadata = self._extract_metadata(book)

            # Estimate content size
            estimated_words = 0
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    text = self._extract_text_from_item(item)
                    estimated_words += len(text.split())

            info = {
                'file_size': file_stats.st_size,
                'file_modified': file_stats.st_mtime,
                'metadata': asdict(metadata),
                'estimated_word_count': estimated_words,
                'estimated_processing_time': estimated_words / 10000,  # Rough estimate
                'estimated_audio_duration': estimated_words / 200.0,  # minutes
                'spine_items': len(book.spine),
                'total_items': len(list(book.get_items())),
                'has_images': len([item for item in book.get_items() if item.get_type() == ebooklib.ITEM_IMAGE]) > 0
            }

            return info

        except Exception as e:
            logger.error(f"Error getting EPUB info: {e}")
            return {'error': str(e)}