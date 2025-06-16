"""Main entry point for ChatGPT Desktop Plus."""

import time
import sys
from typing import Optional
from pynput.keyboard import Key, Controller

from utils.logger import setup_logger, get_logger
from utils.exceptions import VoiceAssistantError
from config.settings import settings
from core.audio_processor import AudioProcessor
from core.hotword_detector import HotwordDetector
from core.window_manager import WindowManager
from ui.tray_manager import TrayManager

class ChatGPTDesktopPlus:
    """Main application class for ChatGPT Desktop Plus."""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.running = False
        self.listening = True
        
        # Initialize components
        self.hotword_detector = HotwordDetector()
        self.audio_processor = AudioProcessor(self._on_speech_detected)
        self.window_manager = WindowManager()
        self.tray_manager = None
        self.keyboard = Controller()
        
        self.logger.info("ChatGPT Desktop Plus initialized")
    
    def _on_speech_detected(self, text: str) -> None:
        """Handle detected speech."""
        if not self.listening:
            return
        
        detected_hotword = self.hotword_detector.check_hotwords(text)
        if detected_hotword:
            try:
                self.hotword_detector.trigger_action(detected_hotword)
            except Exception as e:
                self.logger.error(f"Failed to trigger action: {e}")
    
    def _toggle_listening(self, icon=None, item=None) -> None:
        """Toggle listening state."""
        self.listening = not self.listening
        status = "enabled" if self.listening else "disabled"
        self.logger.info(f"Listening {status}")
        
        if self.tray_manager:
            self.tray_manager.update_menu()
    
    def _test_alt_space(self, icon=None, item=None) -> None:
        """Test Alt+Space functionality."""
        self.logger.info("Testing Alt+Space...")
        try:
            with self.keyboard.pressed(Key.alt):
                self.keyboard.press(Key.space)
                self.keyboard.release(Key.space)
            self.logger.info("Alt+Space test successful!")
        except Exception as e:
            self.logger.error(f"Alt+Space test failed: {e}")
    
    def _test_button_click(self, icon=None, item=None) -> None:
        """Test microphone button click."""
        self.logger.info("Testing microphone button click...")
        if self.window_manager.click_microphone_button():
            self.logger.info("Button click test successful!")
        else:
            self.logger.error("Button click test failed!")
    
    def _test_window_detection(self, icon=None, item=None) -> None:
        """Test window detection."""
        self.logger.info("Testing window detection...")
        if self.window_manager.is_chatgpt_window_open():
            self.logger.info("ChatGPT window detected as OPEN")
        else:
            self.logger.info("ChatGPT window detected as CLOSED")
    
    def _show_hotwords(self, icon=None, item=None) -> None:
        """Show configured hotwords."""
        hotwords = self.hotword_detector.get_hotwords()
        self.logger.info(f"Configured hotwords: {', '.join(hotwords)}")
    
    def _quit_application(self, icon=None, item=None) -> None:
        """Quit the application."""
        self.logger.info("Quitting application...")
        self.stop()
    
    def _is_listening(self) -> bool:
        """Check if currently listening."""
        return self.listening
    
    def start(self) -> None:
        """Start the ChatGPT Desktop Plus."""
        if self.running:
            self.logger.warning("ChatGPT Desktop Plus is already running")
            return
        
        try:
            self.logger.info("Starting ChatGPT Desktop Plus...")
            self.running = True
            
            # Setup tray manager
            test_functions = {
                'alt_space': self._test_alt_space,
                'button_click': self._test_button_click,
                'window_detection': self._test_window_detection,
                'show_hotwords': self._show_hotwords
            }
            
            self.tray_manager = TrayManager(
                on_toggle_listening=self._toggle_listening,
                on_test_functions=test_functions,
                on_quit=self._quit_application,
                is_listening_func=self._is_listening
            )
            
            # Start components
            self.tray_manager.start()
            self.audio_processor.start()
            
            self.logger.info("ChatGPT Desktop Plus started successfully")
            
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal")
            
        except Exception as e:
            self.logger.error(f"Failed to start ChatGPT Desktop Plus: {e}")
            raise VoiceAssistantError(f"Startup failed: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the ChatGPT Desktop Plus."""
        if not self.running:
            return
        
        self.logger.info("Stopping ChatGPT Desktop Plus...")
        self.running = False
        
        # Stop components
        if self.audio_processor:
            self.audio_processor.stop()
        
        if self.tray_manager:
            self.tray_manager.stop()
        
        self.logger.info("ChatGPT Desktop Plus stopped")

def main():
    """Main entry point."""
    try:
        assistant = ChatGPTDesktopPlus()
        assistant.start()
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
