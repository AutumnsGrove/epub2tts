"""
Unit tests for Pandoc wrapper module.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json

from src.core.pandoc_wrapper import PandocConverter, PandocError


class TestPandocConverter:
    """Unit tests for PandocConverter class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.converter = PandocConverter()

    @patch('subprocess.run')
    def test_verify_pandoc_installation_success(self, mock_run):
        """Test successful Pandoc verification."""
        mock_run.return_value.stdout = "pandoc 2.19.2\nCompiled with pandoc-types 1.22.2.1"

        # Should not raise an exception
        converter = PandocConverter()
        assert converter.pandoc_path == "pandoc"

    @patch('subprocess.run')
    def test_verify_pandoc_installation_not_found(self, mock_run):
        """Test Pandoc not found error."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(PandocError, match="Pandoc not found"):
            PandocConverter()

    @patch('subprocess.run')
    def test_verify_pandoc_installation_error(self, mock_run):
        """Test Pandoc execution error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'pandoc')

        with pytest.raises(PandocError, match="Error running Pandoc"):
            PandocConverter()

    def test_extract_to_markdown_file_not_found(self):
        """Test extract_to_markdown with non-existent file."""
        non_existent_file = Path("/non/existent/file.epub")

        with pytest.raises(PandocError, match="EPUB file not found"):
            self.converter.extract_to_markdown(non_existent_file)

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_extract_to_markdown_success(self, mock_mkdtemp, mock_run):
        """Test successful markdown extraction."""
        # Setup mocks
        mock_mkdtemp.return_value = "/tmp/test_media"
        mock_run.return_value.stdout = "# Chapter 1\n\nTest content"

        # Create a temporary EPUB file
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            markdown, media_dir = self.converter.extract_to_markdown(epub_path)

            assert "# Chapter 1" in markdown
            assert "Test content" in markdown
            assert media_dir == Path("/tmp/test_media")

            # Verify pandoc was called with correct arguments
            mock_run.assert_called_once()
            cmd_args = mock_run.call_args[0][0]
            assert "--from=epub" in cmd_args
            assert "--to=markdown" in cmd_args
            assert str(epub_path) in cmd_args

        finally:
            epub_path.unlink()

    @patch('subprocess.run')
    def test_extract_to_markdown_pandoc_error(self, mock_run):
        """Test pandoc execution error during extraction."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'pandoc', stderr="Invalid EPUB format"
        )

        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            with pytest.raises(PandocError, match="Pandoc conversion failed"):
                self.converter.extract_to_markdown(epub_path)
        finally:
            epub_path.unlink()

    @patch('subprocess.run')
    def test_extract_metadata_success(self, mock_run):
        """Test successful metadata extraction."""
        # Mock JSON response from pandoc
        mock_json = {
            "meta": {
                "title": {"c": "Test Book"},
                "author": {"c": [{"c": "Test Author"}]},
                "date": {"c": "2023"}
            }
        }
        mock_run.return_value.stdout = json.dumps(mock_json)

        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            metadata = self.converter.extract_metadata(epub_path)

            assert metadata['title'] == "Test Book"
            assert 'author' in metadata
            assert metadata['date'] == "2023"

        finally:
            epub_path.unlink()

    @patch('subprocess.run')
    def test_extract_metadata_invalid_json(self, mock_run):
        """Test metadata extraction with invalid JSON."""
        mock_run.return_value.stdout = "invalid json"

        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            with pytest.raises(PandocError, match="Invalid JSON from Pandoc"):
                self.converter.extract_metadata(epub_path)
        finally:
            epub_path.unlink()

    def test_extract_metadata_value_string(self):
        """Test metadata value extraction with string input."""
        result = self.converter._extract_metadata_value("simple string")
        assert result == "simple string"

    def test_extract_metadata_value_dict(self):
        """Test metadata value extraction with dict input."""
        metadata_field = {"c": "extracted value"}
        result = self.converter._extract_metadata_value(metadata_field)
        assert result == "extracted value"

    def test_extract_metadata_value_none(self):
        """Test metadata value extraction with None input."""
        result = self.converter._extract_metadata_value(None)
        assert result is None

    def test_extract_text_from_inlines(self):
        """Test text extraction from Pandoc inline elements."""
        inlines = [
            {"t": "Str", "c": "Hello"},
            {"t": "Space"},
            {"t": "Str", "c": "world"},
            {"t": "Emph", "c": [{"t": "Str", "c": "emphasized"}]}
        ]

        result = self.converter._extract_text_from_inlines(inlines)
        assert result == "Hello world emphasized"

    def test_is_image_file(self):
        """Test image file detection."""
        assert self.converter._is_image_file(Path("test.jpg"))
        assert self.converter._is_image_file(Path("test.PNG"))
        assert self.converter._is_image_file(Path("test.svg"))
        assert not self.converter._is_image_file(Path("test.txt"))
        assert not self.converter._is_image_file(Path("test.pdf"))

    def test_find_image_references(self):
        """Test finding image references in markdown."""
        markdown = "Here is an image: ![Alt text](media/image.jpg) in context."

        result = self.converter._find_image_references(markdown, "image.jpg")

        assert result['alt_text'] == "Alt text"
        assert "image:" in result['context'].lower()

    def test_find_image_references_no_match(self):
        """Test finding image references with no matches."""
        markdown = "No images here"

        result = self.converter._find_image_references(markdown, "nonexistent.jpg")

        assert result['alt_text'] == ""
        assert result['context'] == ""

    @patch('shutil.rmtree')
    def test_cleanup_temp_files(self, mock_rmtree):
        """Test temporary file cleanup."""
        temp_dir = Path("/tmp/test_cleanup")

        # Mock the path to exist
        with patch.object(temp_dir, 'exists', return_value=True):
            self.converter.cleanup_temp_files(temp_dir)
            mock_rmtree.assert_called_once_with(temp_dir)

    @patch('shutil.rmtree')
    def test_cleanup_temp_files_error(self, mock_rmtree):
        """Test temporary file cleanup with error."""
        mock_rmtree.side_effect = OSError("Permission denied")
        temp_dir = Path("/tmp/test_cleanup")

        # Should not raise exception, just log warning
        with patch.object(temp_dir, 'exists', return_value=True):
            self.converter.cleanup_temp_files(temp_dir)


class TestVerifyPandoc:
    """Test the standalone verify_pandoc function."""

    @patch('src.core.pandoc_wrapper.PandocConverter')
    def test_verify_pandoc_success(self, mock_converter):
        """Test successful pandoc verification."""
        from src.core.pandoc_wrapper import verify_pandoc

        # Mock successful initialization
        mock_converter.return_value = Mock()

        result = verify_pandoc()
        assert result is True

    @patch('src.core.pandoc_wrapper.PandocConverter')
    def test_verify_pandoc_failure(self, mock_converter):
        """Test pandoc verification failure."""
        from src.core.pandoc_wrapper import verify_pandoc

        # Mock failed initialization
        mock_converter.side_effect = PandocError("Not found")

        result = verify_pandoc()
        assert result is False