"""Configuration settings for ChatGPT Desktop Plus."""

import os
from typing import List
from dataclasses import dataclass

@dataclass
class AudioConfig:
    """Audio processing configuration."""
    timeout: float = 1.0
    phrase_time_limit: float = 3.0
    energy_threshold: int = 300
    dynamic_energy_threshold: bool = True

@dataclass
class UIConfig:
    """User interface configuration."""
    icon_path: str = "assets/icon.png"
    tray_title: str = "ChatGPT Desktop Plus"

@dataclass
class ActionConfig:
    """Action execution configuration."""
    click_delay: float = 1.0
    max_click_attempts: int = 3

@dataclass
class HotwordConfig:
    """Hotword detection configuration."""
    default_hotwords: List[str] = None
    
    def __post_init__(self):
        if self.default_hotwords is None:
            self.default_hotwords = [
                "hi chat", "hey chat", "hai chat",
                "hi gpt", "hey gpt", "hai gpt"
            ]

class Settings:
    """Main settings class."""
    
    def __init__(self):
        self.audio = AudioConfig()
        self.ui = UIConfig()
        self.action = ActionConfig()
        self.hotword = HotwordConfig()
        
        # Load environment variables if available
        self._load_from_env()
    
    def _load_from_env(self):
        """Load settings from environment variables."""
        if os.getenv('AUDIO_ENERGY_THRESHOLD'):
            self.audio.energy_threshold = int(os.getenv('AUDIO_ENERGY_THRESHOLD'))
        
        if os.getenv('CLICK_DELAY'):
            self.action.click_delay = float(os.getenv('CLICK_DELAY'))
        
        if os.getenv('ICON_PATH'):
            self.ui.icon_path = os.getenv('ICON_PATH')

# Global settings instance
settings = Settings()
