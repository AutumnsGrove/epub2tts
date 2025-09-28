"""
Modern text processing module for epub2tts.

This module provides intelligent text processing capabilities using spaCy,
clean-text, and LangChain text splitters as alternatives to regex-based approaches.
"""

from .modern_text_processor import ModernTextProcessor, SmartChapter, ProcessingStats
from .enhanced_text_cleaner import EnhancedTextCleaner

__all__ = [
    'ModernTextProcessor',
    'SmartChapter',
    'ProcessingStats',
    'EnhancedTextCleaner'
]