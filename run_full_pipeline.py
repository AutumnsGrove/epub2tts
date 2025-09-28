#!/usr/bin/env python3
"""
Full EPUB to TTS pipeline with Kokoro TTS and image processing.
"""

import sys
import os
from pathlib import Path
import argparse
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('epub2tts_full.log')
        ]
    )

def main():
    """Main function to run the complete EPUB to TTS pipeline."""
    parser = argparse.ArgumentParser(description="Complete EPUB to TTS pipeline with Kokoro")
    parser.add_argument("epub_file", help="Path to the EPUB file")
    parser.add_argument("-o", "--output", help="Output directory (default: ./output/<epub_name>)")
    parser.add_argument("--no-tts", action="store_true", help="Skip TTS generation")
    parser.add_argument("--no-images", action="store_true", help="Skip image processing")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Validate input file
    epub_path = Path(args.epub_file)
    if not epub_path.exists():
        logger.error(f"EPUB file not found: {epub_path}")
        sys.exit(1)

    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path("./output") / epub_path.stem

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Import pipeline components
        from utils.config import load_config
        from pipelines.orchestrator import PipelineOrchestrator

        # Load configuration
        config = load_config()
        logger.info("✅ Configuration loaded")

        # Initialize orchestrator
        orchestrator = PipelineOrchestrator(config)
        logger.info("✅ Pipeline orchestrator initialized")

        # Configure pipeline options
        enable_tts = not args.no_tts
        enable_images = not args.no_images

        logger.info(f"🔄 Starting full pipeline processing for: {epub_path}")
        logger.info(f"📁 Output directory: {output_dir}")
        logger.info(f"🔊 TTS enabled: {enable_tts}")
        logger.info(f"🖼️  Image processing enabled: {enable_images}")

        # Run the complete pipeline
        result = orchestrator.process_epub_complete(
            epub_path=epub_path,
            output_dir=output_dir,
            enable_tts=enable_tts,
            enable_images=enable_images
        )

        # Display results
        if result.epub_processing.success:
            logger.info("🎉 Pipeline completed successfully!")
            logger.info(f"📄 Text content: {len(result.epub_processing.text_content):,} characters")
            logger.info(f"📚 Chapters: {len(result.epub_processing.chapters)}")

            if result.image_descriptions:
                logger.info(f"🖼️  Images processed: {len(result.image_descriptions)}")

            if result.tts_results:
                tts_info = result.tts_results
                if "audio_files" in tts_info:
                    logger.info(f"🔊 Audio files generated: {len(tts_info['audio_files'])}")
                if "total_duration" in tts_info:
                    duration = tts_info['total_duration']
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    logger.info(f"⏱️  Total audio duration: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")

            # Show output structure
            logger.info(f"📁 Output saved to: {output_dir}")
            if output_dir.exists():
                for item in sorted(output_dir.iterdir()):
                    if item.is_file():
                        size = item.stat().st_size
                        if size > 1024*1024:
                            size_str = f"{size/(1024*1024):.1f}MB"
                        elif size > 1024:
                            size_str = f"{size/1024:.1f}KB"
                        else:
                            size_str = f"{size}B"
                        logger.info(f"  📄 {item.name} ({size_str})")
                    elif item.is_dir():
                        file_count = len(list(item.iterdir()))
                        logger.info(f"  📁 {item.name}/ ({file_count} files)")

        else:
            logger.error(f"❌ Pipeline failed: {result.epub_processing.error_message}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"💥 Pipeline error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()