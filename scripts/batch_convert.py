#!/usr/bin/env python3
"""
Batch processing script for multiple EPUB files.

This script processes multiple EPUB files in parallel with progress tracking
and error handling.
"""

import click
import logging
import sys
from pathlib import Path
from typing import List, Optional
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.epub_processor import EPUBProcessor, ProcessingResult
from utils.config import load_config
from utils.logger import setup_logging, ProgressLogger


class BatchProcessor:
    """Batch processor for multiple EPUB files."""

    def __init__(self, config, max_workers: Optional[int] = None):
        """Initialize batch processor."""
        self.config = config
        self.max_workers = max_workers or min(4, mp.cpu_count())
        self.logger = logging.getLogger(__name__)

    def process_files(
        self,
        epub_files: List[Path],
        output_base_dir: Path,
        resume: bool = False
    ) -> List[ProcessingResult]:
        """
        Process multiple EPUB files.

        Args:
            epub_files: List of EPUB files to process
            output_base_dir: Base output directory
            resume: Whether to resume interrupted processing

        Returns:
            List of processing results
        """
        self.logger.info(f"Starting batch processing of {len(epub_files)} files")

        # Filter files if resuming
        if resume:
            epub_files = self._filter_completed_files(epub_files, output_base_dir)
            self.logger.info(f"Resume mode: {len(epub_files)} files remaining")

        if not epub_files:
            self.logger.info("No files to process")
            return []

        # Create output directory
        output_base_dir.mkdir(parents=True, exist_ok=True)

        # Process files
        results = []
        progress = ProgressLogger("Batch processing", len(epub_files))

        if self.max_workers == 1:
            # Sequential processing
            for epub_file in epub_files:
                result = self._process_single_file(epub_file, output_base_dir)
                results.append(result)
                progress.update()
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self._process_single_file, epub_file, output_base_dir): epub_file
                    for epub_file in epub_files
                }

                # Collect results as they complete
                for future in as_completed(future_to_file):
                    epub_file = future_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)
                        progress.update()
                    except Exception as e:
                        self.logger.error(f"Error processing {epub_file}: {e}")
                        # Create failed result
                        failed_result = ProcessingResult(
                            success=False,
                            text_content="",
                            chapters=[],
                            metadata={},
                            image_info=[],
                            cleaning_stats=None,
                            error_message=str(e)
                        )
                        results.append(failed_result)
                        progress.update()

        progress.finish()

        # Generate summary report
        self._generate_summary_report(results, output_base_dir)

        return results

    def _process_single_file(self, epub_file: Path, output_base_dir: Path) -> ProcessingResult:
        """Process a single EPUB file."""
        try:
            # Create processor instance for this file
            processor = EPUBProcessor(self.config)

            # Create output directory for this file
            output_dir = output_base_dir / epub_file.stem

            # Process the file
            result = processor.process_epub(epub_file, output_dir)

            if result.success:
                self.logger.info(f"✅ Completed: {epub_file.name}")
            else:
                self.logger.error(f"❌ Failed: {epub_file.name} - {result.error_message}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Error processing {epub_file}: {e}")
            return ProcessingResult(
                success=False,
                text_content="",
                chapters=[],
                metadata={},
                image_info=[],
                cleaning_stats=None,
                error_message=str(e)
            )

    def _filter_completed_files(self, epub_files: List[Path], output_base_dir: Path) -> List[Path]:
        """Filter out already processed files when resuming."""
        remaining_files = []

        for epub_file in epub_files:
            output_dir = output_base_dir / epub_file.stem

            # Check if output exists and looks complete
            if output_dir.exists():
                # Look for main output file
                text_file = output_dir / f"{epub_file.stem}.txt"
                json_file = output_dir / f"{epub_file.stem}.json"

                if text_file.exists() or json_file.exists():
                    self.logger.debug(f"Skipping completed file: {epub_file}")
                    continue

            remaining_files.append(epub_file)

        return remaining_files

    def _generate_summary_report(self, results: List[ProcessingResult], output_dir: Path) -> None:
        """Generate a summary report of batch processing."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_processing_time = sum(r.processing_time for r in results if r.processing_time)
        total_characters = sum(len(r.text_content) for r in successful)
        total_chapters = sum(len(r.chapters) for r in successful)

        # Create summary data
        summary = {
            'batch_processing': {
                'total_files': len(results),
                'successful': len(successful),
                'failed': len(failed),
                'total_processing_time': total_processing_time,
                'total_characters_extracted': total_characters,
                'total_chapters_extracted': total_chapters,
                'average_processing_time': total_processing_time / len(results) if results else 0
            },
            'successful_files': [
                {
                    'file': f"file_{i}",  # Don't include full paths for privacy
                    'characters': len(r.text_content),
                    'chapters': len(r.chapters),
                    'processing_time': r.processing_time
                }
                for i, r in enumerate(successful)
            ],
            'failed_files': [
                {
                    'file': f"file_{i}",
                    'error': r.error_message
                }
                for i, r in enumerate(failed)
            ]
        }

        # Save summary report
        summary_file = output_dir / 'batch_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Summary report saved to: {summary_file}")

        # Log summary to console
        click.echo(f"\n📊 Batch Processing Summary:")
        click.echo(f"  Total files: {len(results)}")
        click.echo(f"  ✅ Successful: {len(successful)}")
        click.echo(f"  ❌ Failed: {len(failed)}")
        click.echo(f"  ⏱️  Total time: {total_processing_time:.1f}s")
        if successful:
            click.echo(f"  📄 Total characters: {total_characters:,}")
            click.echo(f"  📚 Total chapters: {total_chapters}")


@click.command()
@click.argument('epub_patterns', nargs=-1, required=True)
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default=Path('./batch_output'),
              help='Base output directory')
@click.option('--parallel', '-p',
              type=int,
              default=4,
              help='Number of parallel workers')
@click.option('--config', '-c',
              type=click.Path(exists=True, path_type=Path),
              help='Custom configuration file')
@click.option('--resume', is_flag=True,
              help='Resume interrupted processing')
@click.option('--verbose', is_flag=True,
              help='Enable verbose output')
@click.option('--format', '-f',
              type=click.Choice(['text', 'json']),
              default='text',
              help='Output format')
@click.option('--images/--no-images',
              default=True,
              help='Process images with VLM')
@click.option('--dry-run', is_flag=True,
              help='Show what would be processed without actually processing')
def batch_convert(
    epub_patterns: tuple,
    output_dir: Path,
    parallel: int,
    config: Optional[Path],
    resume: bool,
    verbose: bool,
    format: str,
    images: bool,
    dry_run: bool
):
    """
    Batch convert multiple EPUB files to text.

    EPUB_PATTERNS: File patterns or paths to EPUB files (e.g., *.epub, book1.epub, /path/to/books/*.epub)

    Examples:

        # Process all EPUB files in current directory
        python batch_convert.py *.epub

        # Process specific files with custom output
        python batch_convert.py book1.epub book2.epub -o ./my_output

        # Parallel processing with 8 workers
        python batch_convert.py /path/to/books/*.epub --parallel 8

        # Resume interrupted processing
        python batch_convert.py *.epub --resume

        # Dry run to see what would be processed
        python batch_convert.py *.epub --dry-run
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)

    try:
        # Expand file patterns to actual file paths
        epub_files = []
        for pattern in epub_patterns:
            pattern_path = Path(pattern)

            if pattern_path.is_file() and pattern_path.suffix.lower() == '.epub':
                # Direct file path
                epub_files.append(pattern_path)
            elif '*' in pattern or '?' in pattern:
                # Glob pattern
                parent_dir = pattern_path.parent if pattern_path.parent != Path('.') else Path.cwd()
                matches = list(parent_dir.glob(pattern_path.name))
                epub_files.extend([f for f in matches if f.suffix.lower() == '.epub'])
            else:
                # Directory or non-EPUB file
                if pattern_path.is_dir():
                    epub_files.extend(pattern_path.glob('*.epub'))
                else:
                    logger.warning(f"Skipping non-EPUB file: {pattern}")

        # Remove duplicates and sort
        epub_files = sorted(list(set(epub_files)))

        if not epub_files:
            click.echo("❌ No EPUB files found matching the patterns")
            sys.exit(1)

        click.echo(f"📚 Found {len(epub_files)} EPUB files")

        if dry_run:
            click.echo("\n🔍 Files that would be processed:")
            for i, epub_file in enumerate(epub_files, 1):
                click.echo(f"  {i:3d}. {epub_file}")
            click.echo(f"\n📁 Output directory: {output_dir}")
            click.echo(f"🔧 Parallel workers: {parallel}")
            click.echo(f"📄 Output format: {format}")
            click.echo(f"🖼️  Process images: {images}")
            return

        # Validate parallel workers
        if parallel < 1:
            raise click.BadParameter("Parallel workers must be at least 1")
        if parallel > mp.cpu_count():
            logger.warning(f"Requested {parallel} workers but only {mp.cpu_count()} CPUs available")

        # Load configuration
        app_config = load_config(config)

        # Override config with CLI options
        app_config.output.text_format = format
        app_config.image_description.enabled = images
        app_config.processing.max_parallel_jobs = parallel

        # Create batch processor
        batch_processor = BatchProcessor(app_config, max_workers=parallel)

        # Start processing
        start_time = time.time()
        click.echo(f"\n🚀 Starting batch processing with {parallel} workers...")

        results = batch_processor.process_files(epub_files, output_dir, resume)

        total_time = time.time() - start_time

        # Final summary
        successful = len([r for r in results if r.success])
        failed = len(results) - successful

        click.echo(f"\n🎉 Batch processing completed in {total_time:.1f}s")
        click.echo(f"✅ Successfully processed: {successful}/{len(results)} files")

        if failed > 0:
            click.echo(f"❌ Failed: {failed} files")
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n⏹️  Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Batch processing error: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    batch_convert()