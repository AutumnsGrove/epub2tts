#!/usr/bin/env python3
"""
Direct EPUB processor script that avoids import issues.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Now import with absolute imports
try:
    # Import all required modules directly
    import yaml
    from pathlib import Path
    import logging

    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Import the processor
    from core.epub_processor import EPUBProcessor
    from utils.config import load_config

    def main():
        """Main function to process EPUB file."""
        if len(sys.argv) != 2:
            print("Usage: python run_epub_processor.py <epub_file>")
            sys.exit(1)

        epub_file = Path(sys.argv[1])
        if not epub_file.exists():
            print(f"Error: File {epub_file} does not exist")
            sys.exit(1)

        print(f"🔄 Processing EPUB file: {epub_file}")

        try:
            # Load configuration
            config = load_config()
            print("✅ Configuration loaded")

            # Initialize processor
            processor = EPUBProcessor(config)
            print("✅ EPUB processor initialized")

            # Create output directory
            output_dir = Path("./output") / epub_file.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process the EPUB
            print("🔄 Starting EPUB processing...")
            result = processor.process_epub(epub_file, output_dir)

            if result.success:
                print(f"✅ Processing completed successfully!")
                print(f"📁 Output directory: {output_dir}")
                print(f"📄 Text content: {len(result.text_content):,} characters")
                print(f"📚 Chapters extracted: {len(result.chapters)}")

                if result.image_info:
                    print(f"🖼️  Images processed: {len(result.image_info)}")

                # Show cleaning stats
                if hasattr(result, 'cleaning_stats') and result.cleaning_stats:
                    stats = result.cleaning_stats
                    print(f"🧹 Text cleaning: {stats.characters_removed:,} characters removed")

            else:
                print(f"❌ Processing failed: {result.error_message}")
                sys.exit(1)

        except Exception as e:
            logger.error(f"Error processing EPUB: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            sys.exit(1)

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("The project structure has import issues. Let me try a different approach...")
    sys.exit(1)