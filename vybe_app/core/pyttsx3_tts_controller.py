"""
PyTTSx3 TTS Controller for Vybe - Reliable offline text-to-speech
Uses pyttsx3 engine for cross-platform, offline TTS functionality.
"""

import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

from ..logger import logger


class PyTTSx3Controller:
    """Controller for managing pyttsx3 TTS functionality"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        # Use user data directory for output
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.output_dir = output_dir or user_data_dir / "workspace" / "tts_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.available = PYTTSX3_AVAILABLE
        self.engine = None
        self._lock = threading.Lock()
        
        if self.available:
            try:
                self._init_engine()
                logger.info("PyTTSx3 TTS Controller initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3 engine: {e}")
                self.available = False
        else:
            logger.warning("pyttsx3 not available - TTS functionality will be limited")
    
    def _init_engine(self):
        """Initialize the pyttsx3 engine with proper settings"""
        if not PYTTSX3_AVAILABLE or pyttsx3 is None:
            raise RuntimeError("pyttsx3 is not available")
            
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice settings
            voices = self.engine.getProperty('voices')
            if voices and hasattr(voices, '__len__') and hasattr(voices, '__iter__'):
                try:
                    if len(voices) > 0:  # type: ignore
                        # Prefer female voices or first available
                        for voice in voices:  # type: ignore
                            if hasattr(voice, 'name') and hasattr(voice, 'id'):
                                if 'female' in str(voice.name).lower() or 'aria' in str(voice.name).lower():
                                    self.engine.setProperty('voice', voice.id)
                                    break
                        else:
                            # Use first available voice
                            first_voice = list(voices)[0]  # type: ignore
                            if hasattr(first_voice, 'id'):
                                self.engine.setProperty('voice', first_voice.id)
                except (TypeError, AttributeError, IndexError):
                    # Fallback - just use default voice
                    pass
            
            # Set speech rate (words per minute)
            self.engine.setProperty('rate', 200)  # Normal speaking rate
            
            # Set volume (0.0 to 1.0)
            self.engine.setProperty('volume', 0.8)
            
        except Exception as e:
            logger.error(f"Error initializing pyttsx3 engine: {e}")
            raise
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices"""
        if not self.available or not self.engine:
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            voice_list = []
            
            if voices and hasattr(voices, '__iter__'):
                try:
                    for voice in voices:  # type: ignore
                        if hasattr(voice, 'id') and hasattr(voice, 'name'):
                            voice_info = {
                                'id': str(voice.id),
                                'name': str(voice.name),
                                'gender': 'Female' if 'female' in str(voice.name).lower() else 'Male',
                                'language': getattr(voice, 'languages', ['en-US'])[0] if hasattr(voice, 'languages') else 'en-US'
                            }
                            voice_list.append(voice_info)
                except (TypeError, AttributeError):
                    # Fallback if voice iteration fails
                    pass
            
            return voice_list
            
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return []
    
    def get_available_voices_sync(self) -> List[Dict[str, Any]]:
        """Synchronous version of get_available_voices for API compatibility"""
        return self.get_available_voices()
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """Alias for get_available_voices for API compatibility"""
        return self.get_available_voices()
    
    def synthesize_speech(self, text: str, voice_id: Optional[str] = None, 
                         rate: int = 200, volume: float = 0.8) -> Optional[str]:
        """
        Synthesize speech from text and save to file
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use (optional)
            rate: Speech rate in words per minute
            volume: Volume level (0.0 to 1.0)
            
        Returns:
            Path to generated audio file or None if failed
        """
        if not self.available or not self.engine:
            logger.error("pyttsx3 TTS not available")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return None
        
        with self._lock:
            try:
                # Create output file
                output_file = self.output_dir / f"tts_{hash(text) % 1000000}.wav"
                
                # Configure engine
                if voice_id:
                    self.engine.setProperty('voice', voice_id)
                
                self.engine.setProperty('rate', rate)
                self.engine.setProperty('volume', volume)
                
                # Save to file
                self.engine.save_to_file(text, str(output_file))
                self.engine.runAndWait()
                
                if output_file.exists():
                    logger.info(f"TTS audio saved to: {output_file}")
                    return str(output_file)
                else:
                    logger.error("TTS file was not created")
                    return None
                    
            except Exception as e:
                logger.error(f"Error synthesizing speech: {e}")
                return None
    
    def speak_text(self, text: str, voice_id: Optional[str] = None, 
                   rate: int = 200, volume: float = 0.8) -> bool:
        """
        Speak text directly (no file output)
        
        Args:
            text: Text to speak
            voice_id: Voice ID to use (optional)
            rate: Speech rate in words per minute
            volume: Volume level (0.0 to 1.0)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available or not self.engine:
            logger.error("pyttsx3 TTS not available")
            return False
        
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return False
        
        with self._lock:
            try:
                # Configure engine
                if voice_id:
                    self.engine.setProperty('voice', voice_id)
                
                self.engine.setProperty('rate', rate)
                self.engine.setProperty('volume', volume)
                
                # Speak the text
                self.engine.say(text)
                self.engine.runAndWait()
                
                return True
                
            except Exception as e:
                logger.error(f"Error speaking text: {e}")
                return False
    
    def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific voice"""
        voices = self.get_available_voices()
        for voice in voices:
            if voice['id'] == voice_id:
                return voice
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the TTS controller"""
        return {
            "available": self.available,
            "engine_ready": self.engine is not None,
            "voices_count": len(self.get_available_voices()),
            "output_directory": str(self.output_dir),
            "pyttsx3_available": PYTTSX3_AVAILABLE
        }
    
    def start(self) -> tuple[bool, str]:
        """Start the TTS service - for pyttsx3 this means initializing the engine"""
        try:
            if not self.available:
                return False, "PyTTSx3 is not available"
            
            if self.engine is None:
                self._init_engine()
            
            return True, "PyTTSx3 TTS service is ready"
        except Exception as e:
            logger.error(f"Failed to start TTS service: {e}")
            return False, f"Failed to start TTS: {str(e)}"
    
    def stop(self) -> tuple[bool, str]:
        """Stop the TTS service"""
        try:
            self.cleanup()
            return True, "PyTTSx3 TTS service stopped"
        except Exception as e:
            logger.error(f"Failed to stop TTS service: {e}")
            return False, f"Failed to stop TTS: {str(e)}"
    
    def test_tts(self) -> bool:
        """Test TTS functionality"""
        try:
            return self.speak_text("TTS test successful")
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                logger.debug(f"Engine stop failed during cleanup: {e}")
                pass
            self.engine = None
    
    def start_tts(self) -> bool:
        """Start TTS service (placeholder for compatibility)"""
        logger.info("PyTTSx3 service started")
        return True
    
    def stop_tts(self) -> bool:
        """Stop TTS service (placeholder for compatibility)"""
        logger.info("PyTTSx3 service stopped")
        return True
    
    def get_tts_status(self) -> Dict[str, Any]:
        """Get TTS service status (placeholder for compatibility)"""
        return {
            'running': self.available,
            'controller': 'PyTTSx3',
            'voices_available': len(self.get_available_voices_sync()) if self.available else 0
        }


# Global instance
_tts_controller = None


def get_pyttsx3_controller() -> PyTTSx3Controller:
    """Get or create the global PyTTSx3 TTS controller"""
    global _tts_controller
    if _tts_controller is None:
        _tts_controller = PyTTSx3Controller()
    return _tts_controller


def test_tts_functionality() -> bool:
    """Test if TTS is working properly"""
    controller = get_pyttsx3_controller()
    return controller.test_tts() if controller.available else False
