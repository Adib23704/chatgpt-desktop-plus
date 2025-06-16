"""Core functionality package for ChatGPT Desktop Plus."""

from .audio_processor import AudioProcessor
from .hotword_detector import HotwordDetector
from .window_manager import WindowManager

__all__ = ['AudioProcessor', 'HotwordDetector', 'WindowManager']
