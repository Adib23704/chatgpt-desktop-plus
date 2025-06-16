"""System tray management for ChatGPT Desktop Plus."""

import os
import threading
from PIL import Image
import pystray
from pystray import MenuItem as item
from typing import Callable, Optional
from utils.logger import get_logger
from utils.exceptions import UIError
from config.settings import settings

class TrayManager:
    """Manages the system tray icon and menu."""
    
    def __init__(self, 
                 on_toggle_listening: Callable,
                 on_test_functions: dict,
                 on_quit: Callable,
                 is_listening_func: Callable[[], bool]):
        self.logger = get_logger(__name__)
        self.on_toggle_listening = on_toggle_listening
        self.on_test_functions = on_test_functions
        self.on_quit = on_quit
        self.is_listening_func = is_listening_func
        
        self.tray_icon = None
        self.icon_image = self._load_icon()
    
    def _load_icon(self) -> Image.Image:
        """Load the tray icon image."""
        try:
            if os.path.exists(settings.ui.icon_path):
                return Image.open(settings.ui.icon_path)
            else:
                self.logger.warning(f"Icon file {settings.ui.icon_path} not found, creating default")
                return self._create_default_icon()
        except Exception as e:
            self.logger.error(f"Failed to load icon: {e}")
            return self._create_default_icon()
    
    def _create_default_icon(self) -> Image.Image:
        """Create a simple default icon."""
        return Image.new('RGB', (64, 64), color='blue')
    
    def _create_menu(self):
        """Create the system tray menu."""
        return pystray.Menu(
            item(
                lambda text: f"{'✓' if self.is_listening_func() else '✗'} Listening",
                self.on_toggle_listening,
                checked=lambda item: self.is_listening_func()
            ),
            pystray.Menu.SEPARATOR,
            item("Test Alt+Space", self.on_test_functions.get('alt_space')),
            item("Test Button Click", self.on_test_functions.get('button_click')),
            item("Test Window Detection", self.on_test_functions.get('window_detection')),
            item("Show Hotwords", self.on_test_functions.get('show_hotwords')),
            pystray.Menu.SEPARATOR,
            item("Quit", self.on_quit)
        )
    
    def start(self) -> None:
        """Start the system tray icon."""
        try:
            self.tray_icon = pystray.Icon(
                "chatgpt_desktop_plus",
                self.icon_image,
                settings.ui.tray_title,
                menu=self._create_menu()
            )
            
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
            self.logger.info("System tray icon started successfully")
            
        except Exception as e:
            raise UIError(f"Failed to start tray icon: {e}")
    
    def stop(self) -> None:
        """Stop the system tray icon."""
        if self.tray_icon:
            self.tray_icon.stop()
            self.logger.info("System tray icon stopped")
    
    def update_menu(self) -> None:
        """Update the tray menu (useful for dynamic content)."""
        if self.tray_icon:
            self.tray_icon.update_menu()
