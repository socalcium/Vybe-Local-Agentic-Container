"""
Custom TTS Engine for Vybe
A self-contained text-to-speech solution that can replace external dependencies
"""

import os
import json
import time
import threading
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from ..logger import log_info, log_warning, log_error

# Optional TTS library availability flags
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    log_warning("pyttsx3 not available - system TTS features disabled")

try:
    import subprocess
    SUBPROCESS_AVAILABLE = True
except ImportError:
    SUBPROCESS_AVAILABLE = False
    log_warning("subprocess not available - espeak features disabled")

logger = logging.getLogger(__name__)

@dataclass
class VoiceInfo:
    """Voice information structure"""
    id: str
    name: str
    language: str
    gender: str
    age: str
    quality: str
    sample_rate: int = 22050
    bit_depth: int = 16
    channels: int = 1
    mobile_compatible: bool = True
    api_endpoint: Optional[str] = None
    streaming_support: bool = False

class CustomTTSEngine:
    """
    Custom TTS Engine that provides a reliable alternative to external TTS services
    """
    
    def __init__(self):
        self.voices = self._initialize_voices()
        self.current_voice = self.voices[0] if self.voices else None
        self.is_initialized = False
        self._audio_cache = {}
        self._cache_size_limit = 100
        self.mobile_api_enabled = False
        self.mobile_api_url = None
        self.streaming_enabled = False
        
    def _initialize_voices(self) -> List[VoiceInfo]:
        """Initialize available voices"""
        voices = [
            VoiceInfo(
                id="en-us-default",
                name="English (US) - Default",
                language="en-US",
                gender="neutral",
                age="adult",
                quality="standard"
            ),
            VoiceInfo(
                id="en-us-male",
                name="English (US) - Male",
                language="en-US",
                gender="male",
                age="adult",
                quality="standard"
            ),
            VoiceInfo(
                id="en-us-female",
                name="English (US) - Female",
                language="en-US",
                gender="female",
                age="adult",
                quality="standard"
            ),
            VoiceInfo(
                id="en-gb-default",
                name="English (UK) - Default",
                language="en-GB",
                gender="neutral",
                age="adult",
                quality="standard"
            ),
            VoiceInfo(
                id="en-gb-male",
                name="English (UK) - Male",
                language="en-GB",
                gender="male",
                age="adult",
                quality="standard"
            ),
            VoiceInfo(
                id="en-gb-female",
                name="English (UK) - Female",
                language="en-GB",
                gender="female",
                age="adult",
                quality="standard"
            ),
            VoiceInfo(
                id="system-default",
                name="System Default",
                language="en-US",
                gender="neutral",
                age="adult",
                quality="system"
            )
        ]
        
        # Try to detect system voices
        try:
            system_voices = self._detect_system_voices()
            if system_voices:
                voices.extend(system_voices)
        except Exception as e:
            log_warning(f"Failed to detect system voices: {e}")
        
        return voices
    
    def _detect_system_voices(self) -> List[VoiceInfo]:
        """Detect system voices using available methods"""
        system_voices = []
        
        # Try pyttsx3 if available
        if PYTTSX3_AVAILABLE:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                
                # Safely handle voices object with proper type checking
                if voices:
                    try:
                        # Try to check if it's list-like and iterable
                        if hasattr(voices, '__len__') and hasattr(voices, '__getitem__'):
                            for i in range(len(voices)):  # type: ignore
                                try:
                                    voice = voices[i]  # type: ignore
                                    voice_info = VoiceInfo(
                                        id=f"system-{i}",
                                        name=getattr(voice, 'name', f'System Voice {i}'),
                                        language=getattr(voice, 'languages', ['en-US'])[0] if hasattr(voice, 'languages') else 'en-US',
                                        gender=getattr(voice, 'gender', 'neutral'),
                                        age='adult',
                                        quality='system'
                                    )
                                    system_voices.append(voice_info)
                                except Exception as e:
                                    log_warning(f"Failed to process system voice {i}: {e}")
                                    continue
                    except Exception as e:
                        log_warning(f"Failed to iterate through voices: {e}")
                        
            except ImportError:
                log_info("pyttsx3 not available for system voice detection")
            except Exception as e:
                log_warning(f"Failed to detect system voices with pyttsx3: {e}")
        else:
            log_info("pyttsx3 not available - system voice detection skipped")
        
        return system_voices
    
    def initialize(self) -> bool:
        """Initialize the TTS engine"""
        try:
            # Create output directory
            output_dir = Path(__file__).parent.parent.parent / "workspace" / "generated_audio"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.output_dir = output_dir
            self.is_initialized = True
            
            log_info("Custom TTS Engine initialized successfully")
            return True
            
        except Exception as e:
            log_error(f"Failed to initialize Custom TTS Engine: {e}")
            return False
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available voices"""
        try:
            voices_data = []
            for voice in self.voices:
                voices_data.append({
                    'id': voice.id,
                    'name': voice.name,
                    'language': voice.language,
                    'gender': voice.gender,
                    'age': voice.age,
                    'quality': voice.quality,
                    'sample_rate': voice.sample_rate,
                    'bit_depth': voice.bit_depth,
                    'channels': voice.channels
                })
            
            return {
                'success': True,
                'voices': voices_data,
                'default_voice': self.voices[0].id if self.voices else None,
                'total_count': len(voices_data),
                'message': f'Found {len(voices_data)} available voices'
            }
            
        except Exception as e:
            log_error(f"Error getting available voices: {e}")
            return {
                'success': False,
                'voices': [],
                'default_voice': None,
                'error': f'Failed to get voices: {str(e)}'
            }
    
    def synthesize_speech(self, text: str, voice_id: Optional[str] = None, speed: float = 1.0) -> Tuple[bool, str, Optional[bytes]]:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            speed: Speech speed (0.5 to 2.0)
            
        Returns:
            Tuple of (success, message, audio_data)
        """
        try:
            if not self.is_initialized:
                success = self.initialize()
                if not success:
                    return False, "TTS engine not initialized", None
            
            # Validate input
            if not text or not text.strip():
                return False, "No text provided", None
            
            # Normalize speed
            speed = max(0.5, min(2.0, speed))
            
            # Select voice
            voice = self._get_voice(voice_id)
            if not voice:
                return False, f"Voice not found: {voice_id}", None
            
            # Check cache first
            cache_key = f"{text}_{voice_id}_{speed}"
            if cache_key in self._audio_cache:
                log_info("Using cached audio")
                return True, "Success", self._audio_cache[cache_key]
            
            # Generate audio using available methods
            audio_data = self._generate_audio(text, voice, speed)
            
            if audio_data:
                # Cache the result
                self._cache_audio(cache_key, audio_data)
                return True, "Success", audio_data
            else:
                return False, "Failed to generate audio", None
                
        except Exception as e:
            log_error(f"Error in synthesize_speech: {e}")
            return False, f"TTS error: {str(e)}", None
    
    def _get_voice(self, voice_id: Optional[str] = None) -> Optional[VoiceInfo]:
        """Get voice by ID or return default"""
        if not voice_id:
            return self.current_voice or (self.voices[0] if self.voices else None)
        
        for voice in self.voices:
            if voice.id == voice_id:
                return voice
        
        return None
    
    def _generate_audio(self, text: str, voice: VoiceInfo, speed: float) -> Optional[bytes]:
        """Generate audio using available methods"""
        
        # Method 1: Try system TTS (pyttsx3)
        if voice.quality == 'system' or 'system' in voice.id:
            audio_data = self._generate_with_system_tts(text, voice, speed)
            if audio_data:
                return audio_data
        
        # Method 2: Try espeak-ng if available
        audio_data = self._generate_with_espeak(text, voice, speed)
        if audio_data:
            return audio_data
        
        # Method 3: Generate simple beep pattern (fallback)
        log_warning("Using fallback audio generation")
        return self._generate_fallback_audio(text, voice, speed)
    
    def _generate_with_system_tts(self, text: str, voice: VoiceInfo, speed: float) -> Optional[bytes]:
        """Generate audio using system TTS (pyttsx3)"""
        if not PYTTSX3_AVAILABLE:
            log_warning("pyttsx3 not available for system TTS")
            return None
            
        try:
            import pyttsx3
            import tempfile
            
            engine = pyttsx3.init()
            
            # Set voice if possible
            voices = engine.getProperty('voices')
            if voices and 'system' in voice.id:
                try:
                    voice_index = int(voice.id.split('-')[-1])
                    # Try to access voice directly with proper error handling
                    if hasattr(voices, '__getitem__') and hasattr(voices, '__len__'):
                        if voice_index < len(voices):  # type: ignore
                            engine.setProperty('voice', voices[voice_index].id)  # type: ignore
                except (ValueError, IndexError, AttributeError, TypeError):
                    # Fallback: try to set voice by index if possible
                    pass
            
            # Set properties
            engine.setProperty('rate', int(200 * speed))  # Default rate is 200
            engine.setProperty('volume', 0.9)
            
            # Generate temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Synthesize to file
            engine.save_to_file(text, temp_path)
            engine.runAndWait()
            
            # Read the generated audio
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                os.unlink(temp_path)  # Clean up
                return audio_data
            
        except ImportError:
            log_info("pyttsx3 not available for system TTS")
        except Exception as e:
            log_warning(f"Failed to generate audio with system TTS: {e}")
        
        return None
    
    def _generate_with_espeak(self, text: str, voice: VoiceInfo, speed: float) -> Optional[bytes]:
        """Generate audio using espeak-ng"""
        if not SUBPROCESS_AVAILABLE:
            log_warning("subprocess not available for espeak")
            return None
            
        try:
            import subprocess
            import tempfile
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Build espeak command
            cmd = [
                'espeak-ng',
                '-w', temp_path,
                '-s', str(int(150 * speed)),  # Speed (default 150)
                '-p', '50',  # Pitch (0-99)
                '-a', '100',  # Amplitude (0-200)
                '-v', self._get_espeak_voice(voice),
                text
            ]
            
            # Run espeak
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                os.unlink(temp_path)  # Clean up
                return audio_data
            else:
                log_warning(f"espeak failed: {result.stderr}")
                
        except FileNotFoundError:
            log_info("espeak-ng not available")
        except Exception as e:
            log_warning(f"Failed to generate audio with espeak: {e}")
        
        return None
    
    def _get_espeak_voice(self, voice: VoiceInfo) -> str:
        """Get espeak voice parameter"""
        if 'en-us' in voice.id:
            if 'male' in voice.id:
                return 'en-us+m3'
            elif 'female' in voice.id:
                return 'en-us+f2'
            else:
                return 'en-us'
        elif 'en-gb' in voice.id:
            if 'male' in voice.id:
                return 'en-gb+m3'
            elif 'female' in voice.id:
                return 'en-gb+f2'
            else:
                return 'en-gb'
        else:
            return 'en-us'
    
    def _generate_fallback_audio(self, text: str, voice: VoiceInfo, speed: float) -> bytes:
        """Generate simple fallback audio (beep pattern)"""
        try:
            import wave
            import struct
            import math
            import tempfile
            
            # Create a simple beep pattern
            sample_rate = voice.sample_rate
            duration = len(text) * 0.1 * speed  # Rough duration estimate
            frequency = 440  # A4 note
            
            # Generate sine wave
            num_samples = int(sample_rate * duration)
            audio_data = []
            
            for i in range(num_samples):
                sample = math.sin(2 * math.pi * frequency * i / sample_rate)
                # Convert to 16-bit PCM
                audio_data.append(struct.pack('<h', int(sample * 32767)))
            
            # Create WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(voice.channels)
                wav_file.setsampwidth(voice.bit_depth // 8)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b''.join(audio_data))
            
            # Read the generated audio
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(temp_path)  # Clean up
            return audio_data
            
        except Exception as e:
            log_error(f"Failed to generate fallback audio: {e}")
            # Return empty audio data
            return b''
    
    def _cache_audio(self, key: str, audio_data: bytes):
        """Cache audio data with size limit"""
        self._audio_cache[key] = audio_data
        
        # Limit cache size
        if len(self._audio_cache) > self._cache_size_limit:
            # Remove oldest entry
            oldest_key = next(iter(self._audio_cache))
            del self._audio_cache[oldest_key]
    
    def get_status(self) -> Dict[str, Any]:
        """Get TTS engine status"""
        return {
            'initialized': self.is_initialized,
            'available_voices': len(self.voices),
            'current_voice': self.current_voice.id if self.current_voice else None,
            'cache_size': len(self._audio_cache),
            'cache_limit': self._cache_size_limit,
            'engine_type': 'custom',
            'mobile_api_enabled': self.mobile_api_enabled,
            'streaming_enabled': self.streaming_enabled
        }
    
    # Mobile Companion App Integration Methods
    def enable_mobile_api(self, api_url: str, streaming: bool = False):
        """Enable mobile companion app API integration"""
        self.mobile_api_enabled = True
        self.mobile_api_url = api_url
        self.streaming_enabled = streaming
        log_info(f"Mobile API enabled: {api_url}, Streaming: {streaming}")
    
    def disable_mobile_api(self):
        """Disable mobile companion app API integration"""
        self.mobile_api_enabled = False
        self.mobile_api_url = None
        self.streaming_enabled = False
        log_info("Mobile API disabled")
    
    def speak_text_mobile(self, text: str, voice_id: Optional[str] = None, speed: float = 1.0) -> Dict[str, Any]:
        """Send TTS request to mobile companion app"""
        if not self.mobile_api_enabled or not self.mobile_api_url:
            return {'success': False, 'error': 'Mobile API not enabled'}
        
        try:
            import requests
            
            payload = {
                'text': text,
                'voice_id': voice_id or (self.current_voice.id if self.current_voice else 'en-us-default'),
                'speed': speed,
                'streaming': self.streaming_enabled
            }
            
            response = requests.post(
                f"{self.mobile_api_url}/tts/speak",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'success': False, 'error': f'Mobile API error: {response.status_code}'}
                
        except Exception as e:
            log_error(f"Mobile TTS API error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_mobile_voices(self) -> List[Dict[str, Any]]:
        """Get available voices from mobile companion app"""
        if not self.mobile_api_enabled or not self.mobile_api_url:
            return []
        
        try:
            import requests
            
            response = requests.get(
                f"{self.mobile_api_url}/tts/voices",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json().get('voices', [])
            else:
                return []
                
        except Exception as e:
            log_error(f"Failed to get mobile voices: {e}")
            return []
    
    def stream_audio_mobile(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """Stream audio from mobile companion app"""
        if not self.mobile_api_enabled or not self.streaming_enabled:
            return None
        
        try:
            import requests
            
            payload = {
                'text': text,
                'voice_id': voice_id or (self.current_voice.id if self.current_voice else 'en-us-default'),
                'stream': True
            }
            
            response = requests.post(
                f"{self.mobile_api_url}/tts/stream",
                json=payload,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                audio_data = b''
                for chunk in response.iter_content(chunk_size=1024):
                    audio_data += chunk
                return audio_data
            else:
                return None
                
        except Exception as e:
            log_error(f"Mobile streaming error: {e}")
            return None
    
    def start_tts(self) -> bool:
        """Start TTS service (placeholder for compatibility)"""
        self.initialize()
        return True
    
    def stop_tts(self) -> bool:
        """Stop TTS service (placeholder for compatibility)"""
        return True
    
    def get_tts_status(self) -> Dict[str, Any]:
        """Get TTS service status (placeholder for compatibility)"""
        return {
            'running': self.is_initialized,
            'controller': 'CustomTTS',
            'voices_available': len(self.voices)
        }


# Global instance
custom_tts_engine = CustomTTSEngine()
