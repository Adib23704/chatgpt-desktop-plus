"""Speech recognition Audio processing module for ChatGPT Desktop Plus."""

import speech_recognition as sr
import threading
import queue
from typing import Optional, Callable
from utils.logger import get_logger
from utils.exceptions import AudioProcessingError
from config.settings import settings

class AudioProcessor:
    """Handles audio capture and speech recognition."""
    
    def __init__(self, on_speech_detected: Callable[[str], None]):
        self.logger = get_logger(__name__)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = settings.audio.energy_threshold
        self.recognizer.dynamic_energy_threshold = settings.audio.dynamic_energy_threshold
        
        self.audio_queue = queue.Queue()
        self.running = False
        self.on_speech_detected = on_speech_detected
        
        self.audio_worker = None
        self.listen_worker = None
    
    def calibrate_microphone(self) -> None:
        """Calibrate microphone for ambient noise."""
        try:
            with sr.Microphone() as source:
                self.logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.logger.info(f"Energy threshold set to: {self.recognizer.energy_threshold}")
        except Exception as e:
            raise AudioProcessingError(f"Failed to calibrate microphone: {e}")
    
    def _process_audio_worker(self) -> None:
        """Worker thread for processing audio from queue."""
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                if audio_data is None:
                    continue
                
                threading.Thread(
                    target=self._recognize_audio, 
                    args=(audio_data,), 
                    daemon=True
                ).start()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in audio processing worker: {e}")
    
    def _recognize_audio(self, audio_data) -> None:
        """Recognize speech from audio data."""
        try:
            text = self.recognizer.recognize_google(audio_data)
            self.logger.info(f"Recognized: {text}")
            self.on_speech_detected(text)
            
        except sr.UnknownValueError:
            pass  # Speech was unintelligible
        except sr.RequestError as e:
            self.logger.error(f"Google Speech Recognition service error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during recognition: {e}")
    
    def _listen_continuously(self) -> None:
        """Main listening loop."""
        try:
            with sr.Microphone() as source:
                while self.running:
                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=settings.audio.timeout,
                            phrase_time_limit=settings.audio.phrase_time_limit
                        )
                        
                        if not self.audio_queue.full():
                            self.audio_queue.put(audio)
                        else:
                            self.logger.warning("Audio queue is full, dropping audio")
                            
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error during listening: {e}")
                        
        except Exception as e:
            raise AudioProcessingError(f"Critical error in listening loop: {e}")
    
    def start(self) -> None:
        """Start audio processing."""
        if self.running:
            self.logger.warning("Audio processor is already running")
            return
        
        self.logger.info("Starting audio processor...")
        self.running = True
        
        self.calibrate_microphone()
        
        self.audio_worker = threading.Thread(target=self._process_audio_worker, daemon=True)
        self.audio_worker.start()
        
        self.listen_worker = threading.Thread(target=self._listen_continuously, daemon=True)
        self.listen_worker.start()
    
    def stop(self) -> None:
        """Stop audio processing."""
        if not self.running:
            return
        
        self.logger.info("Stopping audio processor...")
        self.running = False
        
        self.audio_queue.put(None)
        
        if self.audio_worker:
            self.audio_worker.join(timeout=2)
        if self.listen_worker:
            self.listen_worker.join(timeout=2)
        
        self.logger.info("Audio processor stopped")
