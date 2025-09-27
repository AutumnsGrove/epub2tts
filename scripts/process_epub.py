#!/usr/bin/env python3
"""
Main CLI script for processing EPUB files.

This script provides a command-line interface for converting EPUB files
to TTS-optimized text and optionally generating audio.
"""

import click
import logging
import sys
from pathlib import Path
from typing import Optional
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.epub_processor import EPUBProcessor
from utils.config import load_config, Config
from utils.logger import setup_logging


@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default=Path('./output'),
              help='Output directory for processed files')
@click.option('--format', '-f',
              type=click.Choice(['text', 'ssml', 'json']),
              default='text',
              help='Output format')
@click.option('--tts/--no-tts',
              default=False,
              help='Generate TTS audio files')
@click.option('--images/--no-images',
              default=True,
              help='Process images with VLM descriptions')
@click.option('--chapters/--no-chapters',
              default=True,
              help='Split output by chapters')
@click.option('--voice', '-v',
              default='bf_lily',
              help='TTS voice selection')
@click.option('--speed',
              type=float,
              default=1.0,
              help='TTS speed (0.5-2.0)')
@click.option('--config', '-c',
              type=click.Path(exists=True, path_type=Path),
              help='Custom configuration file')
@click.option('--verbose', is_flag=True,
              help='Enable verbose output')
@click.option('--resume', is_flag=True,
              help='Resume interrupted processing')
@click.option('--validate-only', is_flag=True,
              help='Only validate EPUB file without processing')
@click.option('--info', is_flag=True,
              help='Show EPUB information without full processing')
def process_epub(
    input_file: Path,
    output_dir: Path,
    format: str,
    tts: bool,
    images: bool,
    chapters: bool,
    voice: str,
    speed: float,
    config: Optional[Path],
    verbose: bool,
    resume: bool,
    validate_only: bool,
    info: bool
):
    """
    Convert EPUB to TTS-optimized text and optionally generate audio.

    INPUT_FILE: Path to the EPUB file to process

    Examples:

        # Basic text extraction
        python process_epub.py book.epub

        # Full pipeline with TTS
        python process_epub.py book.epub --tts --voice "bf_lily"

        # Custom configuration and output
        python process_epub.py book.epub -c custom_config.yaml -o ./my_output

        # JSON output with image processing
        python process_epub.py book.epub --format json --images

        # Validate EPUB without processing
        python process_epub.py book.epub --validate-only
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting EPUB processing: {input_file}")

    try:
        # Load configuration
        app_config = load_config(config)

        # Override config with CLI options
        if format != 'text':
            app_config.output.text_format = format
        if not images:
            app_config.image_description.enabled = False
        if voice != 'bf_lily':
            app_config.tts.voice = voice
        if speed != 1.0:
            app_config.tts.speed = speed

        # Validate speed
        if not (0.5 <= speed <= 2.0):
            raise click.BadParameter("Speed must be between 0.5 and 2.0")

        # Initialize processor
        processor = EPUBProcessor(app_config)

        # Validate EPUB file
        if validate_only or info:
            logger.info("Validating EPUB file...")
            validation_issues = processor.validate_epub(input_file)

            if validation_issues:
                click.echo("❌ EPUB Validation Issues:")
                for issue in validation_issues:
                    click.echo(f"  • {issue}")
                if validate_only:
                    sys.exit(1)
            else:
                click.echo("✅ EPUB file is valid")
                if validate_only:
                    sys.exit(0)

        # Show info if requested
        if info:
            logger.info("Getting EPUB information...")
            epub_info = processor.get_processing_info(input_file)

            if 'error' in epub_info:
                click.echo(f"❌ Error getting info: {epub_info['error']}")
                sys.exit(1)

            click.echo("\n📖 EPUB Information:")
            click.echo(f"  File size: {epub_info['file_size']:,} bytes")
            click.echo(f"  Estimated text length: {epub_info['estimated_text_length']:,} characters")
            click.echo(f"  Estimated word count: {epub_info['estimated_word_count']:,} words")
            click.echo(f"  Estimated processing time: {epub_info['estimated_processing_time']:.1f} seconds")
            click.echo(f"  Estimated audio duration: {epub_info['estimated_audio_duration']:.1f} minutes")

            if epub_info['metadata']:
                click.echo("\n📋 Metadata:")
                for key, value in epub_info['metadata'].items():
                    if value:
                        click.echo(f"  {key.title()}: {value}")

            sys.exit(0)

        # Check for existing output and resume capability
        if resume and output_dir.exists():
            logger.info(f"Resume mode: checking for existing output in {output_dir}")
            # TODO: Implement resume logic

        # Process EPUB
        logger.info("Starting EPUB processing...")
        start_time = time.time()

        with click.progressbar(
            length=100,
            label='Processing EPUB',
            show_percent=True,
            show_eta=True
        ) as bar:
            # Simulate progress updates (in real implementation, this would be callbacks)
            bar.update(20)  # Metadata extraction

            result = processor.process_epub(input_file, output_dir)

            bar.update(80)  # Processing complete

        processing_time = time.time() - start_time

        # Handle results
        if result.success:
            click.echo(f"\n✅ Processing completed successfully in {processing_time:.2f}s")
            click.echo(f"📁 Output saved to: {output_dir}")
            click.echo(f"📄 Text content: {len(result.text_content):,} characters")
            click.echo(f"📚 Chapters extracted: {len(result.chapters)}")

            if result.image_info:
                click.echo(f"🖼️  Images processed: {len(result.image_info)}")

            # Show cleaning stats
            stats = result.cleaning_stats
            click.echo(f"🧹 Text cleaning: {stats.characters_removed:,} characters removed "
                      f"({stats.compression_ratio:.1%} retained)")

            # TTS processing if requested
            if tts:
                click.echo("\n🔊 Starting TTS generation...")
                # TODO: Implement TTS processing
                click.echo("TTS processing not yet implemented")

        else:
            click.echo(f"\n❌ Processing failed: {result.error_message}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


@click.group()
def cli():
    """EPUB to TTS converter toolkit."""
    pass


@cli.command()
@click.argument('epub_file', type=click.Path(exists=True, path_type=Path))
def validate(epub_file: Path):
    """Validate an EPUB file."""
    try:
        config = load_config()
        processor = EPUBProcessor(config)

        issues = processor.validate_epub(epub_file)

        if issues:
            click.echo("❌ Validation Issues:")
            for issue in issues:
                click.echo(f"  • {issue}")
            sys.exit(1)
        else:
            click.echo("✅ EPUB file is valid")

    except Exception as e:
        click.echo(f"❌ Validation error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('epub_file', type=click.Path(exists=True, path_type=Path))
def info(epub_file: Path):
    """Show information about an EPUB file."""
    try:
        config = load_config()
        processor = EPUBProcessor(config)

        epub_info = processor.get_processing_info(epub_file)

        if 'error' in epub_info:
            click.echo(f"❌ Error: {epub_info['error']}")
            sys.exit(1)

        click.echo("📖 EPUB Information:")
        click.echo(f"  File size: {epub_info['file_size']:,} bytes")
        click.echo(f"  Estimated words: {epub_info['estimated_word_count']:,}")
        click.echo(f"  Processing time: ~{epub_info['estimated_processing_time']:.1f}s")
        click.echo(f"  Audio duration: ~{epub_info['estimated_audio_duration']:.1f} minutes")

        if epub_info['metadata']:
            click.echo("\n📋 Metadata:")
            for key, value in epub_info['metadata'].items():
                if value:
                    click.echo(f"  {key.title()}: {value}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


@cli.command()
def test_setup():
    """Test system setup and dependencies."""
    setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)

    click.echo("🔧 Testing system setup...")

    # Test Pandoc
    try:
        from core.pandoc_wrapper import verify_pandoc
        if verify_pandoc():
            click.echo("✅ Pandoc: Available")
        else:
            click.echo("❌ Pandoc: Not found")
    except Exception as e:
        click.echo(f"❌ Pandoc: Error - {e}")

    # Test configuration loading
    try:
        config = load_config()
        click.echo("✅ Configuration: Loaded successfully")
    except Exception as e:
        click.echo(f"❌ Configuration: Error - {e}")

    # Test regex patterns
    try:
        from core.text_cleaner import TextCleaner
        cleaner = TextCleaner()
        errors = cleaner.validate_patterns()
        if not errors:
            click.echo("✅ Regex patterns: Valid")
        else:
            click.echo(f"❌ Regex patterns: {len(errors)} errors")
            for error in errors[:3]:  # Show first 3 errors
                click.echo(f"  • {error}")
    except Exception as e:
        click.echo(f"❌ Regex patterns: Error - {e}")

    # Test temp directory
    try:
        config = load_config()
        temp_dir = Path(config.processing.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        test_file = temp_dir / "test_write.txt"
        test_file.write_text("test")
        test_file.unlink()
        click.echo("✅ Temp directory: Writable")
    except Exception as e:
        click.echo(f"❌ Temp directory: Error - {e}")

    click.echo("\n🎯 Setup test completed")


if __name__ == '__main__':
    # Use the main command directly when run as script
    process_epub()