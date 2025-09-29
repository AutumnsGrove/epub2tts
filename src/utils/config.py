"""
Configuration management for epub2tts.

This module handles loading and validating configuration from YAML files.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    """Configuration for text processing."""
    epub_processor: str = "ebooklib"  # "ebooklib" or "pandoc"
    pandoc_path: str = "pandoc"
    temp_dir: str = "/tmp/epub2tts"
    max_parallel_jobs: int = 4


@dataclass
class TextProcessingConfig:
    """Configuration for modern text processing."""
    processor_mode: str = "modern"  # "legacy", "modern", "hybrid"
    spacy_model: str = "en_core_web_sm"
    chunk_size: int = 4000
    chunk_overlap: int = 200


@dataclass
class CleaningConfig:
    """Configuration for text cleaning."""
    remove_footnotes: bool = True
    remove_page_numbers: bool = True
    preserve_emphasis: bool = True
    preserve_dialogue_marks: bool = True
    add_pause_markers: bool = True


@dataclass
class ChapterConfig:
    """Configuration for chapter detection."""
    detect_by_headings: bool = True
    use_toc_when_available: bool = True
    min_words_per_chapter: int = 100
    max_words_per_chunk: int = 5000
    confidence_threshold: float = 0.6


@dataclass
class TTSConfig:
    """Configuration for TTS pipeline."""
    # Engine selection
    engine: str = "kokoro"  # "kokoro" or "elevenlabs"

    # Kokoro settings
    model: str = "kokoro"
    model_path: str = "./models/Kokoro-82M-8bit"
    voice: str = "bf_lily"
    speed: float = 1.0
    pitch: float = 1.0
    sample_rate: int = 22050
    output_format: str = "wav"

    # MLX-specific settings (for Kokoro)
    use_mlx: bool = True
    quantization: bool = False
    mlx_cache_dir: Optional[str] = None

    # ElevenLabs settings
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # George voice
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_stability: float = 0.75
    elevenlabs_similarity_boost: float = 0.75
    elevenlabs_style: float = 0.0
    elevenlabs_max_chunk_chars: int = 2500

    # Performance settings
    batch_size: int = 1
    max_workers: int = 4


@dataclass
class ImageConfig:
    """Configuration for image description."""
    enabled: bool = True
    model: str = "gemma-3n-e4b"
    model_path: str = "./models/llava"
    api_url: str = "http://127.0.0.1:1234"
    max_description_length: int = 100
    include_context: bool = True

    # Auto-loading settings
    auto_load_timeout: int = 10
    skip_if_not_loaded: bool = False


@dataclass
class OutputConfig:
    """Configuration for output formatting."""
    text_format: str = "plain"
    save_intermediate: bool = True
    create_metadata: bool = True
    generate_toc: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    file: str = "./logs/epub2tts.log"
    rotate_size: str = "10MB"
    keep_days: int = 7


@dataclass
class UIConfig:
    """Configuration for terminal UI."""
    mode: str = "classic"  # "classic" or "split-window"
    window_height: int = 20
    update_frequency: float = 0.1  # seconds
    show_stats: bool = True
    show_progress_bars: bool = True
    show_recent_activity: bool = True
    recent_activity_lines: int = 3

    # Color scheme
    colors: Dict[str, str] = field(default_factory=lambda: {
        'progress_complete': 'green',
        'progress_incomplete': 'white',
        'error': 'red',
        'warning': 'yellow',
        'info': 'blue',
        'success': 'green',
        'processing': 'cyan'
    })


@dataclass
class Config:
    """Main configuration container."""
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    text_processing: TextProcessingConfig = field(default_factory=TextProcessingConfig)
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    chapters: ChapterConfig = field(default_factory=ChapterConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    image_description: ImageConfig = field(default_factory=ImageConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        return cls(
            processing=ProcessingConfig(**config_dict.get('processing', {})),
            text_processing=TextProcessingConfig(**config_dict.get('text_processing', {})),
            cleaning=CleaningConfig(**config_dict.get('cleaning', {})),
            chapters=ChapterConfig(**config_dict.get('chapters', {})),
            tts=TTSConfig(**config_dict.get('tts', {})),
            image_description=ImageConfig(**config_dict.get('image_description', {})),
            output=OutputConfig(**config_dict.get('output', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            ui=UIConfig(**config_dict.get('ui', {}))
        )


class ConfigManager:
    """Manages configuration loading and validation."""

    def __init__(self, default_config_path: Optional[Path] = None):
        """Initialize configuration manager."""
        if default_config_path is None:
            # Find default config relative to this file
            current_dir = Path(__file__).parent.parent.parent
            default_config_path = current_dir / "config" / "default_config.yaml"

        self.default_config_path = default_config_path
        self._config: Optional[Config] = None

    def load_config(self, custom_config_path: Optional[Path] = None) -> Config:
        """
        Load configuration from YAML files.

        Args:
            custom_config_path: Optional path to custom config file

        Returns:
            Config object with loaded settings

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config contains invalid values
        """
        # Start with default config
        config_dict = self._load_yaml_file(self.default_config_path)

        # Override with custom config if provided
        if custom_config_path and custom_config_path.exists():
            custom_dict = self._load_yaml_file(custom_config_path)
            config_dict = self._deep_merge_dicts(config_dict, custom_dict)
            logger.info(f"Loaded custom config from {custom_config_path}")

        # Create and validate config
        self._config = Config.from_dict(config_dict)
        self._validate_config(self._config)

        logger.info("Configuration loaded successfully")
        return self._config

    def get_config(self) -> Config:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.error(f"Config file not found: {file_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file {file_path}: {e}")
            raise

    def _deep_merge_dicts(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self, config: Config) -> None:
        """Validate configuration values."""
        # Validate TTS settings
        if not (0.5 <= config.tts.speed <= 2.0):
            raise ValueError(f"TTS speed must be between 0.5 and 2.0, got {config.tts.speed}")

        if not (0.5 <= config.tts.pitch <= 2.0):
            raise ValueError(f"TTS pitch must be between 0.5 and 2.0, got {config.tts.pitch}")

        if config.tts.sample_rate not in [16000, 22050, 44100, 48000]:
            raise ValueError(f"Invalid sample rate: {config.tts.sample_rate}")

        if config.tts.output_format not in ["wav", "mp3"]:
            raise ValueError(f"Invalid output format: {config.tts.output_format}")

        # Validate output settings
        if config.output.text_format not in ["plain", "ssml", "json"]:
            raise ValueError(f"Invalid text format: {config.output.text_format}")

        # Validate chapter settings
        if config.chapters.min_words_per_chapter < 1:
            raise ValueError("min_words_per_chapter must be positive")

        if config.chapters.max_words_per_chunk < config.chapters.min_words_per_chapter:
            raise ValueError("max_words_per_chunk must be >= min_words_per_chapter")

        # Validate processing settings
        if config.processing.max_parallel_jobs < 1:
            raise ValueError("max_parallel_jobs must be positive")

        logger.debug("Configuration validation passed")


def load_regex_patterns(patterns_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load regex patterns from YAML file.

    Args:
        patterns_file: Path to patterns file

    Returns:
        Dictionary containing regex patterns
    """
    if patterns_file is None:
        # Find patterns file relative to this file
        current_dir = Path(__file__).parent.parent.parent
        patterns_file = current_dir / "config" / "regex_patterns.yaml"

    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns = yaml.safe_load(f)
        logger.info(f"Loaded regex patterns from {patterns_file}")
        return patterns
    except FileNotFoundError:
        logger.error(f"Regex patterns file not found: {patterns_file}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in patterns file {patterns_file}: {e}")
        raise


# Global config manager instance
_config_manager = ConfigManager()

def get_config() -> Config:
    """Get global configuration instance."""
    return _config_manager.get_config()

def load_config(custom_config_path: Optional[Path] = None) -> Config:
    """Load configuration with optional custom config."""
    return _config_manager.load_config(custom_config_path)