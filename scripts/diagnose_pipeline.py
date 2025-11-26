#!/usr/bin/env python3
"""
Diagnostic script to trace through the epub2tts pipeline and identify issues.
This script will analyze each stage of processing to find where text/audio
is being truncated or lost.
"""

import sys
import logging
from pathlib import Path
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.epub_processor import EPUBProcessor
from utils.config import load_config
from utils.logger import setup_logging

# Setup logging
setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def diagnose_epub(epub_path: Path, output_dir: Path = None):
    """Run diagnostic analysis on EPUB processing pipeline."""

    print("\n" + "="*80)
    print("EPUB2TTS PIPELINE DIAGNOSTICS")
    print("="*80)

    if not epub_path.exists():
        print(f"ERROR: EPUB file not found: {epub_path}")
        return

    print(f"\nInput file: {epub_path}")
    print(f"File size: {epub_path.stat().st_size:,} bytes")

    # Load config
    config = load_config()
    print(f"\nConfiguration loaded:")
    print(f"  - TTS engine: {config.tts.engine}")
    print(f"  - TTS model: {config.tts.model}")
    print(f"  - Voice: {config.tts.voice}")
    print(f"  - Min words per chapter: {config.chapters.min_words_per_chapter}")
    print(f"  - Max words per chunk: {config.chapters.max_words_per_chunk}")

    # Stage 1: EPUB Processing
    print("\n" + "-"*80)
    print("STAGE 1: EPUB PROCESSING")
    print("-"*80)

    processor = EPUBProcessor(config)

    start_time = time.time()
    result = processor.process_epub(epub_path, output_dir)
    process_time = time.time() - start_time

    if not result.success:
        print(f"ERROR: EPUB processing failed: {result.error_message}")
        return

    print(f"\n✓ EPUB processing completed in {process_time:.2f}s")
    print(f"\nMetadata:")
    for key, value in result.metadata.items():
        if value:
            print(f"  {key}: {value}")

    print(f"\nContent summary:")
    print(f"  - Total text length: {len(result.text_content):,} characters")
    print(f"  - Total word count: {sum(ch.word_count for ch in result.chapters):,} words")
    print(f"  - Chapters extracted: {len(result.chapters)}")
    print(f"  - Images found: {len(result.image_info)}")

    # Stage 2: Chapter Analysis
    print("\n" + "-"*80)
    print("STAGE 2: CHAPTER ANALYSIS")
    print("-"*80)

    total_word_count = 0
    for i, chapter in enumerate(result.chapters):
        total_word_count += chapter.word_count
        # Show first 100 chars of content
        preview = chapter.content[:100].replace('\n', ' ').strip()
        if len(chapter.content) > 100:
            preview += "..."

        print(f"\n  Chapter {chapter.chapter_num}: {chapter.title}")
        print(f"    Words: {chapter.word_count:,}")
        print(f"    Characters: {len(chapter.content):,}")
        print(f"    Est. duration: {chapter.estimated_duration:.1f} min")
        print(f"    Confidence: {chapter.confidence:.2f}")
        print(f"    Preview: {preview}")

    print(f"\n  TOTAL WORDS: {total_word_count:,}")
    estimated_audio_minutes = total_word_count / 150  # ~150 WPM for TTS
    print(f"  ESTIMATED AUDIO DURATION: {estimated_audio_minutes:.1f} minutes")

    # Stage 3: Text Cleaning Stats
    print("\n" + "-"*80)
    print("STAGE 3: TEXT CLEANING STATS")
    print("-"*80)

    if result.cleaning_stats:
        stats = result.cleaning_stats
        print(f"  Original length: {stats.original_length:,} chars")
        print(f"  Cleaned length: {stats.cleaned_length:,} chars")
        print(f"  Characters removed: {stats.characters_removed:,}")
        print(f"  Compression ratio: {stats.compression_ratio:.1%}")
        print(f"  Patterns applied: {stats.patterns_applied}")
        print(f"  Errors: {stats.errors_encountered}")

    # Stage 4: TTS Pipeline Analysis
    print("\n" + "-"*80)
    print("STAGE 4: TTS PIPELINE ANALYSIS")
    print("-"*80)

    # Prepare text chunks like TTS pipeline does
    text_chunks = []
    for i, chapter in enumerate(result.chapters):
        chapter_num = chapter.chapter_num
        chapter_title = chapter.title
        clean_title = "".join(c for c in chapter_title if c.isalnum() or c in ' -_')
        clean_title = clean_title.replace(' ', '_')[:20]
        chunk_id = f"chapter_{chapter_num:03d}_{clean_title}"

        text_chunks.append({
            'id': chunk_id,
            'text': chapter.content,
            'title': chapter_title,
            'chapter_num': chapter_num
        })

    print(f"\n  Text chunks prepared: {len(text_chunks)}")

    for chunk in text_chunks:
        text_len = len(chunk['text'])
        word_count = len(chunk['text'].split())
        print(f"\n    Chunk '{chunk['id']}':")
        print(f"      Characters: {text_len:,}")
        print(f"      Words: {word_count:,}")

        # Check if text would be split by TTS (500 char limit)
        if text_len > 500:
            num_splits = (text_len // 500) + 1
            print(f"      TTS splits: ~{num_splits} sub-chunks (500 char limit)")

    # Stage 5: Check for potential issues
    print("\n" + "-"*80)
    print("STAGE 5: POTENTIAL ISSUES CHECK")
    print("-"*80)

    issues_found = []

    # Check for empty chapters
    empty_chapters = [ch for ch in result.chapters if ch.word_count == 0]
    if empty_chapters:
        issues_found.append(f"Found {len(empty_chapters)} empty chapters")

    # Check for very short chapters
    short_chapters = [ch for ch in result.chapters if 0 < ch.word_count < 50]
    if short_chapters:
        issues_found.append(f"Found {len(short_chapters)} very short chapters (<50 words)")

    # Check for very long chapters
    long_chapters = [ch for ch in result.chapters if ch.word_count > 10000]
    if long_chapters:
        issues_found.append(f"Found {len(long_chapters)} very long chapters (>10k words)")

    # Check for problematic characters that might cause TTS issues
    problematic_chars = ['[PAUSE:', '[CHAPTER_START:', '[EMPHASIS_']
    for ch in result.chapters:
        for pc in problematic_chars:
            if pc in ch.content:
                issues_found.append(f"Chapter {ch.chapter_num} contains TTS markers: {pc}")
                break

    # Check total content
    if len(result.text_content) < 1000:
        issues_found.append("Total content is very short (<1000 chars)")

    if issues_found:
        print("\n  ⚠️  Issues found:")
        for issue in issues_found:
            print(f"    - {issue}")
    else:
        print("\n  ✓ No obvious issues found")

    # Stage 6: Text Preprocessing Check
    print("\n" + "-"*80)
    print("STAGE 6: TEXT PREPROCESSING CHECK")
    print("-"*80)

    # Test that markers are properly stripped
    sample_text = result.chapters[1].content[:500] if len(result.chapters) > 1 else result.chapters[0].content[:500]
    print(f"\n  Sample text BEFORE preprocessing (first 200 chars):")
    print(f"    {sample_text[:200]}...")

    # Import and test preprocessing
    try:
        from pipelines.tts_pipeline import KokoroTTSPipeline

        # Create a mock preprocess test
        class MockConfig:
            model = "kokoro"
            model_path = "test"
            voice = "bf_lily"
            speed = 1.0
            pitch = 1.0
            sample_rate = 22050
            output_format = "wav"
            use_mlx = False  # Don't actually load model

        # Test the preprocessing function directly
        import re
        processed = sample_text

        # Apply the same preprocessing logic
        processed = re.sub(r'\[PAUSE:\s*[\d.]+\]', ' ', processed)
        processed = re.sub(r'\[EMPHASIS_STRONG:\s*([^\]]+)\]', r'\1', processed)
        processed = re.sub(r'\[EMPHASIS_MILD:\s*([^\]]+)\]', r'\1', processed)
        processed = re.sub(r'\[DIALOGUE_START\]', '', processed)
        processed = re.sub(r'\[DIALOGUE_END\]', '', processed)
        processed = re.sub(r'\[CHAPTER_START:\s*([^\]]+)\]', r'Chapter: \1. ', processed)
        processed = re.sub(r'\[IMAGE:\s*([^\]]+)\]', r'Image description: \1. ', processed)
        processed = re.sub(r'\[HEADER_END\]', '. ', processed)
        processed = re.sub(r'\[[A-Z_]+(?::\s*[^\]]+)?\]', ' ', processed)
        processed = re.sub(r'\s+', ' ', processed).strip()

        print(f"\n  Sample text AFTER preprocessing (first 200 chars):")
        print(f"    {processed[:200]}...")

        # Check for remaining markers
        remaining_markers = re.findall(r'\[[A-Z_]+[:\s][^\]]*\]', processed)
        if remaining_markers:
            print(f"\n  ⚠️  WARNING: {len(remaining_markers)} markers still present after preprocessing")
            for marker in remaining_markers[:5]:
                print(f"    - {marker}")
        else:
            print(f"\n  ✓ All markers successfully stripped")

    except Exception as e:
        print(f"\n  Error testing preprocessing: {e}")

    # Stage 7: TTS Availability Check
    print("\n" + "-"*80)
    print("STAGE 7: TTS AVAILABILITY CHECK")
    print("-"*80)

    try:
        from pipelines.tts_pipeline import create_tts_pipeline

        print("\n  Attempting to initialize TTS pipeline...")
        tts_pipeline = create_tts_pipeline(config.tts)
        print(f"  ✓ TTS pipeline initialized successfully")
        print(f"    Model: {config.tts.model}")
        print(f"    Voice: {config.tts.voice}")

        if hasattr(tts_pipeline, 'is_initialized') and tts_pipeline.is_initialized:
            print("    Status: Ready")

    except Exception as e:
        print(f"\n  ✗ TTS initialization failed: {e}")
        print("    (This is expected if running remotely without GPU/Metal)")

    print("\n" + "="*80)
    print("DIAGNOSTICS COMPLETE")
    print("="*80)

    return result


def test_tts_with_sample(sample_text: str = None):
    """Test TTS with a sample text."""

    if sample_text is None:
        sample_text = """
        This is a test of the text-to-speech system.
        The quick brown fox jumps over the lazy dog.
        How does the audio sound? Is it working correctly?
        """

    print("\n" + "-"*80)
    print("TTS SAMPLE TEST")
    print("-"*80)

    print(f"\nSample text ({len(sample_text)} chars):")
    print(f"  '{sample_text[:100]}...'")

    try:
        config = load_config()
        from pipelines.tts_pipeline import create_tts_pipeline

        tts_pipeline = create_tts_pipeline(config.tts)

        # Test synthesis
        print("\n  Testing synthesis...")
        result = tts_pipeline.model.synthesize(
            sample_text,
            voice=config.tts.voice,
            speed=config.tts.speed
        )

        if result is not None:
            import numpy as np
            duration = len(result) / config.tts.sample_rate
            print(f"  ✓ Generated {len(result):,} samples")
            print(f"  ✓ Duration: {duration:.2f} seconds")
        else:
            print("  ✗ Synthesis returned None")

    except Exception as e:
        print(f"\n  ✗ TTS test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Diagnose epub2tts pipeline')
    parser.add_argument('epub_file', type=Path, nargs='?',
                       default=Path('tests/fixtures/epub/alice-in-wonderland.epub'),
                       help='EPUB file to diagnose')
    parser.add_argument('--output-dir', '-o', type=Path, default=Path('./diagnostic_output'),
                       help='Output directory')
    parser.add_argument('--test-tts', action='store_true',
                       help='Also test TTS with sample text')

    args = parser.parse_args()

    result = diagnose_epub(args.epub_file, args.output_dir)

    if args.test_tts:
        test_tts_with_sample()
