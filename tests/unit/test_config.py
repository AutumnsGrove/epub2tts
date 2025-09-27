"""
Unit tests for configuration management.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml

from src.utils.config import (
    Config, ConfigManager, ProcessingConfig, CleaningConfig,
    TTSConfig, load_config, get_config
)


class TestConfigDataClasses:
    """Test configuration dataclasses."""

    def test_processing_config_defaults(self):
        """Test ProcessingConfig default values."""
        config = ProcessingConfig()
        assert config.pandoc_path == "pandoc"
        assert config.temp_dir == "/tmp/epub2tts"
        assert config.max_parallel_jobs == 4

    def test_cleaning_config_defaults(self):
        """Test CleaningConfig default values."""
        config = CleaningConfig()
        assert config.remove_footnotes is True
        assert config.preserve_emphasis is True

    def test_tts_config_defaults(self):
        """Test TTSConfig default values."""
        config = TTSConfig()
        assert config.model == "kokoro"
        assert config.speed == 1.0
        assert config.pitch == 1.0
        assert config.sample_rate == 22050

    def test_config_from_dict(self):
        """Test Config creation from dictionary."""
        config_dict = {
            'processing': {'pandoc_path': '/usr/bin/pandoc'},
            'tts': {'speed': 1.5, 'voice': 'custom-voice'},
            'cleaning': {'remove_footnotes': False}
        }

        config = Config.from_dict(config_dict)

        assert config.processing.pandoc_path == '/usr/bin/pandoc'
        assert config.tts.speed == 1.5
        assert config.tts.voice == 'custom-voice'
        assert config.cleaning.remove_footnotes is False


class TestConfigManager:
    """Test ConfigManager class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config_manager = ConfigManager()

    def test_init_with_custom_path(self):
        """Test ConfigManager initialization with custom path."""
        custom_path = Path("/custom/config.yaml")
        manager = ConfigManager(custom_path)
        assert manager.default_config_path == custom_path

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_load_yaml_file(self, mock_yaml_load, mock_file):
        """Test YAML file loading."""
        mock_yaml_load.return_value = {'key': 'value'}

        result = self.config_manager._load_yaml_file(Path("test.yaml"))

        assert result == {'key': 'value'}
        mock_file.assert_called_once()
        mock_yaml_load.assert_called_once()

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_yaml_file_not_found(self, mock_file):
        """Test YAML file loading with file not found."""
        with pytest.raises(FileNotFoundError):
            self.config_manager._load_yaml_file(Path("nonexistent.yaml"))

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML"))
    def test_load_yaml_file_invalid_yaml(self, mock_yaml_load, mock_file):
        """Test YAML file loading with invalid YAML."""
        with pytest.raises(yaml.YAMLError):
            self.config_manager._load_yaml_file(Path("invalid.yaml"))

    def test_deep_merge_dicts(self):
        """Test deep dictionary merging."""
        base = {
            'a': 1,
            'b': {'c': 2, 'd': 3},
            'e': 5
        }
        override = {
            'b': {'c': 10, 'f': 6},
            'g': 7
        }

        result = self.config_manager._deep_merge_dicts(base, override)

        expected = {
            'a': 1,
            'b': {'c': 10, 'd': 3, 'f': 6},
            'e': 5,
            'g': 7
        }

        assert result == expected

    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        config = Config()
        # Should not raise any exception
        self.config_manager._validate_config(config)

    def test_validate_config_invalid_tts_speed(self):
        """Test configuration validation with invalid TTS speed."""
        config = Config()
        config.tts.speed = 3.0  # Invalid: > 2.0

        with pytest.raises(ValueError, match="TTS speed must be between"):
            self.config_manager._validate_config(config)

    def test_validate_config_invalid_tts_pitch(self):
        """Test configuration validation with invalid TTS pitch."""
        config = Config()
        config.tts.pitch = 0.1  # Invalid: < 0.5

        with pytest.raises(ValueError, match="TTS pitch must be between"):
            self.config_manager._validate_config(config)

    def test_validate_config_invalid_sample_rate(self):
        """Test configuration validation with invalid sample rate."""
        config = Config()
        config.tts.sample_rate = 8000  # Invalid rate

        with pytest.raises(ValueError, match="Invalid sample rate"):
            self.config_manager._validate_config(config)

    def test_validate_config_invalid_output_format(self):
        """Test configuration validation with invalid output format."""
        config = Config()
        config.tts.output_format = "flac"  # Invalid format

        with pytest.raises(ValueError, match="Invalid output format"):
            self.config_manager._validate_config(config)

    def test_validate_config_invalid_text_format(self):
        """Test configuration validation with invalid text format."""
        config = Config()
        config.output.text_format = "xml"  # Invalid format

        with pytest.raises(ValueError, match="Invalid text format"):
            self.config_manager._validate_config(config)

    def test_validate_config_invalid_chapter_settings(self):
        """Test configuration validation with invalid chapter settings."""
        config = Config()
        config.chapters.min_words_per_chapter = 0  # Invalid: must be positive

        with pytest.raises(ValueError, match="min_words_per_chapter must be positive"):
            self.config_manager._validate_config(config)

    def test_validate_config_invalid_chunk_size(self):
        """Test configuration validation with invalid chunk size."""
        config = Config()
        config.chapters.min_words_per_chapter = 500
        config.chapters.max_words_per_chunk = 300  # Invalid: < min_words

        with pytest.raises(ValueError, match="max_words_per_chunk must be"):
            self.config_manager._validate_config(config)

    @patch.object(ConfigManager, '_load_yaml_file')
    @patch.object(ConfigManager, '_validate_config')
    def test_load_config_default_only(self, mock_validate, mock_load_yaml):
        """Test loading config with default file only."""
        mock_load_yaml.return_value = {
            'processing': {'pandoc_path': 'pandoc'},
            'tts': {'speed': 1.0}
        }

        config = self.config_manager.load_config()

        assert isinstance(config, Config)
        mock_validate.assert_called_once()

    @patch.object(ConfigManager, '_load_yaml_file')
    @patch.object(ConfigManager, '_validate_config')
    def test_load_config_with_custom(self, mock_validate, mock_load_yaml):
        """Test loading config with custom override."""
        # Mock loading default config then custom config
        mock_load_yaml.side_effect = [
            {'processing': {'pandoc_path': 'pandoc'}},  # default
            {'processing': {'pandoc_path': '/custom/pandoc'}}  # custom
        ]

        custom_path = Path("custom.yaml")
        with patch.object(custom_path, 'exists', return_value=True):
            config = self.config_manager.load_config(custom_path)

        assert isinstance(config, Config)
        assert mock_load_yaml.call_count == 2

    def test_get_config_lazy_loading(self):
        """Test get_config loads config only once."""
        with patch.object(self.config_manager, 'load_config') as mock_load:
            mock_load.return_value = Config()

            # First call should load config
            config1 = self.config_manager.get_config()
            # Second call should return cached config
            config2 = self.config_manager.get_config()

            assert config1 is config2
            mock_load.assert_called_once()


class TestModuleFunctions:
    """Test module-level functions."""

    @patch('src.utils.config._config_manager')
    def test_get_config_function(self, mock_manager):
        """Test get_config module function."""
        mock_config = Config()
        mock_manager.get_config.return_value = mock_config

        result = get_config()

        assert result is mock_config
        mock_manager.get_config.assert_called_once()

    @patch('src.utils.config._config_manager')
    def test_load_config_function(self, mock_manager):
        """Test load_config module function."""
        mock_config = Config()
        mock_manager.load_config.return_value = mock_config
        custom_path = Path("test.yaml")

        result = load_config(custom_path)

        assert result is mock_config
        mock_manager.load_config.assert_called_once_with(custom_path)


class TestLoadRegexPatterns:
    """Test regex patterns loading function."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_load_regex_patterns_success(self, mock_yaml_load, mock_file):
        """Test successful regex patterns loading."""
        from src.utils.config import load_regex_patterns

        mock_patterns = {
            'cleaning_rules': {
                'remove': [{'pattern': r'\[\d+\]', 'name': 'footnotes'}]
            }
        }
        mock_yaml_load.return_value = mock_patterns

        result = load_regex_patterns(Path("patterns.yaml"))

        assert result == mock_patterns
        mock_file.assert_called_once()

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_regex_patterns_not_found(self, mock_file):
        """Test regex patterns loading with file not found."""
        from src.utils.config import load_regex_patterns

        with pytest.raises(FileNotFoundError):
            load_regex_patterns(Path("nonexistent.yaml"))

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid"))
    def test_load_regex_patterns_invalid_yaml(self, mock_yaml_load, mock_file):
        """Test regex patterns loading with invalid YAML."""
        from src.utils.config import load_regex_patterns

        with pytest.raises(yaml.YAMLError):
            load_regex_patterns(Path("invalid.yaml"))