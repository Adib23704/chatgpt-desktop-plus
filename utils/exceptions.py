"""Custom exceptions for ChatGPT Desktop Plus."""

class VoiceAssistantError(Exception):
    """Base exception for voice assistant errors."""
    pass

class AudioProcessingError(VoiceAssistantError):
    """Exception raised for audio processing errors."""
    pass

class WindowDetectionError(VoiceAssistantError):
    """Exception raised for window detection errors."""
    pass

class HotwordDetectionError(VoiceAssistantError):
    """Exception raised for hotword detection errors."""
    pass

class UIError(VoiceAssistantError):
    """Exception raised for UI-related errors."""
    pass
