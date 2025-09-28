"""
Enhanced text cleaner that combines regex patterns with modern NLP processing.

This module provides a bridge between the existing regex-based system and
the new modern text processing capabilities.
"""

import logging
from typing import List, Dict, Optional, Union
from pathlib import Path

from .modern_text_processor import ModernTextProcessor, SmartChapter

# Handle imports properly
try:
    from core.text_cleaner import TextCleaner, Chapter, CleaningStats
except ImportError:
    # Fallback for test environment
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from core.text_cleaner import TextCleaner, Chapter, CleaningStats

logger = logging.getLogger(__name__)


class EnhancedTextCleaner:
    """
    Enhanced text cleaner that combines regex patterns with modern NLP.

    Provides backward compatibility while offering modern processing capabilities.
    """

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        processor_mode: str = "modern",  # "legacy", "modern", "hybrid"
        spacy_model: str = "en_core_web_sm",
        chunk_size: int = 4000
    ):
        """
        Initialize enhanced text cleaner.

        Args:
            rules_path: Path to regex patterns YAML file
            processor_mode: Processing mode ("legacy", "modern", "hybrid")
            spacy_model: spaCy model for modern processing
            chunk_size: Target chunk size for text splitting
        """
        self.processor_mode = processor_mode

        # Initialize legacy processor
        self.legacy_cleaner = TextCleaner(rules_path)

        # Initialize modern processor if needed
        self.modern_processor = None
        if processor_mode in ["modern", "hybrid"]:
            try:
                self.modern_processor = ModernTextProcessor(spacy_model, chunk_size)
                logger.info(f"Initialized enhanced text cleaner in {processor_mode} mode")
            except Exception as e:
                logger.warning(f"Failed to initialize modern processor: {e}")
                if processor_mode == "modern":
                    logger.info("Falling back to legacy mode")
                    self.processor_mode = "legacy"

    def process_text(
        self,
        text: str,
        toc_data: Optional[List[Dict]] = None,
        return_modern_format: bool = True
    ) -> Union[List[Chapter], List[SmartChapter]]:
        """
        Process text using the configured processing mode.

        Args:
            text: Raw text to process
            toc_data: Optional table of contents for chapter detection
            return_modern_format: Whether to return SmartChapter objects

        Returns:
            List of Chapter or SmartChapter objects depending on mode
        """
        if self.processor_mode == "legacy":
            return self._process_legacy(text, return_modern_format)

        elif self.processor_mode == "modern":
            if self.modern_processor:
                return self.modern_processor.process_text(text, toc_data)
            else:
                logger.warning("Modern processor not available, using legacy")
                return self._process_legacy(text, return_modern_format)

        elif self.processor_mode == "hybrid":
            return self._process_hybrid(text, toc_data, return_modern_format)

        else:
            raise ValueError(f"Unknown processor mode: {self.processor_mode}")

    def _process_legacy(self, text: str, return_modern_format: bool) -> Union[List[Chapter], List[SmartChapter]]:
        """Process text using legacy regex-based cleaner."""
        # Clean text first
        cleaned_text = self.legacy_cleaner.clean_text(text)

        # Segment into chapters
        chapters = self.legacy_cleaner.segment_chapters(cleaned_text)

        if return_modern_format:
            # Convert to SmartChapter format
            smart_chapters = []
            for chapter in chapters:
                smart_chapter = SmartChapter(
                    chapter_num=chapter.chapter_num,
                    title=chapter.title,
                    content=chapter.content,
                    word_count=chapter.word_count,
                    estimated_duration=chapter.estimated_duration,
                    confidence=chapter.confidence,
                    semantic_summary=None,
                    topics=[],
                    named_entities=[],
                    chunks=self._create_simple_chunks(chapter.content)
                )
                smart_chapters.append(smart_chapter)
            return smart_chapters

        return chapters

    def _process_hybrid(
        self,
        text: str,
        toc_data: Optional[List[Dict]],
        return_modern_format: bool
    ) -> Union[List[Chapter], List[SmartChapter]]:
        """Process text using hybrid approach combining both methods."""
        # Step 1: Use legacy cleaner for text cleaning
        cleaned_text = self.legacy_cleaner.clean_text(text)

        # Step 2: Use modern processor for chapter detection if available
        if self.modern_processor and toc_data:
            # Use modern processor with TOC data
            smart_chapters = self.modern_processor.process_text(cleaned_text, toc_data)

            if not return_modern_format:
                # Convert back to legacy format
                legacy_chapters = []
                for smart_chapter in smart_chapters:
                    chapter = Chapter(
                        chapter_num=smart_chapter.chapter_num,
                        title=smart_chapter.title,
                        content=smart_chapter.content,
                        word_count=smart_chapter.word_count,
                        estimated_duration=smart_chapter.estimated_duration,
                        confidence=smart_chapter.confidence
                    )
                    legacy_chapters.append(chapter)
                return legacy_chapters

            return smart_chapters

        else:
            # Fallback to legacy chapter detection
            logger.info("Using legacy chapter detection in hybrid mode")
            return self._process_legacy(cleaned_text, return_modern_format)

    def _create_simple_chunks(self, content: str) -> List[Dict]:
        """Create simple chunks for legacy compatibility."""
        # Simple sentence-based chunking
        sentences = content.split('. ')
        chunks = []

        current_chunk = ""
        chunk_id = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > 4000:  # Chunk size limit
                if current_chunk:
                    chunks.append({
                        'id': f'simple_{chunk_id:03d}',
                        'text': current_chunk.strip(),
                        'method': 'simple',
                        'word_count': len(current_chunk.split())
                    })
                    chunk_id += 1
                current_chunk = sentence
            else:
                current_chunk += sentence + '. '

        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'id': f'simple_{chunk_id:03d}',
                'text': current_chunk.strip(),
                'method': 'simple',
                'word_count': len(current_chunk.split())
            })

        return chunks

    def clean_text_only(self, text: str) -> str:
        """Clean text without chapter segmentation."""
        if self.processor_mode == "modern" and self.modern_processor:
            return self.modern_processor._clean_text_modern(text)
        else:
            return self.legacy_cleaner.clean_text(text)

    def get_stats(self) -> Dict:
        """Get processing statistics from the last operation."""
        stats = {}

        if hasattr(self.legacy_cleaner, 'stats'):
            legacy_stats = self.legacy_cleaner.get_cleaning_stats()
            stats['legacy'] = {
                'original_length': legacy_stats.original_length,
                'cleaned_length': legacy_stats.cleaned_length,
                'patterns_applied': legacy_stats.patterns_applied,
                'compression_ratio': legacy_stats.compression_ratio
            }

        if self.modern_processor:
            modern_stats = self.modern_processor.get_processing_stats()
            stats['modern'] = {
                'original_length': modern_stats.original_length,
                'processed_length': modern_stats.processed_length,
                'chapters_detected': modern_stats.chapters_detected,
                'chunks_created': modern_stats.chunks_created,
                'processing_time': modern_stats.spacy_processing_time,
                'confidence_score': modern_stats.confidence_score
            }

        return stats

    def validate_configuration(self) -> List[str]:
        """Validate the current configuration and return any issues."""
        issues = []

        # Validate legacy patterns
        if hasattr(self.legacy_cleaner, 'validate_patterns'):
            pattern_errors = self.legacy_cleaner.validate_patterns()
            issues.extend([f"Legacy pattern error: {err}" for err in pattern_errors])

        # Validate modern processor
        if self.processor_mode in ["modern", "hybrid"] and not self.modern_processor:
            issues.append("Modern processor required but not available")

        # Test basic functionality
        test_text = "Chapter 1: Test\n\nThis is a test chapter with some content."
        try:
            result = self.process_text(test_text)
            if not result:
                issues.append("Processing returns empty results")
        except Exception as e:
            issues.append(f"Processing test failed: {e}")

        return issues

    def set_processor_mode(self, mode: str) -> bool:
        """
        Change processor mode at runtime.

        Args:
            mode: New processor mode ("legacy", "modern", "hybrid")

        Returns:
            True if mode was successfully changed
        """
        if mode not in ["legacy", "modern", "hybrid"]:
            logger.error(f"Invalid processor mode: {mode}")
            return False

        if mode in ["modern", "hybrid"] and not self.modern_processor:
            logger.error("Cannot switch to modern/hybrid mode: modern processor not available")
            return False

        old_mode = self.processor_mode
        self.processor_mode = mode
        logger.info(f"Switched processor mode from {old_mode} to {mode}")
        return True

    def benchmark_modes(self, text: str, toc_data: Optional[List[Dict]] = None) -> Dict:
        """
        Benchmark different processing modes on the same text.

        Args:
            text: Text to benchmark
            toc_data: Optional TOC data

        Returns:
            Benchmark results
        """
        import time
        results = {}

        original_mode = self.processor_mode

        for mode in ["legacy", "modern", "hybrid"]:
            if mode in ["modern", "hybrid"] and not self.modern_processor:
                continue

            self.processor_mode = mode
            start_time = time.time()

            try:
                chapters = self.process_text(text, toc_data)
                processing_time = time.time() - start_time

                results[mode] = {
                    'processing_time': processing_time,
                    'chapters_detected': len(chapters),
                    'total_word_count': sum(ch.word_count for ch in chapters),
                    'average_confidence': sum(ch.confidence for ch in chapters) / len(chapters) if chapters else 0,
                    'success': True
                }

            except Exception as e:
                results[mode] = {
                    'processing_time': time.time() - start_time,
                    'error': str(e),
                    'success': False
                }

        # Restore original mode
        self.processor_mode = original_mode

        return results