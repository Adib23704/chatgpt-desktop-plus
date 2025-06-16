import speech_recognition as sr
import pyaudio
import threading
import time
import logging
from pynput.keyboard import Key, Controller
from typing import Optional
import queue

class HotwordDetector:
    def __init__(self, 
                 hotword: str = "hey chat", 
                 timeout: float = 1.0,
                 phrase_time_limit: float = 3.0,
                 energy_threshold: int = 300,
                 dynamic_energy_threshold: bool = True):

        self.hotword = hotword.lower()
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.running = False
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = dynamic_energy_threshold
        self.keyboard = Controller()
        
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.audio_queue = queue.Queue()
        
    def _calibrate_microphone(self) -> None:
        try:
            with sr.Microphone() as source:
                self.logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.logger.info(f"Energy threshold set to: {self.recognizer.energy_threshold}")
        except Exception as e:
            self.logger.error(f"Failed to calibrate microphone: {e}")
    
    def _process_audio_worker(self) -> None:
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                if audio_data is None:
                    continue
                    
                threading.Thread(target=self._recognize_audio, args=(audio_data,), daemon=True).start()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in audio processing worker: {e}")
    
    def _recognize_audio(self, audio_data) -> None:
        try:
            text = self.recognizer.recognize_google(audio_data).lower()
            self.logger.info(f"Recognized: {text}")
            
            if self.hotword in text:
                self.logger.info("Hotword detected! Triggering action...")
                self._trigger_action()
                
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            self.logger.error(f"Google Speech Recognition service error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during recognition: {e}")
    
    def _trigger_action(self) -> None:
        try:
            with self.keyboard.pressed(Key.alt):
                self.keyboard.press(Key.space)
                self.keyboard.release(Key.space)
            self.logger.info("Action triggered successfully")
        except Exception as e:
            self.logger.error(f"Failed to trigger action: {e}")
    
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
    
    def start(self) -> None:
        if self.running:
            self.logger.warning("Detector is already running")
            return
            
        self.logger.info(f"Starting hotword detection for: '{self.hotword}'")
        self.running = True
        
        self._calibrate_microphone()
        
        self.audio_worker = threading.Thread(target=self._process_audio_worker, daemon=True)
        self.audio_worker.start()
        
        try:
            self._listen_continuously()
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
        
        self.logger.info("Hotword detection stopped")

def main():
    detector = HotwordDetector(
        hotword="hey chat",
        timeout=1.0,
        phrase_time_limit=3.0,
        energy_threshold=300,
        dynamic_energy_threshold=True
    )
    
    try:
        detector.start()
    except Exception as e:
        logging.error(f"Failed to start detector: {e}")

if __name__ == "__main__":
    main()
