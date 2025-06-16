import speech_recognition as sr
import pyaudio
import threading
import time
import logging
from pynput.keyboard import Key, Controller
from pynput import mouse
from typing import Optional, List
import queue
import sys
from PIL import Image
import pystray
from pystray import MenuItem as item
import os
import pyautogui
import win32gui # type: ignore
import win32con # type: ignore
import win32api  # type: ignore
import win32process  # type: ignore
import psutil

class HotwordDetector:
    def __init__(self, 
                 hotwords: List[str] = None,
                 timeout: float = 1.0,
                 phrase_time_limit: float = 3.0,
                 energy_threshold: int = 300,
                 dynamic_energy_threshold: bool = True,
                 icon_path: str = "assets/icon.png",
                 click_delay: float = 1.0,
                 max_click_attempts: int = 3):

        if hotwords is None:
            hotwords = [
                "hi chat", "hey chat", "hai chat",
                "hi gpt", "hey gpt", "hai gpt"
            ]
        
        self.hotwords = [hotword.lower() for hotword in hotwords]
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.running = False
        self.listening = True
        self.icon_path = icon_path
        self.last_detected_hotword = None
        self.click_delay = click_delay
        self.max_click_attempts = max_click_attempts
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = dynamic_energy_threshold
        self.keyboard = Controller()
        self.mouse_controller = mouse.Controller()
        
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.audio_queue = queue.Queue()
        
        self.tray_icon = None
        
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05  # Reduced pause for faster execution
        
        self.logger.info(f"Configured hotwords: {', '.join(self.hotwords)}")
        
    def _load_icon(self) -> Image.Image:
        try:
            if os.path.exists(self.icon_path):
                return Image.open(self.icon_path)
            else:
                self.logger.warning(f"Icon file {self.icon_path} not found, creating default icon")
                return self._create_default_icon()
        except Exception as e:
            self.logger.error(f"Failed to load icon: {e}")
            return self._create_default_icon()
    
    def _create_default_icon(self) -> Image.Image:
        img = Image.new('RGB', (64, 64), color='blue')
        return img
    
    def _calibrate_microphone(self) -> None:
        try:
            with sr.Microphone() as source:
                self.logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.logger.info(f"Energy threshold set to: {self.recognizer.energy_threshold}")
        except Exception as e:
            self.logger.error(f"Failed to calibrate microphone: {e}")
    
    def _get_window_process_name(self, hwnd: int) -> str:
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name().lower()
        except Exception:
            return ""
    
    def _is_chatgpt_window_open(self) -> bool:
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    process_name = self._get_window_process_name(hwnd)
                    if 'chatgpt' in process_name:
                        windows.append(hwnd)
                        return True
                    
                    class_name = win32gui.GetClassName(hwnd).lower()
                    if 'chatgpt' in class_name:
                        windows.append(hwnd)
                        return True
                    
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    
                    if (style & win32con.WS_POPUP) or (ex_style & win32con.WS_EX_TOOLWINDOW):
                        rect = win32gui.GetWindowRect(hwnd)
                        width = rect[2] - rect[0]
                        height = rect[3] - rect[1]
                        
                        if 400 <= width <= 1200 and 300 <= height <= 800:
                            window_text = win32gui.GetWindowText(hwnd)
                            if len(window_text) > 0:  # Has some title
                                windows.append(hwnd)
                                return True
                    
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        exe_path = process.exe().lower()
                        if 'chatgpt' in exe_path:
                            windows.append(hwnd)
                            return True
                    except Exception:
                        pass
                        
                except Exception:
                    pass
            
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            self.logger.info(f"ChatGPT window is already open (found {len(windows)} potential windows)")
            return True
        else:
            self.logger.info("ChatGPT window is not open")
            return False
    
    def _find_chatgpt_window(self) -> Optional[int]:
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    process_name = self._get_window_process_name(hwnd)
                    if 'chatgpt' in process_name:
                        windows.append((hwnd, f"Process: {process_name}", "ProcessMatch"))
                        return True
                    
                    class_name = win32gui.GetClassName(hwnd).lower()
                    if 'chatgpt' in class_name:
                        windows.append((hwnd, f"Class: {class_name}", "ClassMatch"))
                        return True
                    
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    
                    if (style & win32con.WS_POPUP) or (ex_style & win32con.WS_EX_TOOLWINDOW):
                        rect = win32gui.GetWindowRect(hwnd)
                        width = rect[2] - rect[0]
                        height = rect[3] - rect[1]
                        
                        if 400 <= width <= 1200 and 300 <= height <= 800:
                            window_text = win32gui.GetWindowText(hwnd)
                            if len(window_text) > 0:  # Has some title
                                windows.append((hwnd, f"Popup: {window_text}", "PopupMatch"))
                                return True
                    
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        exe_path = process.exe().lower()
                        if 'chatgpt' in exe_path:
                            windows.append((hwnd, f"Exe: {exe_path}", "ExeMatch"))
                            return True
                    except Exception:
                        pass
                        
                except Exception:
                    pass
            
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        for hwnd, description, match_type in windows:
            self.logger.debug(f"Found ChatGPT window: {description} ({match_type}) - HWND: {hwnd}")
        
        if windows:
            return windows[0][0]
        
        return None
    
    def _find_microphone_button_advanced(self) -> Optional[tuple]:
        try:
            chatgpt_hwnd = self._find_chatgpt_window()
            if chatgpt_hwnd:
                rect = win32gui.GetWindowRect(chatgpt_hwnd)
                left, top, right, bottom = rect
                
                self.logger.info(f"Found ChatGPT window at: {rect}")
                
                win32gui.SetForegroundWindow(chatgpt_hwnd)
                time.sleep(0.2)
                
                window_width = right - left
                window_height = bottom - top
                
                search_left = left + int(window_width * 0.6)  # Right 40% of window
                search_top = top + int(window_height * 0.8)   # Bottom 20% of window
                search_right = right - 10  # 10px margin from edge
                search_bottom = bottom - 20  # 20px margin from bottom
                
                potential_positions = [
                    (search_right - 30, search_bottom - 30),  # Bottom-right corner
                    (search_right - 40, search_bottom - 40),  # Slightly more inward
                    (search_right - 25, search_bottom - 35),  # Alternative position
                    (search_right - 35, search_bottom - 25),  # Another alternative
                ]
                
                return potential_positions[0]  # Return the most likely position
            
            screen_width, screen_height = pyautogui.size()
            
            fallback_positions = [
                (screen_width - 50, screen_height - 80),
                (screen_width - 60, screen_height - 90),
                (screen_width - 40, screen_height - 70),
                (screen_width - 70, screen_height - 100),
            ]
            
            return fallback_positions[0]
            
        except Exception as e:
            self.logger.error(f"Error in advanced button detection: {e}")
            return None
    
    def _click_microphone_button_retry(self) -> bool:
        for attempt in range(self.max_click_attempts):
            try:
                self.logger.info(f"Microphone button click attempt {attempt + 1}/{self.max_click_attempts}")
                
                if attempt > 0:
                    time.sleep(0.5 * attempt)  # Progressive delay
                
                button_pos = self._find_microphone_button_advanced()
                
                if button_pos:
                    x, y = button_pos
                    
                    screen_width, screen_height = pyautogui.size()
                    if 0 <= x <= screen_width and 0 <= y <= screen_height:
                        
                        pyautogui.moveTo(x, y, duration=0.1)
                        time.sleep(0.1)
                        
                        pyautogui.click(x, y)
                        
                        self.logger.info(f"Clicked microphone button at ({x}, {y}) on attempt {attempt + 1}")
                        
                        time.sleep(0.2)
                        return True
                    else:
                        self.logger.warning(f"Button position ({x}, {y}) is outside screen bounds")
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                
        self.logger.error("All microphone button click attempts failed")
        return False
    
    def _process_audio_worker(self) -> None:
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                if audio_data is None:
                    continue
                
                if self.listening:
                    threading.Thread(target=self._recognize_audio, args=(audio_data,), daemon=True).start()
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in audio processing worker: {e}")
    
    def _check_hotwords(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        
        for hotword in self.hotwords:
            if hotword in text_lower:
                return hotword
        
        return None
    
    def _recognize_audio(self, audio_data) -> None:
        try:
            text = self.recognizer.recognize_google(audio_data)
            self.logger.info(f"Recognized: {text}")
            
            detected_hotword = self._check_hotwords(text)
            if detected_hotword:
                self.last_detected_hotword = detected_hotword
                self.logger.info(f"Hotword '{detected_hotword}' detected! Triggering action...")
                self._trigger_action()
                
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            self.logger.error(f"Google Speech Recognition service error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during recognition: {e}")
    
    def _trigger_action(self) -> None:
        try:
            if self._is_chatgpt_window_open():
                self.logger.info("ChatGPT window is already open - skipping Alt+Space and going straight to button click")
                
                chatgpt_hwnd = self._find_chatgpt_window()
                if chatgpt_hwnd:
                    win32gui.SetForegroundWindow(chatgpt_hwnd)
                    time.sleep(0.3)  # Brief pause to ensure window is focused
                
                if self._click_microphone_button_retry():
                    self.logger.info(f"Microphone button clicked successfully for existing window - hotword: {self.last_detected_hotword}")
                else:
                    self.logger.warning("Failed to click microphone button on existing window")
            
            else:
                self.logger.info("ChatGPT window not open - opening new window")
                
                with self.keyboard.pressed(Key.alt):
                    self.keyboard.press(Key.space)
                    self.keyboard.release(Key.space)
                
                self.logger.info("Alt+Space triggered successfully")
                
                with self.keyboard.pressed(Key.ctrl_l):
                    self.keyboard.press('n')
                    self.keyboard.release('n')
                
                self.logger.info("New Chat triggered successfully")
                
                time.sleep(self.click_delay)
                
                if self._click_microphone_button_retry():
                    self.logger.info(f"Complete action sequence successful for hotword: {self.last_detected_hotword}")
                else:
                    self.logger.warning("Microphone button click failed, but Alt+Space was successful")
                
        except Exception as e:
            self.logger.error(f"Failed to trigger complete action: {e}")
    
    def _listen_continuously(self) -> None:
        try:
            with sr.Microphone() as source:
                while self.running:
                    try:
                        audio = self.recognizer.listen(
                            source, 
                            timeout=self.timeout, 
                            phrase_time_limit=self.phrase_time_limit
                        )
                        
                        if not self.audio_queue.full():
                            self.audio_queue.put(audio)
                        else:
                            self.logger.warning("Audio queue is full, dropping audio")
                            
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error during listening: {e}")
                        time.sleep(0.1)
                        
        except Exception as e:
            self.logger.error(f"Critical error in listening loop: {e}")
    
    def toggle_listening(self, icon=None, item=None) -> None:
        self.listening = not self.listening
        status = "enabled" if self.listening else "disabled"
        self.logger.info(f"Listening {status}")
        
        if self.tray_icon:
            self.tray_icon.update_menu()
    
    def test_button_click(self, icon=None, item=None) -> None:
        self.logger.info("Testing microphone button click...")
        if self._click_microphone_button_retry():
            self.logger.info("Test click successful!")
        else:
            self.logger.error("Test click failed!")
    
    def test_alt_space(self, icon=None, item=None) -> None:
        self.logger.info("Testing Alt+Space...")
        try:
            with self.keyboard.pressed(Key.alt):
                self.keyboard.press(Key.space)
                self.keyboard.release(Key.space)
            self.logger.info("Alt+Space test successful!")
        except Exception as e:
            self.logger.error(f"Alt+Space test failed: {e}")
    
    def test_window_detection(self, icon=None, item=None) -> None:
        self.logger.info("Testing ChatGPT window detection...")
        if self._is_chatgpt_window_open():
            self.logger.info("ChatGPT window detected as OPEN")
        else:
            self.logger.info("ChatGPT window detected as CLOSED")
    
    def show_hotwords(self, icon=None, item=None) -> None:
        self.logger.info(f"Configured hotwords: {', '.join(self.hotwords)}")
    
    def quit_application(self, icon=None, item=None) -> None:
        self.logger.info("Quitting application...")
        self.stop()
        if self.tray_icon:
            self.tray_icon.stop()
    
    def _create_tray_menu(self):
        return pystray.Menu(
            item(
                lambda text: f"{'✓' if self.listening else '✗'} Listening",
                self.toggle_listening,
                checked=lambda item: self.listening
            ),
            pystray.Menu.SEPARATOR,
            item("Test Alt+Space", self.test_alt_space),
            item("Test Button Click", self.test_button_click),
            item("Test Window Detection", self.test_window_detection),
            item("Show Hotwords", self.show_hotwords),
            pystray.Menu.SEPARATOR,
            item("Quit", self.quit_application)
        )
    
    def _setup_tray_icon(self) -> None:
        try:
            icon_image = self._load_icon()
            self.tray_icon = pystray.Icon(
                "chatgpt_desktop_plus",
                icon_image,
                "ChatGPT Desktop Plus",
                menu=self._create_tray_menu()
            )
            
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
            self.logger.info("System tray icon created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create tray icon: {e}")
    
    def add_hotword(self, hotword: str) -> None:
        hotword_lower = hotword.lower()
        if hotword_lower not in self.hotwords:
            self.hotwords.append(hotword_lower)
            self.logger.info(f"Added new hotword: {hotword}")
        else:
            self.logger.warning(f"Hotword '{hotword}' already exists")
    
    def remove_hotword(self, hotword: str) -> None:
        hotword_lower = hotword.lower()
        if hotword_lower in self.hotwords:
            self.hotwords.remove(hotword_lower)
            self.logger.info(f"Removed hotword: {hotword}")
        else:
            self.logger.warning(f"Hotword '{hotword}' not found")
    
    def start(self) -> None:
        if self.running:
            self.logger.warning("Detector is already running")
            return
            
        self.logger.info(f"Starting ChatGPT voice assistant...")
        self.logger.info(f"Monitoring hotwords: {', '.join(self.hotwords)}")
        self.running = True
        
        self._setup_tray_icon()
        self._calibrate_microphone()
        
        self.audio_worker = threading.Thread(target=self._process_audio_worker, daemon=True)
        self.audio_worker.start()
        
        self.listen_worker = threading.Thread(target=self._listen_continuously, daemon=True)
        self.listen_worker.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop()
    
    def stop(self) -> None:
        if not self.running:
            return
            
        self.logger.info("Stopping hotword detection...")
        self.running = False
        
        self.audio_queue.put(None)
        
        if hasattr(self, 'audio_worker'):
            self.audio_worker.join(timeout=2)
        if hasattr(self, 'listen_worker'):
            self.listen_worker.join(timeout=2)
        
        self.logger.info("Hotword detection stopped")

def main():
    custom_hotwords = [
        "hi chat", "hey chat", "hai chat",
        "hi gpt", "hey gpt", "hai gpt"
    ]
    
    detector = HotwordDetector(
        hotwords=custom_hotwords,
        timeout=1.0,
        phrase_time_limit=3.0,
        energy_threshold=300,
        dynamic_energy_threshold=True,
        icon_path="assets/icon.png",
        click_delay=1.0,  # Increased delay for popup windows
        max_click_attempts=3
    )
    
    try:
        detector.start()
    except Exception as e:
        logging.error(f"Failed to start detector: {e}")

if __name__ == "__main__":
    main()
