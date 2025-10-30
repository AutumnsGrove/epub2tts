"""
Unit tests for text cleaning module.
"""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path

from src.core.text_cleaner import TextCleaner, Chapter, CleaningStats


class TestTextCleaner:
    """Unit tests for TextCleaner class."""

    def setup_method(self):
        """Setup test fixtures."""
        # Mock rules for testing
        mock_rules = {
            'cleaning_rules': {
                'remove': [
                    {
                        'pattern': r'\[\d+\]',
                        'name': 'footnotes',
                        'replacement': ''
                    }
                ],
                'transform': [
                    {
                        'pattern': r'\*\*(.+?)\*\*',
                        'name': 'bold',
                        'replacement': r'[EMPHASIS_STRONG: \1]'
                    }
                ],
                'tts_replacements': {
                    '&': ' and ',
                    '%': ' percent '
                }
            },
            'pause_rules': {
                'chapter_start': 2.0,
                'paragraph_end': 0.5,
                'question_end': 0.3
            }
        }

        with patch('src.core.text_cleaner.load_regex_patterns', return_value=mock_rules):
            self.cleaner = TextCleaner()

    def test_clean_text_empty_input(self):
        """Test cleaning empty or whitespace-only text."""
        assert self.cleaner.clean_text("") == ""
        assert self.cleaner.clean_text(None) is None

    def test_clean_text_footnote_removal(self):
        """Test footnote removal patterns."""
        text = "This is text with footnote[1] and another[2]."
        cleaned = self.cleaner.clean_text(text)

        assert "[1]" not in cleaned
        assert "[2]" not in cleaned
        assert "This is text with footnote and another." in cleaned

    def test_clean_text_bold_transformation(self):
        """Test bold text transformation."""
        text = "This is **bold text** in a sentence."
        cleaned = self.cleaner.clean_text(text)

        assert "**bold text**" not in cleaned
        assert "[EMPHASIS_STRONG: bold text]" in cleaned

    def test_clean_text_tts_replacements(self):
        """Test TTS character replacements."""
        text = "Sales increased by 15% & revenue grew."
        cleaned = self.cleaner.clean_text(text)

        assert "%" not in cleaned
        assert "&" not in cleaned
        assert " percent " in cleaned
        assert " and " in cleaned

    def test_add_pause_markers_questions(self):
        """Test pause marker insertion after questions."""
        text = "What is this? This is a test."
        result = self.cleaner.add_pause_markers(text)

        assert "[PAUSE: 0.3]" in result

    def test_add_pause_markers_paragraphs(self):
        """Test pause marker insertion between paragraphs."""
        text = "First paragraph.\n\nSecond paragraph."
        result = self.cleaner.add_pause_markers(text)

        assert "[PAUSE: 0.5]" in result

    def test_segment_chapters_with_markers(self):
        """Test chapter segmentation using chapter markers."""
        text = """
        [CHAPTER_START: Introduction]
        This is the introduction chapter.

        [CHAPTER_START: Main Content]
        This is the main content chapter.
        """

        chapters = self.cleaner.segment_chapters(text)

        assert len(chapters) == 2
        assert chapters[0].title == "Introduction"
        assert chapters[1].title == "Main Content"
        assert chapters[0].chapter_num == 1
        assert chapters[1].chapter_num == 2

    def test_segment_chapters_no_markers(self):
        """Test chapter segmentation fallback when no markers found."""
        text = "This is just plain text with no chapter markers."

        chapters = self.cleaner.segment_chapters(text)

        # Should create one chapter for entire text
        assert len(chapters) == 1
        assert chapters[0].title == "Full Text"
        assert chapters[0].chapter_num == 1

    def test_create_chapter(self):
        """Test chapter creation with metadata calculation."""
        content = "This is a test chapter. " * 100  # ~500 words
        chapter = self.cleaner._create_chapter(1, "Test Chapter", content)

        assert chapter.chapter_num == 1
        assert chapter.title == "Test Chapter"
        assert chapter.content == content
        assert chapter.word_count > 0
        assert chapter.estimated_duration > 0
        assert chapter.confidence == 1.0

    def test_cleaning_stats(self):
        """Test cleaning statistics tracking."""
        text = "Original text[1] with **bold** content."
        self.cleaner.clean_text(text)

        stats = self.cleaner.get_cleaning_stats()

        assert isinstance(stats, CleaningStats)
        assert stats.original_length > 0
        assert stats.cleaned_length > 0
        assert stats.patterns_applied > 0

    def test_validate_patterns_success(self):
        """Test pattern validation with valid patterns."""
        errors = self.cleaner.validate_patterns()
        assert len(errors) == 0


class TestChapter:
    """Unit tests for Chapter dataclass."""

    def test_chapter_creation(self):
        """Test Chapter object creation."""
        chapter = Chapter(
            chapter_num=1,
            title="Test Chapter",
            content="Test content",
            word_count=10,
            estimated_duration=5.0,
            confidence=0.9
        )

        assert chapter.chapter_num == 1
        assert chapter.title == "Test Chapter"
        assert chapter.content == "Test content"
        assert chapter.word_count == 10
        assert chapter.estimated_duration == 5.0
        assert chapter.confidence == 0.9


class TestCleaningStats:
    """Unit tests for CleaningStats dataclass."""

    def test_cleaning_stats_properties(self):
        """Test CleaningStats calculated properties."""
        stats = CleaningStats(
            original_length=1000,
            cleaned_length=800,
            patterns_applied=5,
            transformations_made=3,
            errors_encountered=0
        )

        assert stats.compression_ratio == 0.8
        assert stats.characters_removed == 200

    def test_cleaning_stats_zero_length(self):
        """Test CleaningStats with zero original length."""
        stats = CleaningStats(
            original_length=0,
            cleaned_length=0,
            patterns_applied=0,
            transformations_made=0,
            errors_encountered=0
        )

        assert stats.compression_ratio == 0.0
        assert stats.characters_removed == 0


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    # Chapter 1: Introduction

    This is the **introduction** chapter with some footnotes[1].

    What is this book about? It covers various topics & techniques.

    ## Subsection

    More content here with 50% coverage.
    """


class TestIntegrationTextCleaning:
    """Integration tests for text cleaning pipeline."""

    def test_full_cleaning_pipeline(self, sample_text):
        """Test complete cleaning pipeline."""
        # Use real regex patterns for integration test
        cleaner = TextCleaner()
        cleaned = cleaner.clean_text(sample_text)

        # Verify cleaning occurred
        assert len(cleaned) > 0
        assert cleaned != sample_text

        # Check stats were updated
        stats = cleaner.get_cleaning_stats()
        assert stats.original_length > 0
        assert stats.cleaned_length > 0

    def test_chapter_segmentation_integration(self, sample_text):
        """Test chapter segmentation integration."""
        cleaner = TextCleaner()
        chapters = cleaner.segment_chapters(sample_text)

        assert len(chapters) > 0
        for chapter in chapters:
            assert isinstance(chapter, Chapter)
            assert chapter.word_count > 0
            assert chapter.estimated_duration > 0