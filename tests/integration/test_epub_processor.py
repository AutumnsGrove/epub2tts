"""
Integration tests for EPUB processor.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from src.core.epub_processor import EPUBProcessor, ProcessingResult
from src.core.text_cleaner import Chapter, CleaningStats
from src.utils.config import Config


class TestEPUBProcessor:
    """Integration tests for EPUBProcessor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.processor = EPUBProcessor(self.config)

    def test_processor_initialization(self):
        """Test EPUBProcessor initialization."""
        assert self.processor.config == self.config
        assert self.processor.cleaner is not None
        assert self.processor.temp_dir.exists()

    def test_process_epub_file_not_found(self):
        """Test processing non-existent EPUB file."""
        non_existent_path = Path("/non/existent/file.epub")

        result = self.processor.process_epub(non_existent_path)

        assert result.success is False
        assert "not found" in result.error_message
        assert result.text_content == ""
        assert len(result.chapters) == 0

    @patch('src.core.epub_processor.parse_document')
    def test_process_epub_success(self, mock_parse):
        """Test successful EPUB processing."""
        # Create mock OmniParser Document
        mock_doc = Mock()
        mock_doc.content = "Chapter 1 content here"

        # Mock metadata
        mock_metadata = Mock()
        mock_metadata.title = "Test Book"
        mock_metadata.author = "Test Author"
        mock_metadata.authors = ["Test Author"]
        mock_metadata.publisher = None
        mock_metadata.publication_date = None
        mock_metadata.language = "en"
        mock_metadata.isbn = None
        mock_metadata.description = None
        mock_metadata.tags = []
        mock_metadata.file_size = 1024
        mock_doc.metadata = mock_metadata

        # Mock chapters - Make word_count high enough to pass min_words_per_chapter filter
        mock_chapter = Mock()
        mock_chapter.title = "Chapter 1"
        mock_chapter.content = "word " * 150  # 150 words (well above default minimum)
        mock_chapter.word_count = 150
        mock_doc.chapters = [mock_chapter]

        # Mock images
        mock_image = Mock()
        mock_image.file_path = "image.jpg"
        mock_image.alt_text = ""
        mock_image.position = 0
        mock_image.format = "jpg"
        mock_doc.images = [mock_image]

        mock_parse.return_value = mock_doc

        # Create temporary EPUB file
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            result = self.processor.process_epub(epub_path)

            assert result.success is True
            assert result.text_content != ""  # Content will be cleaned
            assert len(result.chapters) == 1
            assert result.chapters[0].title == "Chapter 1"
            assert result.metadata["title"] == "Test Book"
            assert len(result.image_info) == 1
            assert result.error_message is None

        finally:
            epub_path.unlink()

    @patch('src.core.epub_processor.parse_document')
    def test_process_epub_parsing_error(self, mock_parse):
        """Test EPUB processing with OmniParser error."""
        # Simulate parsing error
        mock_parse.side_effect = Exception("OmniParser parsing failed")

        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            result = self.processor.process_epub(epub_path)

            assert result.success is False
            assert "OmniParser parsing failed" in result.error_message
            assert result.processing_time > 0

        finally:
            epub_path.unlink()

    def test_post_process_chapters_filter_short(self):
        """Test filtering out short chapters."""
        # Set minimum words requirement
        self.processor.config.chapters.min_words_per_chapter = 100

        chapters = [
            Chapter(1, "Short", "word " * 10, 10, 0.5),  # Too short
            Chapter(2, "Long", "word " * 150, 150, 7.5)  # Long enough
        ]

        processed = self.processor._post_process_chapters(chapters)

        assert len(processed) == 1
        assert processed[0].title == "Long"

    def test_post_process_chapters_split_long(self):
        """Test splitting very long chapters."""
        # Set maximum words per chunk
        self.processor.config.chapters.max_words_per_chunk = 100

        long_content = "word " * 150  # 150 words
        chapters = [
            Chapter(1, "Long Chapter", long_content, 150, 7.5)
        ]

        processed = self.processor._post_process_chapters(chapters)

        # Should be split into 2 chunks
        assert len(processed) == 2
        assert "Part 1" in processed[0].title
        assert "Part 2" in processed[1].title

    def test_split_long_chapter(self):
        """Test splitting a single long chapter."""
        self.processor.config.chapters.max_words_per_chunk = 50

        long_content = "word " * 100  # 100 words
        chapter = Chapter(1, "Long Chapter", long_content, 100, 5.0)

        chunks = self.processor._split_long_chapter(chapter, 1)

        assert len(chunks) == 2
        assert chunks[0].word_count <= 50
        assert chunks[1].word_count <= 50
        assert chunks[0].title == "Long Chapter - Part 1"
        assert chunks[1].title == "Long Chapter - Part 2"
        assert chunks[0].chapter_num == 1
        assert chunks[1].chapter_num == 2

    def test_save_results_plain_text(self):
        """Test saving results in plain text format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            epub_path = Path("test.epub")

            self.processor.config.output.text_format = "plain"
            self.processor.config.output.save_intermediate = True
            self.processor.config.output.create_metadata = True
            self.processor.config.output.generate_toc = True

            chapters = [Chapter(1, "Chapter 1", "Content 1", 50, 2.5)]
            metadata = {"title": "Test Book"}
            image_info = []

            self.processor._save_results(
                epub_path, output_dir, "Full text content",
                chapters, metadata, image_info
            )

            # Check files were created
            assert (output_dir / "test.txt").exists()
            assert (output_dir / "test_chapters").exists()
            assert (output_dir / "test_metadata.json").exists()
            assert (output_dir / "test_toc.txt").exists()

    def test_save_results_json_format(self):
        """Test saving results in JSON format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            epub_path = Path("test.epub")

            self.processor.config.output.text_format = "json"

            chapters = [Chapter(1, "Chapter 1", "Content 1", 50, 2.5)]
            metadata = {"title": "Test Book"}
            image_info = []

            self.processor._save_results(
                epub_path, output_dir, "Full text content",
                chapters, metadata, image_info
            )

            # Check JSON file was created and contains expected data
            json_file = output_dir / "test.json"
            assert json_file.exists()

            with open(json_file) as f:
                data = json.load(f)

            assert data["metadata"]["title"] == "Test Book"
            assert data["text"] == "Full text content"
            assert len(data["chapters"]) == 1

    @patch('src.core.epub_processor.parse_document')
    def test_validate_epub_success(self, mock_parse):
        """Test EPUB validation with valid file."""
        # Create mock valid document
        mock_doc = Mock()
        mock_metadata = Mock()
        mock_metadata.title = "Valid"
        mock_doc.metadata = mock_metadata
        mock_doc.content = "Valid content"
        mock_parse.return_value = mock_doc

        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)
            # Write enough content to pass the size check (>= 1KB)
            tmp_file.write(b"dummy epub content" * 100)

        try:
            issues = self.processor.validate_epub(epub_path)
            assert len(issues) == 0

        finally:
            epub_path.unlink()

    def test_validate_epub_file_not_found(self):
        """Test EPUB validation with non-existent file."""
        non_existent = Path("/non/existent/file.epub")
        issues = self.processor.validate_epub(non_existent)

        assert len(issues) > 0
        assert any("does not exist" in issue for issue in issues)

    def test_validate_epub_wrong_extension(self):
        """Test EPUB validation with wrong file extension."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            wrong_ext_path = Path(tmp_file.name)

        try:
            issues = self.processor.validate_epub(wrong_ext_path)
            assert any("does not have .epub extension" in issue for issue in issues)

        finally:
            wrong_ext_path.unlink()

    def test_validate_epub_empty_file(self):
        """Test EPUB validation with empty file."""
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            empty_path = Path(tmp_file.name)

        try:
            issues = self.processor.validate_epub(empty_path)
            assert any("empty" in issue for issue in issues)

        finally:
            empty_path.unlink()

    @patch('src.core.epub_processor.parse_document')
    def test_get_processing_info(self, mock_parse):
        """Test getting processing info without full processing."""
        # Create mock document
        mock_doc = Mock()
        mock_doc.content = "Content " * 100

        # Mock metadata
        mock_metadata = Mock()
        mock_metadata.title = "Test Book"
        mock_metadata.author = "Test Author"
        mock_metadata.authors = ["Test Author"]
        mock_metadata.publisher = None
        mock_metadata.publication_date = None
        mock_metadata.language = "en"
        mock_metadata.isbn = None
        mock_metadata.description = None
        mock_metadata.tags = []
        mock_metadata.file_size = 1024
        mock_metadata.word_count = 100
        mock_doc.metadata = mock_metadata

        mock_doc.chapters = []
        mock_doc.images = []

        mock_parse.return_value = mock_doc

        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)
            tmp_file.write(b"dummy content")

        try:
            info = self.processor.get_processing_info(epub_path)

            assert 'file_size' in info
            assert 'metadata' in info
            assert 'estimated_text_length' in info
            assert 'estimated_word_count' in info
            assert info['metadata']['title'] == "Test Book"

        finally:
            epub_path.unlink()


class TestProcessingResult:
    """Test ProcessingResult dataclass."""

    def test_processing_result_creation(self):
        """Test ProcessingResult creation."""
        chapters = [Chapter(1, "Test", "Content", 10, 1.0)]
        stats = CleaningStats(100, 90, 5, 3, 0)

        result = ProcessingResult(
            success=True,
            text_content="Test content",
            chapters=chapters,
            metadata={"title": "Test"},
            image_info=[],
            cleaning_stats=stats
        )

        assert result.success is True
        assert result.text_content == "Test content"
        assert len(result.chapters) == 1
        assert result.metadata["title"] == "Test"

    def test_processing_result_to_dict(self):
        """Test ProcessingResult serialization to dict."""
        chapters = [Chapter(1, "Test", "Content", 10, 1.0)]
        stats = CleaningStats(100, 90, 5, 3, 0)

        result = ProcessingResult(
            success=True,
            text_content="Test content",
            chapters=chapters,
            metadata={"title": "Test"},
            image_info=[],
            cleaning_stats=stats
        )

        result_dict = result.to_dict()

        assert result_dict['success'] is True
        assert result_dict['text_content'] == "Test content"
        assert len(result_dict['chapters']) == 1
        assert isinstance(result_dict['chapters'][0], dict)
        assert isinstance(result_dict['cleaning_stats'], dict)

    def test_processing_result_save_to_json(self):
        """Test ProcessingResult JSON serialization."""
        chapters = [Chapter(1, "Test", "Content", 10, 1.0)]
        stats = CleaningStats(100, 90, 5, 3, 0)

        result = ProcessingResult(
            success=True,
            text_content="Test content",
            chapters=chapters,
            metadata={"title": "Test"},
            image_info=[],
            cleaning_stats=stats
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json_path = Path(tmp_file.name)

        try:
            result.save_to_json(json_path)

            # Verify file was created and contains valid JSON
            assert json_path.exists()

            with open(json_path) as f:
                data = json.load(f)

            assert data['success'] is True
            assert data['metadata']['title'] == "Test"

        finally:
            json_path.unlink()