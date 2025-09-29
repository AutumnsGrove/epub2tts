"""
Tests for ElevenLabs TTS integration.

These tests verify the ElevenLabs TTS pipeline integration, secrets management,
and factory pattern functionality. Most tests use mocking to avoid requiring
actual API keys during testing.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from tempfile import TemporaryDirectory

from src.utils.config import TTSConfig
from src.utils.secrets import (
    load_secrets, get_elevenlabs_api_key, has_elevenlabs_api_key,
    validate_elevenlabs_api_key, get_available_secrets
)


class TestSecretsManagement:
    """Test the secrets management functionality."""

    def test_load_secrets_file_not_found(self):
        """Test secrets loading when file doesn't exist."""
        with patch('src.utils.secrets.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.exists.return_value = False

            with patch('builtins.open', side_effect=FileNotFoundError):
                secrets = load_secrets()
                assert secrets == {}

    def test_load_secrets_json_decode_error(self):
        """Test secrets loading with malformed JSON."""
        with patch('builtins.open'):
            with patch('json.load', side_effect=json.JSONDecodeError("test", "test", 0)):
                secrets = load_secrets()
                assert secrets == {}

    def test_load_secrets_success(self):
        """Test successful secrets loading."""
        test_secrets = {"elevenlabs_api_key": "test-key"}

        with patch('builtins.open'):
            with patch('json.load', return_value=test_secrets):
                secrets = load_secrets()
                assert secrets == test_secrets

    def test_get_elevenlabs_api_key_from_secrets(self):
        """Test getting API key from secrets.json."""
        with patch('src.utils.secrets.load_secrets', return_value={"elevenlabs_api_key": "test-key"}):
            api_key = get_elevenlabs_api_key()
            assert api_key == "test-key"

    def test_get_elevenlabs_api_key_from_env(self):
        """Test getting API key from environment variable."""
        with patch('src.utils.secrets.load_secrets', return_value={}):
            with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'env-key'}):
                api_key = get_elevenlabs_api_key()
                assert api_key == "env-key"

    def test_get_elevenlabs_api_key_not_found(self):
        """Test when no API key is available."""
        with patch('src.utils.secrets.load_secrets', return_value={}):
            with patch.dict(os.environ, {}, clear=True):
                api_key = get_elevenlabs_api_key()
                assert api_key is None

    def test_has_elevenlabs_api_key_true(self):
        """Test has_elevenlabs_api_key when key exists."""
        with patch('src.utils.secrets.get_elevenlabs_api_key', return_value="test-key"):
            assert has_elevenlabs_api_key() is True

    def test_has_elevenlabs_api_key_false(self):
        """Test has_elevenlabs_api_key when key doesn't exist."""
        with patch('src.utils.secrets.get_elevenlabs_api_key', return_value=None):
            assert has_elevenlabs_api_key() is False

    def test_validate_elevenlabs_api_key_valid(self):
        """Test API key validation with valid key."""
        assert validate_elevenlabs_api_key("sk-valid-key-12345") is True

    def test_validate_elevenlabs_api_key_invalid(self):
        """Test API key validation with invalid keys."""
        assert validate_elevenlabs_api_key("") is False
        assert validate_elevenlabs_api_key(None) is False
        assert validate_elevenlabs_api_key("short") is False
        assert validate_elevenlabs_api_key("  key-with-spaces  ") is False

    def test_get_available_secrets(self):
        """Test getting available secrets information."""
        with patch('src.utils.secrets.has_elevenlabs_api_key', return_value=True):
            secrets_info = get_available_secrets()
            assert secrets_info == {"elevenlabs_api_key": True}


class TestElevenLabsTTSPipeline:
    """Test the ElevenLabs TTS pipeline."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock TTS config for testing."""
        config = TTSConfig()
        config.engine = "elevenlabs"
        config.elevenlabs_voice_id = "test-voice-id"
        config.elevenlabs_model = "eleven_multilingual_v2"
        config.elevenlabs_stability = 0.75
        config.elevenlabs_similarity_boost = 0.75
        config.elevenlabs_style = 0.0
        config.elevenlabs_max_chunk_chars = 2500
        return config

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', False)
    def test_elevenlabs_not_available(self, mock_config):
        """Test initialization when ElevenLabs library is not available."""
        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        with pytest.raises(RuntimeError, match="ElevenLabs library not available"):
            ElevenLabsTTSPipeline(mock_config)

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', True)
    @patch('src.pipelines.elevenlabs_tts.get_elevenlabs_api_key', return_value=None)
    def test_no_api_key(self, mock_get_key, mock_config):
        """Test initialization when no API key is available."""
        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        with pytest.raises(RuntimeError, match="ElevenLabs API key not found"):
            ElevenLabsTTSPipeline(mock_config)

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', True)
    @patch('src.pipelines.elevenlabs_tts.get_elevenlabs_api_key', return_value="test-key")
    @patch('src.pipelines.elevenlabs_tts.ElevenLabs')
    def test_successful_initialization(self, mock_elevenlabs_class, mock_get_key, mock_config):
        """Test successful initialization of ElevenLabs pipeline."""
        # Mock the ElevenLabs client
        mock_client = Mock()
        mock_voice = Mock()
        mock_voice.name = "Test Voice"
        mock_client.voices.get.return_value = mock_voice
        mock_elevenlabs_class.return_value = mock_client

        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        pipeline = ElevenLabsTTSPipeline(mock_config)

        assert pipeline.is_initialized is True
        assert pipeline.voice_id == "test-voice-id"
        assert pipeline.model_id == "eleven_multilingual_v2"
        mock_elevenlabs_class.assert_called_once_with(api_key="test-key")

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', True)
    @patch('src.pipelines.elevenlabs_tts.get_elevenlabs_api_key', return_value="test-key")
    @patch('src.pipelines.elevenlabs_tts.ElevenLabs')
    def test_process_chunk_not_initialized(self, mock_elevenlabs_class, mock_get_key, mock_config):
        """Test processing chunk when pipeline is not initialized."""
        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        # Make initialization fail
        mock_elevenlabs_class.side_effect = Exception("Initialization failed")

        with pytest.raises(RuntimeError):
            pipeline = ElevenLabsTTSPipeline(mock_config)

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', True)
    @patch('src.pipelines.elevenlabs_tts.get_elevenlabs_api_key', return_value="test-key")
    @patch('src.pipelines.elevenlabs_tts.ElevenLabs')
    def test_process_chunk_success(self, mock_elevenlabs_class, mock_get_key, mock_config):
        """Test successful chunk processing."""
        # Mock the ElevenLabs client
        mock_client = Mock()
        mock_voice = Mock()
        mock_voice.name = "Test Voice"
        mock_client.voices.get.return_value = mock_voice
        mock_client.generate.return_value = b'fake_audio_data'
        mock_elevenlabs_class.return_value = mock_client

        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        pipeline = ElevenLabsTTSPipeline(mock_config)

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.mp3"

            result = pipeline.process_chunk(
                text="Hello, this is a test.",
                output_path=str(output_path),
                chunk_id="test_chunk"
            )

            assert result.success is True
            assert result.audio_path == str(output_path)
            assert result.characters_processed > 0
            assert output_path.exists()

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', True)
    @patch('src.pipelines.elevenlabs_tts.get_elevenlabs_api_key', return_value="test-key")
    @patch('src.pipelines.elevenlabs_tts.ElevenLabs')
    def test_text_chunking(self, mock_elevenlabs_class, mock_get_key, mock_config):
        """Test text chunking for long text."""
        mock_client = Mock()
        mock_voice = Mock()
        mock_voice.name = "Test Voice"
        mock_client.voices.get.return_value = mock_voice
        mock_client.generate.return_value = b'fake_audio_data'
        mock_elevenlabs_class.return_value = mock_client

        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        pipeline = ElevenLabsTTSPipeline(mock_config)

        # Create text longer than max_chunk_chars
        long_text = "This is a test sentence. " * 200  # Should exceed 2500 chars

        chunks = pipeline._split_text_for_api(long_text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= pipeline.max_chunk_chars

    @patch('src.pipelines.elevenlabs_tts.ELEVENLABS_AVAILABLE', True)
    @patch('src.pipelines.elevenlabs_tts.get_elevenlabs_api_key', return_value="test-key")
    @patch('src.pipelines.elevenlabs_tts.ElevenLabs')
    def test_rate_limit_handling(self, mock_elevenlabs_class, mock_get_key, mock_config):
        """Test rate limit error handling."""
        mock_client = Mock()
        mock_voice = Mock()
        mock_voice.name = "Test Voice"
        mock_client.voices.get.return_value = mock_voice

        # First call raises rate limit error, second succeeds
        mock_client.generate.side_effect = [
            Exception("Rate limit exceeded"),
            b'fake_audio_data'
        ]
        mock_elevenlabs_class.return_value = mock_client

        from src.pipelines.elevenlabs_tts import ElevenLabsTTSPipeline

        pipeline = ElevenLabsTTSPipeline(mock_config)

        with patch('time.sleep'):  # Mock sleep to speed up test
            result = pipeline._synthesize_with_retry("Test text")
            assert result == b'fake_audio_data'


class TestTTSFactory:
    """Test the TTS factory function."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock TTS config for testing."""
        config = TTSConfig()
        return config

    @patch('src.utils.secrets.has_elevenlabs_api_key', return_value=False)
    @patch('src.pipelines.tts_pipeline.KokoroTTSPipeline')
    def test_factory_default_kokoro(self, mock_kokoro_class, mock_has_key, mock_config):
        """Test factory defaults to Kokoro when no ElevenLabs key."""
        # Mock Kokoro pipeline initialization
        mock_pipeline = Mock()
        mock_kokoro_class.return_value = mock_pipeline

        from src.pipelines.tts_pipeline import create_tts_pipeline

        pipeline = create_tts_pipeline(mock_config)

        # Should create and return mocked KokoroTTSPipeline
        mock_kokoro_class.assert_called_once_with(mock_config, None)
        assert pipeline == mock_pipeline

    @patch('src.utils.secrets.has_elevenlabs_api_key', return_value=True)
    @patch('src.pipelines.elevenlabs_tts.create_elevenlabs_tts_pipeline')
    def test_factory_auto_elevenlabs(self, mock_create_elevenlabs, mock_has_key, mock_config):
        """Test factory auto-selects ElevenLabs when key is available."""
        # Mock successful ElevenLabs pipeline creation
        mock_pipeline = Mock()
        mock_pipeline.__class__.__name__ = "ElevenLabsTTSPipeline"
        mock_create_elevenlabs.return_value = mock_pipeline

        from src.pipelines.tts_pipeline import create_tts_pipeline

        pipeline = create_tts_pipeline(mock_config)

        # Should call create_elevenlabs_tts_pipeline and return the mock pipeline
        mock_create_elevenlabs.assert_called_once_with(mock_config, None)
        assert pipeline == mock_pipeline

    @patch('src.utils.secrets.has_elevenlabs_api_key', return_value=True)
    @patch('src.pipelines.tts_pipeline.KokoroTTSPipeline')
    def test_factory_explicit_kokoro(self, mock_kokoro_class, mock_has_key, mock_config):
        """Test factory respects explicit Kokoro request."""
        mock_config.engine = "kokoro"
        mock_pipeline = Mock()
        mock_kokoro_class.return_value = mock_pipeline

        from src.pipelines.tts_pipeline import create_tts_pipeline

        pipeline = create_tts_pipeline(mock_config)

        # Should create and return mocked KokoroTTSPipeline even with ElevenLabs available
        mock_kokoro_class.assert_called_once_with(mock_config, None)
        assert pipeline == mock_pipeline

    @patch('src.utils.secrets.has_elevenlabs_api_key', return_value=False)
    @patch('src.pipelines.tts_pipeline.KokoroTTSPipeline')
    def test_factory_explicit_elevenlabs_no_key(self, mock_kokoro_class, mock_has_key, mock_config):
        """Test factory falls back to Kokoro when ElevenLabs requested but no key."""
        mock_config.engine = "elevenlabs"
        mock_pipeline = Mock()
        mock_kokoro_class.return_value = mock_pipeline

        from src.pipelines.tts_pipeline import create_tts_pipeline

        pipeline = create_tts_pipeline(mock_config)

        # Should fall back to KokoroTTSPipeline
        mock_kokoro_class.assert_called_once_with(mock_config, None)
        assert pipeline == mock_pipeline


class TestConfigurationIntegration:
    """Test configuration system integration with ElevenLabs settings."""

    def test_tts_config_elevenlabs_defaults(self):
        """Test TTSConfig has correct ElevenLabs defaults."""
        from src.utils.config import TTSConfig

        config = TTSConfig()

        assert hasattr(config, 'engine')
        assert hasattr(config, 'elevenlabs_voice_id')
        assert hasattr(config, 'elevenlabs_model')
        assert hasattr(config, 'elevenlabs_stability')
        assert hasattr(config, 'elevenlabs_similarity_boost')
        assert hasattr(config, 'elevenlabs_style')
        assert hasattr(config, 'elevenlabs_max_chunk_chars')

        # Check default values
        assert config.engine == "kokoro"
        assert config.elevenlabs_voice_id == "JBFqnCBsd6RMkjVDRZzb"
        assert config.elevenlabs_model == "eleven_multilingual_v2"
        assert config.elevenlabs_stability == 0.75
        assert config.elevenlabs_similarity_boost == 0.75
        assert config.elevenlabs_style == 0.0
        assert config.elevenlabs_max_chunk_chars == 2500

    def test_tts_config_custom_elevenlabs_values(self):
        """Test TTSConfig accepts custom ElevenLabs values."""
        from src.utils.config import TTSConfig

        config = TTSConfig(
            engine="elevenlabs",
            elevenlabs_voice_id="custom-voice",
            elevenlabs_model="eleven_flash_v2_5",
            elevenlabs_stability=0.5,
            elevenlabs_similarity_boost=0.8,
            elevenlabs_style=0.2,
            elevenlabs_max_chunk_chars=1000
        )

        assert config.engine == "elevenlabs"
        assert config.elevenlabs_voice_id == "custom-voice"
        assert config.elevenlabs_model == "eleven_flash_v2_5"
        assert config.elevenlabs_stability == 0.5
        assert config.elevenlabs_similarity_boost == 0.8
        assert config.elevenlabs_style == 0.2
        assert config.elevenlabs_max_chunk_chars == 1000