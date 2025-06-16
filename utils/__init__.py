"""Utilities package for ChatGPT Desktop Plus."""

from .logger import setup_logger, get_logger
from .exceptions import VoiceAssistantError

__all__ = ['setup_logger', 'get_logger', 'VoiceAssistantError']
