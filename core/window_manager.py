"""Window management for ChatGPT Desktop Plus."""

import win32gui
import win32con
import win32process
import psutil
import pyautogui
import time
from typing import Optional, Tuple
from utils.logger import get_logger
from utils.exceptions import WindowDetectionError
from config.settings import settings

class WindowManager:
    """Manages ChatGPT window detection and interaction."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
    
    def _get_window_process_name(self, hwnd: int) -> str:
        """Get the process name for a given window handle."""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name().lower()
        except Exception:
            return ""
    
    def is_chatgpt_window_open(self) -> bool:
        """Check if ChatGPT window is already open using multiple detection methods."""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    # Method 1: Check process name
                    process_name = self._get_window_process_name(hwnd)
                    if 'chatgpt' in process_name or 'openai' in process_name:
                        windows.append(hwnd)
                        return True
                    
                    # Method 2: Check window class name
                    class_name = win32gui.GetClassName(hwnd).lower()
                    if 'chatgpt' in class_name or 'openai' in class_name:
                        windows.append(hwnd)
                        return True
                    
                    # Method 3: Check window properties for ChatGPT-like popup
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    
                    if (style & win32con.WS_POPUP) or (ex_style & win32con.WS_EX_TOOLWINDOW):
                        rect = win32gui.GetWindowRect(hwnd)
                        width = rect[2] - rect[0]
                        height = rect[3] - rect[1]
                        
                        if 400 <= width <= 1200 and 300 <= height <= 800:
                            window_text = win32gui.GetWindowText(hwnd)
                            if len(window_text) > 0:
                                windows.append(hwnd)
                                return True
                    
                    # Method 4: Check executable path
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        exe_path = process.exe().lower()
                        if 'chatgpt' in exe_path or 'openai' in exe_path:
                            windows.append(hwnd)
                            return True
                    except Exception:
                        pass
                        
                except Exception:
                    pass
            
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        result = len(windows) > 0
        self.logger.info(f"ChatGPT window detection: {'OPEN' if result else 'CLOSED'}")
        return result
    
    def find_chatgpt_window(self) -> Optional[int]:
        """Find ChatGPT popup window using multiple detection methods."""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    # Check various methods to identify ChatGPT window
                    process_name = self._get_window_process_name(hwnd)
                    if 'chatgpt' in process_name or 'openai' in process_name:
                        windows.append((hwnd, f"Process: {process_name}", "ProcessMatch"))
                        return True
                    
                    class_name = win32gui.GetClassName(hwnd).lower()
                    if 'chatgpt' in class_name or 'openai' in class_name:
                        windows.append((hwnd, f"Class: {class_name}", "ClassMatch"))
                        return True
                    
                    # Check for popup windows with ChatGPT characteristics
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    
                    if (style & win32con.WS_POPUP) or (ex_style & win32con.WS_EX_TOOLWINDOW):
                        rect = win32gui.GetWindowRect(hwnd)
                        width = rect[2] - rect[0]
                        height = rect[3] - rect[1]
                        
                        if 400 <= width <= 1200 and 300 <= height <= 800:
                            window_text = win32gui.GetWindowText(hwnd)
                            if len(window_text) > 0:
                                windows.append((hwnd, f"Popup: {window_text}", "PopupMatch"))
                                return True
                    
                except Exception:
                    pass
            
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            hwnd, description, match_type = windows[0]
            self.logger.debug(f"Found ChatGPT window: {description} ({match_type})")
            return hwnd
        
        return None
    
    def find_microphone_button(self) -> Optional[Tuple[int, int]]:
        """Find the microphone button coordinates."""
        try:
            chatgpt_hwnd = self.find_chatgpt_window()
            if chatgpt_hwnd:
                rect = win32gui.GetWindowRect(chatgpt_hwnd)
                left, top, right, bottom = rect
                
                self.logger.info(f"ChatGPT window bounds: {rect}")
                
                # Focus the window
                win32gui.SetForegroundWindow(chatgpt_hwnd)
                time.sleep(0.2)
                
                # Calculate button position in bottom-right area
                window_width = right - left
                window_height = bottom - top
                
                search_right = right - 10
                search_bottom = bottom - 20
                
                button_x = search_right - 30
                button_y = search_bottom - 30
                
                return (button_x, button_y)
            
            # Fallback to screen coordinates
            screen_width, screen_height = pyautogui.size()
            return (screen_width - 50, screen_height - 80)
            
        except Exception as e:
            raise WindowDetectionError(f"Error finding microphone button: {e}")
    
    def click_microphone_button(self) -> bool:
        """Click the microphone button with retry logic."""
        for attempt in range(settings.action.max_click_attempts):
            try:
                self.logger.info(f"Microphone button click attempt {attempt + 1}")
                
                if attempt > 0:
                    time.sleep(0.5 * attempt)
                
                button_pos = self.find_microphone_button()
                if button_pos:
                    x, y = button_pos
                    
                    screen_width, screen_height = pyautogui.size()
                    if 0 <= x <= screen_width and 0 <= y <= screen_height:
                        pyautogui.moveTo(x, y, duration=0.1)
                        time.sleep(0.1)
                        pyautogui.click(x, y)
                        
                        self.logger.info(f"Clicked microphone button at ({x}, {y})")
                        time.sleep(0.2)
                        return True
                    else:
                        self.logger.warning(f"Button position ({x}, {y}) out of bounds")
                
            except Exception as e:
                self.logger.error(f"Click attempt {attempt + 1} failed: {e}")
        
        self.logger.error("All microphone button click attempts failed")
        return False
