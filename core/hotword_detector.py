"""Hotword detection and action triggering for ChatGPT Desktop Plus."""

from typing import List, Optional
from pynput.keyboard import Key, Controller
import time
from utils.logger import get_logger
from utils.exceptions import HotwordDetectionError
from config.settings import settings
from core.window_manager import WindowManager

class HotwordDetector:
    """Detects hotwords and triggers appropriate actions."""
    
    def __init__(self, hotwords: Optional[List[str]] = None):
        self.logger = get_logger(__name__)
        self.hotwords = hotwords or settings.hotword.default_hotwords
        self.hotwords = [word.lower() for word in self.hotwords]
        
        self.keyboard = Controller()
        self.window_manager = WindowManager()
        self.last_detected_hotword = None
        
        self.logger.info(f"Initialized with hotwords: {', '.join(self.hotwords)}")
    
    def check_hotwords(self, text: str) -> Optional[str]:
        """Check if any hotword is present in the recognized text."""
        text_lower = text.lower()
        
        for hotword in self.hotwords:
            if hotword in text_lower:
                return hotword
        
        return None
    
    def trigger_action(self, detected_hotword: str) -> None:
        """Trigger the complete action sequence."""
        self.last_detected_hotword = detected_hotword
        self.logger.info(f"Hotword '{detected_hotword}' detected! Triggering action...")
        
        try:
            if self.window_manager.is_chatgpt_window_open():
                self.logger.info("ChatGPT window already open - focusing and clicking button")
                self._handle_existing_window()
            else:
                self.logger.info("ChatGPT window not open - opening new window")
                self._handle_new_window()
                
        except Exception as e:
            raise HotwordDetectionError(f"Failed to trigger action: {e}")
    
    def _handle_existing_window(self) -> None:
        """Handle case where ChatGPT window is already open."""
        chatgpt_hwnd = self.window_manager.find_chatgpt_window()
        if chatgpt_hwnd:
            import win32gui
            win32gui.SetForegroundWindow(chatgpt_hwnd)
            time.sleep(0.3)
        
        if self.window_manager.click_microphone_button():
            self.logger.info(f"Successfully activated microphone for existing window")
        else:
            self.logger.warning("Failed to click microphone button on existing window")
    
    def _handle_new_window(self) -> None:
        """Handle case where ChatGPT window needs to be opened."""
        # Press Alt+Space
        with self.keyboard.pressed(Key.alt):
            self.keyboard.press(Key.space)
            self.keyboard.release(Key.space)
        
        self.logger.info("Alt+Space triggered")
        
        # Press Ctrl+N for new chat
        with self.keyboard.pressed(Key.ctrl_l):
            self.keyboard.press('n')
            self.keyboard.release('n')
        
        self.logger.info("Ctrl+N triggered")
        
        # Wait for window to appear
        time.sleep(settings.action.click_delay)
        
        # Click microphone button
        if self.window_manager.click_microphone_button():
            self.logger.info(f"Complete action sequence successful")
        else:
            self.logger.warning("Microphone button click failed")
    
    def add_hotword(self, hotword: str) -> None:
        """Add a new hotword."""
        hotword_lower = hotword.lower()
        if hotword_lower not in self.hotwords:
            self.hotwords.append(hotword_lower)
            self.logger.info(f"Added hotword: {hotword}")
        else:
            self.logger.warning(f"Hotword '{hotword}' already exists")
    
    def remove_hotword(self, hotword: str) -> None:
        """Remove a hotword."""
        hotword_lower = hotword.lower()
        if hotword_lower in self.hotwords:
            self.hotwords.remove(hotword_lower)
            self.logger.info(f"Removed hotword: {hotword}")
        else:
            self.logger.warning(f"Hotword '{hotword}' not found")
    
    def get_hotwords(self) -> List[str]:
        """Get current hotwords list."""
        return self.hotwords.copy()
