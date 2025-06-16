import speech_recognition as sr
import pyaudio
from pynput.keyboard import Key, Controller

def simple_hotword_detector():
  r = sr.Recognizer()
  keyboard = Controller()
  
  while True:
    try:
      with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source, timeout=1, phrase_time_limit=3)
      
      try:
        text = r.recognize_google(audio).lower()
        print(f"Heard: {text}")
        if "hey chat" in text:
          print("Hotword detected!")
          with keyboard.pressed(Key.alt):
            keyboard.press(Key.space)
            keyboard.release(Key.space)
      except:
        pass
    except sr.WaitTimeoutError:
      pass
    except KeyboardInterrupt:
      print("Stopping hotword detection...")
      break

if __name__ == "__main__":
  simple_hotword_detector()
        