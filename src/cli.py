"""
Main CLI entry point for epub2tts.

This module provides the main CLI interface when epub2tts is installed as a package.
"""

import click
import sys
from pathlib import Path

# Import CLI commands from scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from process_epub import process_epub, validate, info, test_setup
from batch_convert import batch_convert


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    EPUB to TTS converter - Convert EPUB files to optimized text and audio.

    This tool provides a complete pipeline for converting EPUB files into
    TTS-optimized text with optional audio generation using Kokoro TTS
    and image descriptions via local VLM.
    """
    pass


# Add commands to the main group
main.add_command(process_epub, name="convert")
main.add_command(batch_convert, name="batch")
main.add_command(validate)
main.add_command(info)
main.add_command(test_setup, name="test")


@main.command()
@click.option('--show-config', is_flag=True, help='Show current configuration')
@click.option('--config-path', type=click.Path(path_type=Path), help='Show path to config file')
def config(show_config, config_path):
    """Manage configuration settings."""
    if config_path:
        # Show default config path
        from utils.config import ConfigManager
        manager = ConfigManager()
        click.echo(f"Default config path: {manager.default_config_path}")
        return

    if show_config:
        # Show current configuration
        try:
            from utils.config import get_config
            import yaml

            config_obj = get_config()
            config_dict = {
                'processing': config_obj.processing.__dict__,
                'cleaning': config_obj.cleaning.__dict__,
                'chapters': config_obj.chapters.__dict__,
                'tts': config_obj.tts.__dict__,
                'image_description': config_obj.image_description.__dict__,
                'output': config_obj.output.__dict__,
                'logging': config_obj.logging.__dict__
            }

            click.echo("Current Configuration:")
            click.echo(yaml.dump(config_dict, default_flow_style=False, indent=2))

        except Exception as e:
            click.echo(f"Error loading configuration: {e}")


@main.command()
def version():
    """Show version information."""
    click.echo("epub2tts version 0.1.0")
    click.echo("EPUB to TTS converter with Kokoro TTS and VLM integration")


if __name__ == '__main__':
    main()