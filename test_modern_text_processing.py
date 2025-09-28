#!/usr/bin/env python3
"""
Test script for modern text processing capabilities.

This script tests the new spaCy, clean-text, and LangChain integration
against the legacy regex-based approach.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from text import EnhancedTextCleaner
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_modern_text_processing():
    """Test modern text processing capabilities."""

    # Sample text with various chapter patterns
    test_text = """
    This is a sample book with multiple chapters.

    Chapter 1: The Beginning

    This is the content of the first chapter. It contains some dialogue.
    "Hello, world!" said the protagonist. The story unfolds with various
    characters and plot elements. We'll see how the modern processor
    handles this content.

    There are some special characters: $100, 50%, and email@example.com.
    Also some smart quotes "like this" and an em dash — right here.


    CHAPTER TWO: MIDDLE GROUND

    The second chapter begins here with a different formatting style.
    This chapter discusses advanced topics and includes technical terms.
    The artificial intelligence system processed 1,000+ documents efficiently.

    Some named entities appear: Apple Inc., New York, and John Smith.
    The text continues with more content for processing...


    3. Final Chapter

    This is the last chapter with yet another formatting pattern.
    It includes a conclusion and wraps up the story nicely.
    The end!
    """

    print("=== Modern Text Processing Test ===\n")

    # Test different processor modes
    modes = ["legacy", "modern", "hybrid"]

    for mode in modes:
        if mode == "modern":
            try:
                # Test if spaCy model is available
                import spacy
                spacy.load("en_core_web_sm")
            except (ImportError, OSError) as e:
                print(f"Skipping {mode} mode: {e}")
                continue

        print(f"--- Testing {mode.upper()} mode ---")

        try:
            # Initialize enhanced cleaner
            cleaner = EnhancedTextCleaner(processor_mode=mode)

            # Process text
            start_time = time.time()
            chapters = cleaner.process_text(test_text)
            processing_time = time.time() - start_time

            print(f"Processing time: {processing_time:.3f}s")
            print(f"Chapters detected: {len(chapters)}")

            for i, chapter in enumerate(chapters):
                print(f"  Chapter {chapter.chapter_num}: '{chapter.title}'")
                print(f"    Word count: {chapter.word_count}")
                print(f"    Confidence: {chapter.confidence:.2f}")

                # Show modern features if available
                if hasattr(chapter, 'topics') and chapter.topics:
                    print(f"    Topics: {chapter.topics[:3]}")
                if hasattr(chapter, 'named_entities') and chapter.named_entities:
                    entities = [f"{ent[0]}({ent[1]})" for ent in chapter.named_entities[:3]]
                    print(f"    Entities: {entities}")
                if hasattr(chapter, 'chunks') and chapter.chunks:
                    print(f"    Chunks: {len(chapter.chunks)}")

                print(f"    Content preview: '{chapter.content[:100]}...'")
                print()

            # Get stats
            stats = cleaner.get_stats()
            if stats:
                print(f"Statistics: {stats}")

            print()

        except Exception as e:
            print(f"Error in {mode} mode: {e}")
            print()


def test_text_cleaning_comparison():
    """Compare text cleaning between legacy and modern approaches."""

    dirty_text = """
    Chapter  1:   The    Beginning

    This is text with    excessive   spaces and "smart quotes".
    There are URLs like https://example.com and emails like test@example.com.

    Special characters: $100, 50%, John & Jane, etc.

    [Footnote markers like this should be removed]

    More text with... ellipsis and — em dashes.
    """

    print("=== Text Cleaning Comparison ===\n")

    try:
        # Legacy cleaning
        legacy_cleaner = EnhancedTextCleaner(processor_mode="legacy")
        legacy_cleaned = legacy_cleaner.clean_text_only(dirty_text)

        print("--- Legacy Cleaned Text ---")
        print(legacy_cleaned)
        print()

        # Modern cleaning
        try:
            modern_cleaner = EnhancedTextCleaner(processor_mode="modern")
            modern_cleaned = modern_cleaner.clean_text_only(dirty_text)

            print("--- Modern Cleaned Text ---")
            print(modern_cleaned)
            print()

            # Compare lengths
            print(f"Original length: {len(dirty_text)}")
            print(f"Legacy cleaned length: {len(legacy_cleaned)}")
            print(f"Modern cleaned length: {len(modern_cleaned)}")

        except Exception as e:
            print(f"Modern cleaning failed: {e}")

    except Exception as e:
        print(f"Text cleaning test failed: {e}")


def test_benchmark():
    """Benchmark different processing modes."""

    print("=== Performance Benchmark ===\n")

    # Larger test text for meaningful benchmarks
    large_text = """
    Chapter 1: Introduction to Machine Learning

    Machine learning is a subset of artificial intelligence (AI) that provides
    systems the ability to automatically learn and improve from experience without
    being explicitly programmed. This chapter introduces the fundamental concepts.

    """ * 10  # Repeat for larger content

    try:
        cleaner = EnhancedTextCleaner()

        # Validation test
        issues = cleaner.validate_configuration()
        if issues:
            print("Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
            print()

        # Benchmark different modes
        results = cleaner.benchmark_modes(large_text)

        print("Benchmark Results:")
        for mode, result in results.items():
            if result['success']:
                print(f"  {mode.upper()}:")
                print(f"    Processing time: {result['processing_time']:.3f}s")
                print(f"    Chapters detected: {result['chapters_detected']}")
                print(f"    Total words: {result['total_word_count']}")
                print(f"    Average confidence: {result['average_confidence']:.2f}")
            else:
                print(f"  {mode.upper()}: FAILED - {result.get('error', 'Unknown error')}")
            print()

    except Exception as e:
        print(f"Benchmark failed: {e}")


if __name__ == "__main__":
    print("Testing modern text processing implementation...\n")

    test_modern_text_processing()
    test_text_cleaning_comparison()
    test_benchmark()

    print("Test completed!")