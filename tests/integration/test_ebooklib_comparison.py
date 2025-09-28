#!/usr/bin/env python3
"""
Test script to compare EbookLib and Pandoc EPUB processors.

This script processes the same EPUB file with both processors and
compares their output to validate the EbookLib implementation.
"""

import sys
import logging
from pathlib import Path
import tempfile
import json
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.config import Config
from core.epub_processor import EPUBProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_config(processor_type: str) -> Config:
    """Load configuration for testing with specified processor type."""
    config = Config()

    # Override processor type
    config.processing.epub_processor = processor_type

    # Ensure temp directory exists
    temp_dir = Path(tempfile.gettempdir()) / "epub2tts_test"
    temp_dir.mkdir(exist_ok=True)
    config.processing.temp_dir = str(temp_dir)

    # Disable image processing for simpler comparison
    config.image_description.enabled = False

    return config


def process_with_processor(epub_path: Path, processor_type: str) -> Dict[str, Any]:
    """Process EPUB with specified processor type and return results."""
    logger.info(f"Processing with {processor_type} processor...")

    config = load_test_config(processor_type)
    processor = EPUBProcessor(config)

    # Create output directory
    output_dir = Path(tempfile.mkdtemp(prefix=f"epub2tts_{processor_type}_"))

    try:
        result = processor.process_epub(epub_path, output_dir)

        if result.success:
            return {
                'success': True,
                'processor': processor_type,
                'chapters': len(result.chapters),
                'total_words': sum(ch.word_count for ch in result.chapters),
                'text_length': len(result.text_content),
                'metadata_keys': list(result.metadata.keys()),
                'first_chapter_title': result.chapters[0].title if result.chapters else None,
                'processing_time': result.processing_time,
                'output_dir': str(output_dir)
            }
        else:
            return {
                'success': False,
                'processor': processor_type,
                'error': result.error_message,
                'output_dir': str(output_dir)
            }

    except Exception as e:
        logger.error(f"Error with {processor_type} processor: {e}")
        return {
            'success': False,
            'processor': processor_type,
            'error': str(e),
            'output_dir': str(output_dir)
        }


def compare_results(ebooklib_result: Dict[str, Any], pandoc_result: Dict[str, Any]) -> None:
    """Compare results from both processors."""
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)

    # Success comparison
    print(f"EbookLib Success: {ebooklib_result.get('success', False)}")
    print(f"Pandoc Success:   {pandoc_result.get('success', False)}")

    if not ebooklib_result.get('success') or not pandoc_result.get('success'):
        print("\nOne or both processors failed:")
        if not ebooklib_result.get('success'):
            print(f"  EbookLib Error: {ebooklib_result.get('error')}")
        if not pandoc_result.get('success'):
            print(f"  Pandoc Error: {pandoc_result.get('error')}")
        return

    # Chapter count comparison
    eb_chapters = ebooklib_result.get('chapters', 0)
    pd_chapters = pandoc_result.get('chapters', 0)
    print(f"\nChapter Count:")
    print(f"  EbookLib: {eb_chapters}")
    print(f"  Pandoc:   {pd_chapters}")
    print(f"  Difference: {eb_chapters - pd_chapters}")

    # Word count comparison
    eb_words = ebooklib_result.get('total_words', 0)
    pd_words = pandoc_result.get('total_words', 0)
    print(f"\nTotal Words:")
    print(f"  EbookLib: {eb_words:,}")
    print(f"  Pandoc:   {pd_words:,}")
    print(f"  Difference: {eb_words - pd_words:,}")
    if pd_words > 0:
        print(f"  Percentage: {((eb_words - pd_words) / pd_words * 100):+.1f}%")

    # Text length comparison
    eb_length = ebooklib_result.get('text_length', 0)
    pd_length = pandoc_result.get('text_length', 0)
    print(f"\nText Length:")
    print(f"  EbookLib: {eb_length:,}")
    print(f"  Pandoc:   {pd_length:,}")
    print(f"  Difference: {eb_length - pd_length:,}")
    if pd_length > 0:
        print(f"  Percentage: {((eb_length - pd_length) / pd_length * 100):+.1f}%")

    # Processing time comparison
    eb_time = ebooklib_result.get('processing_time', 0)
    pd_time = pandoc_result.get('processing_time', 0)
    print(f"\nProcessing Time:")
    print(f"  EbookLib: {eb_time:.2f}s")
    print(f"  Pandoc:   {pd_time:.2f}s")
    print(f"  Speedup:  {pd_time / eb_time:.1f}x" if eb_time > 0 else "  Speedup: N/A")

    # Metadata comparison
    eb_meta = set(ebooklib_result.get('metadata_keys', []))
    pd_meta = set(pandoc_result.get('metadata_keys', []))
    print(f"\nMetadata Fields:")
    print(f"  EbookLib: {len(eb_meta)} fields")
    print(f"  Pandoc:   {len(pd_meta)} fields")
    print(f"  Common:   {len(eb_meta & pd_meta)} fields")
    print(f"  EbookLib only: {eb_meta - pd_meta}")
    print(f"  Pandoc only:   {pd_meta - eb_meta}")

    # First chapter comparison
    eb_first = ebooklib_result.get('first_chapter_title')
    pd_first = pandoc_result.get('first_chapter_title')
    print(f"\nFirst Chapter Title:")
    print(f"  EbookLib: '{eb_first}'")
    print(f"  Pandoc:   '{pd_first}'")
    print(f"  Match:    {eb_first == pd_first}")


def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python test_ebooklib_comparison.py <epub_file>")
        sys.exit(1)

    epub_path = Path(sys.argv[1])
    if not epub_path.exists():
        print(f"Error: EPUB file not found: {epub_path}")
        sys.exit(1)

    print(f"Testing EPUB processors with: {epub_path.name}")
    print(f"File size: {epub_path.stat().st_size / (1024*1024):.1f} MB")

    # Test EbookLib processor
    ebooklib_result = process_with_processor(epub_path, "ebooklib")

    # Test Pandoc processor
    pandoc_result = process_with_processor(epub_path, "pandoc")

    # Compare results
    compare_results(ebooklib_result, pandoc_result)

    # Save detailed results
    results_file = Path("comparison_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            'epub_file': str(epub_path),
            'ebooklib_result': ebooklib_result,
            'pandoc_result': pandoc_result
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")
    print(f"EbookLib output: {ebooklib_result.get('output_dir')}")
    print(f"Pandoc output:   {pandoc_result.get('output_dir')}")


if __name__ == "__main__":
    main()