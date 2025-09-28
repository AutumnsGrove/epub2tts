"""
Pandoc wrapper for EPUB processing.

This module provides a clean interface to Pandoc operations specifically
optimized for EPUB to text conversion with image extraction.
"""

import logging
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import shutil
import re

logger = logging.getLogger(__name__)


class PandocError(Exception):
    """Exception raised for Pandoc-related errors."""
    pass


class PandocConverter:
    """
    Wrapper for Pandoc operations with EPUB-specific optimizations.
    """

    def __init__(self, pandoc_path: str = "pandoc"):
        """
        Initialize Pandoc converter.

        Args:
            pandoc_path: Path to pandoc executable

        Raises:
            PandocError: If pandoc is not found or version is incompatible
        """
        self.pandoc_path = pandoc_path

        # Try system pandoc first, then pypandoc if available
        if not self._check_pandoc_exists():
            try:
                import pypandoc
                pypandoc_path = pypandoc.get_pandoc_path()
                if pypandoc_path and Path(pypandoc_path).exists():
                    self.pandoc_path = pypandoc_path
                    logger.info(f"Using pypandoc's pandoc at: {pypandoc_path}")
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Could not get pypandoc path: {e}")

        self.verify_pandoc_installation()

    def _check_pandoc_exists(self) -> bool:
        """Check if pandoc exists at the given path."""
        try:
            subprocess.run(
                [self.pandoc_path, "--version"],
                capture_output=True,
                check=False,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def verify_pandoc_installation(self) -> None:
        """
        Verify Pandoc is installed and get version info.

        Raises:
            PandocError: If pandoc is not found or version is incompatible
        """
        try:
            result = subprocess.run(
                [self.pandoc_path, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version_info = result.stdout.strip()
            logger.info(f"Found Pandoc: {version_info.splitlines()[0]}")

            # Extract version number
            version_match = re.search(r'pandoc (\d+)\.(\d+)', version_info)
            if version_match:
                major, minor = map(int, version_match.groups())
                if major < 2:
                    logger.warning(f"Pandoc version {major}.{minor} may not support all features")
            else:
                logger.warning("Could not parse Pandoc version")

        except FileNotFoundError:
            raise PandocError(f"Pandoc not found at '{self.pandoc_path}'. Please install Pandoc.")
        except subprocess.CalledProcessError as e:
            raise PandocError(f"Error running Pandoc: {e}")

    def extract_to_markdown(self, epub_path: Path, extract_images: bool = True) -> Tuple[str, Path]:
        """
        Convert EPUB to Markdown with all content preserved.

        Args:
            epub_path: Path to EPUB file
            extract_images: Whether to extract images

        Returns:
            Tuple of (markdown_content, temp_media_dir)

        Raises:
            PandocError: If conversion fails
        """
        if not epub_path.exists():
            raise PandocError(f"EPUB file not found: {epub_path}")

        # Create temporary directory for media extraction
        temp_media_dir = Path(tempfile.mkdtemp(prefix="epub2tts_media_"))

        try:
            # Build pandoc command
            cmd = [
                self.pandoc_path,
                "--from=epub",
                "--to=markdown",
                "--standalone",
                "--wrap=none",
                "--markdown-headings=atx",
                str(epub_path)
            ]

            if extract_images:
                cmd.extend(["--extract-media", str(temp_media_dir)])

            logger.info(f"Converting EPUB to Markdown: {epub_path}")
            logger.debug(f"Pandoc command: {' '.join(cmd)}")

            # Run pandoc
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            markdown_content = result.stdout

            if not markdown_content.strip():
                raise PandocError("Pandoc returned empty content")

            logger.info(f"Successfully converted EPUB ({len(markdown_content)} characters)")

            if extract_images:
                image_count = len(list(temp_media_dir.rglob("*")))
                logger.info(f"Extracted {image_count} media files to {temp_media_dir}")

            return markdown_content, temp_media_dir

        except subprocess.CalledProcessError as e:
            logger.error(f"Pandoc conversion failed: {e}")
            logger.error(f"Pandoc stderr: {e.stderr}")
            raise PandocError(f"Pandoc conversion failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error during conversion: {e}")
            raise PandocError(f"Conversion error: {e}")

    def extract_metadata(self, epub_path: Path) -> Dict[str, Any]:
        """
        Extract book metadata using Pandoc's JSON output.

        Args:
            epub_path: Path to EPUB file

        Returns:
            Dictionary containing metadata

        Raises:
            PandocError: If metadata extraction fails
        """
        if not epub_path.exists():
            raise PandocError(f"EPUB file not found: {epub_path}")

        try:
            cmd = [
                self.pandoc_path,
                "--from=epub",
                "--to=json",
                str(epub_path)
            ]

            logger.debug(f"Extracting metadata with command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            json_data = json.loads(result.stdout)
            metadata = json_data.get('meta', {})

            # Extract common metadata fields
            extracted_metadata = {
                'title': self._extract_metadata_value(metadata.get('title')),
                'author': self._extract_metadata_value(metadata.get('author')),
                'creator': self._extract_metadata_value(metadata.get('creator')),
                'publisher': self._extract_metadata_value(metadata.get('publisher')),
                'date': self._extract_metadata_value(metadata.get('date')),
                'language': self._extract_metadata_value(metadata.get('language')),
                'subject': self._extract_metadata_value(metadata.get('subject')),
                'description': self._extract_metadata_value(metadata.get('description')),
                'identifier': self._extract_metadata_value(metadata.get('identifier')),
                'rights': self._extract_metadata_value(metadata.get('rights')),
            }

            # Remove None values
            extracted_metadata = {k: v for k, v in extracted_metadata.items() if v is not None}

            logger.info(f"Extracted metadata: {list(extracted_metadata.keys())}")
            return extracted_metadata

        except subprocess.CalledProcessError as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise PandocError(f"Metadata extraction failed: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON metadata: {e}")
            raise PandocError(f"Invalid JSON from Pandoc: {e}")

    def extract_images_info(self, epub_path: Path) -> List[Dict[str, Any]]:
        """
        Extract information about images in the EPUB.

        Args:
            epub_path: Path to EPUB file

        Returns:
            List of dictionaries with image information

        Raises:
            PandocError: If image extraction fails
        """
        markdown_content, temp_media_dir = self.extract_to_markdown(epub_path, extract_images=True)

        try:
            images = []

            # Find all image files in extracted media
            for image_file in temp_media_dir.rglob("*"):
                if image_file.is_file() and self._is_image_file(image_file):
                    # Find references to this image in markdown
                    relative_path = image_file.relative_to(temp_media_dir)
                    image_refs = self._find_image_references(markdown_content, str(relative_path))

                    image_info = {
                        'file_path': str(image_file),
                        'relative_path': str(relative_path),
                        'alt_text': image_refs.get('alt_text', ''),
                        'context': image_refs.get('context', ''),
                        'file_size': image_file.stat().st_size,
                        'format': image_file.suffix.lower()
                    }
                    images.append(image_info)

            logger.info(f"Found {len(images)} images in EPUB")
            return images

        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_media_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_media_dir}: {e}")

    def _extract_metadata_value(self, metadata_field: Any) -> Optional[str]:
        """
        Extract string value from Pandoc metadata field.

        Args:
            metadata_field: Pandoc metadata field value

        Returns:
            Extracted string value or None
        """
        if metadata_field is None:
            return None

        if isinstance(metadata_field, str):
            return metadata_field

        if isinstance(metadata_field, dict):
            # Handle Pandoc's structured metadata
            if 'c' in metadata_field:
                if isinstance(metadata_field['c'], str):
                    return metadata_field['c']
                elif isinstance(metadata_field['c'], list):
                    # Extract text from inline elements
                    return self._extract_text_from_inlines(metadata_field['c'])

        if isinstance(metadata_field, list):
            if len(metadata_field) > 0:
                return self._extract_metadata_value(metadata_field[0])

        return str(metadata_field) if metadata_field else None

    def _extract_text_from_inlines(self, inlines: List[Any]) -> str:
        """
        Extract plain text from Pandoc inline elements.

        Args:
            inlines: List of Pandoc inline elements

        Returns:
            Concatenated text content
        """
        text_parts = []

        for inline in inlines:
            if isinstance(inline, dict):
                if inline.get('t') == 'Str':
                    text_parts.append(inline.get('c', ''))
                elif inline.get('t') == 'Space':
                    text_parts.append(' ')
                elif inline.get('t') in ['Emph', 'Strong']:
                    # Recursively extract from emphasized text
                    nested_text = self._extract_text_from_inlines(inline.get('c', []))
                    text_parts.append(nested_text)
            elif isinstance(inline, str):
                text_parts.append(inline)

        return ''.join(text_parts)

    def _is_image_file(self, file_path: Path) -> bool:
        """
        Check if file is an image based on extension.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to be an image
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
        return file_path.suffix.lower() in image_extensions

    def _find_image_references(self, markdown_content: str, image_path: str) -> Dict[str, str]:
        """
        Find references to an image in markdown content.

        Args:
            markdown_content: Markdown text to search
            image_path: Relative path to image

        Returns:
            Dictionary with alt_text and context
        """
        # Escape special regex characters in path
        escaped_path = re.escape(image_path)

        # Look for markdown image syntax
        pattern = rf'!\[([^\]]*)\]\([^)]*{escaped_path}[^)]*\)'
        matches = re.finditer(pattern, markdown_content, re.IGNORECASE)

        alt_text = ''
        context = ''

        for match in matches:
            alt_text = match.group(1)

            # Extract surrounding context (50 characters before and after)
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(markdown_content), match.end() + 50)
            context = markdown_content[start_pos:end_pos].replace('\n', ' ')
            break  # Use first match

        return {
            'alt_text': alt_text,
            'context': context.strip()
        }

    def cleanup_temp_files(self, temp_dir: Path) -> None:
        """
        Clean up temporary files and directories.

        Args:
            temp_dir: Temporary directory to remove
        """
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up {temp_dir}: {e}")


def verify_pandoc() -> bool:
    """
    Quick verification that Pandoc is available.

    Returns:
        True if Pandoc is available, False otherwise
    """
    try:
        converter = PandocConverter()
        return True
    except PandocError:
        return False