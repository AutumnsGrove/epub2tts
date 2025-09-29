"""
Secrets management for epub2tts.

This module handles loading and managing API keys and other sensitive configuration
from a secrets.json file. Follows the pattern established in CLAUDE.md guidelines.
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_secrets() -> Dict[str, str]:
    """
    Load API keys from secrets.json file with fallback to environment variables.

    Returns:
        Dictionary containing available secrets/API keys
    """
    # Find secrets.json in project root directory
    project_root = Path(__file__).parent.parent.parent  # Go up from src/utils/
    secrets_path = project_root / "secrets.json"

    try:
        with open(secrets_path, 'r') as f:
            secrets = json.load(f)
        logger.info(f"Loaded secrets from {secrets_path}")
        return secrets
    except FileNotFoundError:
        logger.info(f"secrets.json not found at {secrets_path}. Using environment variables as fallback.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing secrets.json: {e}. Using environment variables as fallback.")
        return {}
    except Exception as e:
        logger.error(f"Error loading secrets.json: {e}. Using environment variables as fallback.")
        return {}


def get_elevenlabs_api_key() -> Optional[str]:
    """
    Get ElevenLabs API key from secrets or environment variables.

    Returns:
        ElevenLabs API key if available, None otherwise
    """
    secrets = load_secrets()

    # Try secrets.json first, then environment variable
    api_key = secrets.get("elevenlabs_api_key") or os.getenv("ELEVENLABS_API_KEY")

    if api_key:
        logger.debug("ElevenLabs API key found")
        return api_key
    else:
        logger.debug("No ElevenLabs API key found in secrets.json or environment variables")
        return None


def has_elevenlabs_api_key() -> bool:
    """
    Check if ElevenLabs API key is available.

    Returns:
        True if API key is available, False otherwise
    """
    return get_elevenlabs_api_key() is not None


def validate_elevenlabs_api_key(api_key: str) -> bool:
    """
    Validate ElevenLabs API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if key format appears valid, False otherwise
    """
    if not api_key or not isinstance(api_key, str):
        return False

    # ElevenLabs API keys typically start with a specific format
    # This is a basic validation - actual validation happens during API calls
    return len(api_key) > 10 and api_key.strip() == api_key


def get_available_secrets() -> Dict[str, bool]:
    """
    Get information about which secrets are available.

    Returns:
        Dictionary with secret names as keys and availability as values
    """
    return {
        "elevenlabs_api_key": has_elevenlabs_api_key()
    }