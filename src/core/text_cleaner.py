"""
Advanced text cleaning for TTS optimization.

This module provides comprehensive text cleaning and preprocessing
specifically designed for Text-to-Speech applications.
"""

import logging
import regex as re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import ftfy

from utils.config import load_regex_patterns

logger = logging.getLogger(__name__)


@dataclass
class CleaningStats:
    """Statistics from text cleaning operations."""
    original_length: int
    cleaned_length: int
    patterns_applied: int
    transformations_made: int
    errors_encountered: int

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if self.original_length == 0:
            return 0.0
        return self.cleaned_length / self.original_length

    @property
    def characters_removed(self) -> int:
        """Number of characters removed."""
        return self.original_length - self.cleaned_length


@dataclass
class Chapter:
    """Represents a book chapter with metadata."""
    chapter_num: int
    title: str
    content: str
    word_count: int
    estimated_duration: float  # in minutes
    confidence: float = 1.0  # chapter detection confidence


class TextCleaner:
    """
    Advanced text cleaning for TTS optimization.
    """

    def __init__(self, rules_path: Optional[Path] = None):
        """
        Initialize text cleaner with regex patterns.

        Args:
            rules_path: Path to regex patterns YAML file
        """
        self.rules = load_regex_patterns(rules_path)
        self.compiled_patterns = self._compile_patterns()
        self.stats = CleaningStats(0, 0, 0, 0, 0)

    def clean_text(self, text: str) -> str:
        """
        Apply all cleaning rules in sequence.

        Processing order:
        1. Fix encoding issues (ftfy)
        2. Apply removal patterns
        3. Apply transformation patterns
        4. Handle special TTS cases
        5. Normalize whitespace
        6. Add pause markers

        Args:
            text: Raw text to clean

        Returns:
            Cleaned and TTS-optimized text
        """
        if not text or not text.strip():
            return text

        self.stats = CleaningStats(len(text), 0, 0, 0, 0)
        cleaned_text = text

        try:
            # Step 1: Fix encoding issues
            cleaned_text = ftfy.fix_text(cleaned_text)
            logger.debug("Applied encoding fixes")

            # Step 2: Apply removal patterns
            cleaned_text = self._apply_removal_patterns(cleaned_text)

            # Step 3: Apply transformation patterns
            cleaned_text = self._apply_transformation_patterns(cleaned_text)

            # Step 4: Handle special TTS characters
            cleaned_text = self._apply_tts_replacements(cleaned_text)

            # Step 5: Normalize whitespace
            cleaned_text = self._normalize_whitespace(cleaned_text)

            # Step 6: Add pause markers
            cleaned_text = self.add_pause_markers(cleaned_text)

            self.stats.cleaned_length = len(cleaned_text)

            logger.info(
                f"Text cleaning completed: "
                f"{self.stats.characters_removed} chars removed "
                f"({self.stats.compression_ratio:.2%} retained), "
                f"{self.stats.patterns_applied} patterns applied"
            )

            return cleaned_text

        except Exception as e:
            self.stats.errors_encountered += 1
            logger.error(f"Error during text cleaning: {e}")
            return text  # Return original text on error

    def _compile_patterns(self) -> Dict[str, Any]:
        """
        Compile regex patterns for better performance.

        Returns:
            Dictionary of compiled patterns
        """
        compiled = {}

        try:
            # Compile removal patterns
            if 'cleaning_rules' in self.rules and 'remove' in self.rules['cleaning_rules']:
                compiled['remove'] = []
                for pattern_config in self.rules['cleaning_rules']['remove']:
                    pattern = pattern_config['pattern']
                    flags = re.MULTILINE if pattern_config.get('multiline', False) else 0
                    compiled_pattern = {
                        'regex': re.compile(pattern, flags),
                        'name': pattern_config.get('name', 'unnamed'),
                        'replacement': pattern_config.get('replacement', '')
                    }
                    compiled['remove'].append(compiled_pattern)

            # Compile transformation patterns
            if 'cleaning_rules' in self.rules and 'transform' in self.rules['cleaning_rules']:
                compiled['transform'] = []
                for pattern_config in self.rules['cleaning_rules']['transform']:
                    pattern = pattern_config['pattern']
                    flags = re.MULTILINE if pattern_config.get('multiline', False) else 0
                    compiled_pattern = {
                        'regex': re.compile(pattern, flags),
                        'name': pattern_config.get('name', 'unnamed'),
                        'replacement': pattern_config.get('replacement', '')
                    }
                    compiled['transform'].append(compiled_pattern)

            # Compile chapter detection patterns
            if 'chapter_detection' in self.rules:
                compiled['chapters'] = []
                for pattern in self.rules['chapter_detection']['patterns']:
                    compiled['chapters'].append(re.compile(pattern, re.MULTILINE | re.IGNORECASE))

            logger.info(f"Compiled {len(compiled)} pattern groups")
            return compiled

        except Exception as e:
            logger.error(f"Error compiling patterns: {e}")
            return {}

    def _apply_removal_patterns(self, text: str) -> str:
        """
        Apply removal patterns to text.

        Args:
            text: Text to process

        Returns:
            Text with removal patterns applied
        """
        if 'remove' not in self.compiled_patterns:
            return text

        for pattern_config in self.compiled_patterns['remove']:
            try:
                old_text = text
                text = pattern_config['regex'].sub(pattern_config['replacement'], text)

                if text != old_text:
                    self.stats.patterns_applied += 1
                    logger.debug(f"Applied removal pattern: {pattern_config['name']}")

            except Exception as e:
                self.stats.errors_encountered += 1
                logger.warning(f"Error applying pattern {pattern_config['name']}: {e}")

        return text

    def _apply_transformation_patterns(self, text: str) -> str:
        """
        Apply transformation patterns to text.

        Args:
            text: Text to process

        Returns:
            Text with transformations applied
        """
        if 'transform' not in self.compiled_patterns:
            return text

        for pattern_config in self.compiled_patterns['transform']:
            try:
                old_text = text
                text = pattern_config['regex'].sub(pattern_config['replacement'], text)

                if text != old_text:
                    self.stats.transformations_made += 1
                    self.stats.patterns_applied += 1
                    logger.debug(f"Applied transformation: {pattern_config['name']}")

            except Exception as e:
                self.stats.errors_encountered += 1
                logger.warning(f"Error applying transformation {pattern_config['name']}: {e}")

        return text

    def _apply_tts_replacements(self, text: str) -> str:
        """
        Apply TTS-friendly character replacements.

        Args:
            text: Text to process

        Returns:
            Text with TTS replacements
        """
        if 'cleaning_rules' not in self.rules or 'tts_replacements' not in self.rules['cleaning_rules']:
            return text

        replacements = self.rules['cleaning_rules']['tts_replacements']

        for char, replacement in replacements.items():
            if char in text:
                text = text.replace(char, replacement)
                logger.debug(f"Replaced '{char}' with '{replacement}'")

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text.

        Args:
            text: Text to normalize

        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)

        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove trailing whitespace from lines
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

        # Remove leading whitespace from lines (except intended indentation)
        text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)

        return text.strip()

    def add_pause_markers(self, text: str) -> str:
        """
        Insert natural pause markers for TTS.

        Rules:
        - After chapter titles: [PAUSE: 2.0]
        - After paragraphs: [PAUSE: 0.5]
        - After sentences ending with "?": [PAUSE: 0.3]
        - After sentences ending with "!": [PAUSE: 0.2]
        - After dialogue: [PAUSE: 0.3]

        Args:
            text: Text to process

        Returns:
            Text with pause markers added
        """
        if 'pause_rules' not in self.rules:
            return text

        pause_rules = self.rules['pause_rules']

        # Chapter start pauses
        chapter_pause = pause_rules.get('chapter_start', 2.0)
        text = re.sub(
            r'\[CHAPTER_START: ([^\]]+)\]',
            rf'[CHAPTER_START: \1][PAUSE: {chapter_pause}]',
            text
        )

        # Question pauses
        question_pause = pause_rules.get('question_end', 0.3)
        text = re.sub(
            r'\?(\s+)',
            rf'?[PAUSE: {question_pause}]\1',
            text
        )

        # Exclamation pauses
        exclamation_pause = pause_rules.get('exclamation_end', 0.2)
        text = re.sub(
            r'!(\s+)',
            rf'![PAUSE: {exclamation_pause}]\1',
            text
        )

        # Dialogue pauses
        dialogue_pause = pause_rules.get('dialogue_end', 0.3)
        text = re.sub(
            r'\[DIALOGUE_END\]',
            rf'[DIALOGUE_END][PAUSE: {dialogue_pause}]',
            text
        )

        # Paragraph pauses (double newlines)
        paragraph_pause = pause_rules.get('paragraph_end', 0.5)
        text = re.sub(
            r'\n\n',
            rf'\n[PAUSE: {paragraph_pause}]\n',
            text
        )

        return text

    def segment_chapters(self, text: str) -> List[Chapter]:
        """
        Split text into chapters with metadata.

        Args:
            text: Text to segment

        Returns:
            List of Chapter objects
        """
        chapters = []

        # Look for chapter markers first
        chapter_pattern = re.compile(r'\[CHAPTER_START: ([^\]]+)\]', re.MULTILINE)
        matches = list(chapter_pattern.finditer(text))

        if matches:
            # Process chapters based on markers
            for i, match in enumerate(matches):
                title = match.group(1).strip()
                start_pos = match.end()

                # Find end position (next chapter or end of text)
                if i + 1 < len(matches):
                    end_pos = matches[i + 1].start()
                else:
                    end_pos = len(text)

                content = text[start_pos:end_pos].strip()

                if content:  # Only add non-empty chapters
                    chapter = self._create_chapter(i + 1, title, content)
                    chapters.append(chapter)

        else:
            # Fallback: try pattern-based detection
            chapters = self._detect_chapters_by_patterns(text)

        if not chapters:
            # Ultimate fallback: treat entire text as one chapter
            logger.warning("No chapters detected, treating as single chapter")
            chapter = self._create_chapter(1, "Full Text", text)
            chapters.append(chapter)

        logger.info(f"Segmented text into {len(chapters)} chapters")
        return chapters

    def _detect_chapters_by_patterns(self, text: str) -> List[Chapter]:
        """
        Detect chapters using regex patterns.

        Args:
            text: Text to analyze

        Returns:
            List of detected chapters
        """
        chapters = []

        if 'chapters' not in self.compiled_patterns:
            return chapters

        # Try each chapter detection pattern
        for pattern in self.compiled_patterns['chapters']:
            matches = list(pattern.finditer(text))

            if matches:
                logger.info(f"Found {len(matches)} chapters using pattern detection")

                for i, match in enumerate(matches):
                    title = match.group(0).strip()
                    start_pos = match.end()

                    # Find end position
                    if i + 1 < len(matches):
                        end_pos = matches[i + 1].start()
                    else:
                        end_pos = len(text)

                    content = text[start_pos:end_pos].strip()

                    if content:
                        chapter = self._create_chapter(i + 1, title, content, confidence=0.8)
                        chapters.append(chapter)

                break  # Use first successful pattern

        return chapters

    def _create_chapter(self, num: int, title: str, content: str, confidence: float = 1.0) -> Chapter:
        """
        Create a Chapter object with calculated metadata.

        Args:
            num: Chapter number
            title: Chapter title
            content: Chapter content
            confidence: Detection confidence

        Returns:
            Chapter object with metadata
        """
        word_count = len(content.split())

        # Estimate reading duration (200 words per minute average)
        estimated_duration = word_count / 200.0

        return Chapter(
            chapter_num=num,
            title=title,
            content=content,
            word_count=word_count,
            estimated_duration=estimated_duration,
            confidence=confidence
        )

    def get_cleaning_stats(self) -> CleaningStats:
        """
        Get statistics from the last cleaning operation.

        Returns:
            CleaningStats object
        """
        return self.stats

    def validate_patterns(self) -> List[str]:
        """
        Validate all regex patterns and return any errors.

        Returns:
            List of error messages (empty if all patterns are valid)
        """
        errors = []

        try:
            # Test compile all patterns
            test_patterns = self._compile_patterns()

            # Test apply patterns on sample text
            sample_text = "Chapter 1: Test\n\nThis is a test with \"dialogue\" and [footnote1]."

            for pattern_group in test_patterns.values():
                if isinstance(pattern_group, list):
                    for pattern_config in pattern_group:
                        try:
                            pattern_config['regex'].search(sample_text)
                        except Exception as e:
                            errors.append(f"Pattern {pattern_config['name']}: {e}")

        except Exception as e:
            errors.append(f"General pattern compilation error: {e}")

        return errors