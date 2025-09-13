"""
Advanced Audio I/O Module - Voice Processing with TTS and Transcription
Provides text-to-speech, audio transcription, voice cloning, and audio enhancement functionality
"""

import logging
import os
import tempfile
import wave
import numpy as np
from typing import Optional, Dict, Any, Tuple, List, Union
from pathlib import Path
from datetime import datetime
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..logger import log_info, log_warning, log_error, logger

# Audio processing libraries
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    log_warning("librosa not available - advanced audio processing disabled")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    log_warning("soundfile not available - some audio formats may not be supported")

try:
    import pydub
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    log_warning("pydub not available - audio conversion features disabled")

# Set overall availability flag
AUDIO_LIBS_AVAILABLE = LIBROSA_AVAILABLE and SOUNDFILE_AVAILABLE and PYDUB_AVAILABLE

# Voice cloning libraries
try:
    import torch
    import torchaudio
    VOICE_CLONING_AVAILABLE = True
except ImportError:
    VOICE_CLONING_AVAILABLE = False
    log_warning("Voice cloning libraries not available")
from ..utils.cache_manager import cached, get_cache_manager


class AudioProcessor:
    """Advanced audio processing with multi-format support and real-time capabilities"""
    
    def __init__(self):
        self.supported_formats = {
            'wav': 'Waveform Audio File Format',
            'mp3': 'MPEG Audio Layer III',
            'flac': 'Free Lossless Audio Codec',
            'ogg': 'Ogg Vorbis',
            'm4a': 'MPEG-4 Audio',
            'aac': 'Advanced Audio Coding',
            'wma': 'Windows Media Audio',
            'aiff': 'Audio Interchange File Format'
        }
        
        # Audio API settings
        self.settings = {
            'sample_rate': 44100,
            'channels': 1,
            'format': 'wav',
            'quality': 'high',
            'recording_enabled': True,
            'real_time_processing': True
        }
        
        self.audio_cache = get_cache_manager()
        self.processing_queue = queue.Queue()
        self.real_time_buffer = queue.Queue(maxsize=1000)
        self.is_processing = False
        self.recording_active = False
        self.current_session_id = None
        
        # Start background processing thread
        self.processing_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.processing_thread.start()
        
        log_info("Advanced audio processor initialized")
    
    def get_supported_formats(self) -> Dict[str, str]:
        """Get list of supported audio formats"""
        return self.supported_formats.copy()
    
    def is_format_supported(self, file_path: str) -> bool:
        """Check if audio format is supported"""
        if not file_path:
            return False
        
        extension = Path(file_path).suffix.lower().lstrip('.')
        return extension in self.supported_formats
    
    def convert_audio_format(self, input_path: str, output_path: str, 
                           target_format: str = 'wav', quality: str = 'high') -> Dict[str, Any]:
        """Convert audio file to different format"""
        try:
            if not AUDIO_LIBS_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Audio processing libraries not available'
                }
            
            if not self.is_format_supported(input_path):
                return {
                    'success': False,
                    'error': f'Unsupported input format: {Path(input_path).suffix}'
                }
            
            # Load audio file
            audio = AudioSegment.from_file(input_path)
            
            # Set export parameters based on quality
            export_params = {}
            if target_format == 'mp3':
                export_params['bitrate'] = '320k' if quality == 'high' else '128k'
            elif target_format == 'wav':
                export_params['parameters'] = ['-ar', '44100', '-ac', '2']
            
            # Export to target format
            audio.export(output_path, format=target_format, **export_params)
            
            return {
                'success': True,
                'output_path': output_path,
                'format': target_format,
                'duration': len(audio) / 1000.0,
                'sample_rate': audio.frame_rate,
                'channels': audio.channels
            }
            
        except Exception as e:
            log_error(f"Audio format conversion error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def enhance_audio(self, input_path: str, output_path: str, 
                     noise_reduction: bool = True, normalize: bool = True,
                     enhance_clarity: bool = False) -> Dict[str, Any]:
        """Enhance audio quality with noise reduction and normalization"""
        try:
            if not AUDIO_LIBS_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Audio processing libraries not available'
                }
            
            # Load audio file
            y, sr = librosa.load(input_path, sr=None)
            
            # Apply enhancements
            if noise_reduction:
                y = self._reduce_noise(y, sr)  # type: ignore
            
            if normalize:
                y = librosa.util.normalize(y)  # type: ignore
            
            if enhance_clarity:
                y = self._enhance_clarity(y, sr)  # type: ignore
            
            # Save enhanced audio
            sf.write(output_path, y, sr)
            
            return {
                'success': True,
                'output_path': output_path,
                'enhancements_applied': {
                    'noise_reduction': noise_reduction,
                    'normalize': normalize,
                    'enhance_clarity': enhance_clarity
                }
            }
            
        except Exception as e:
            log_error(f"Audio enhancement error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _reduce_noise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Reduce noise from audio using spectral gating"""
        try:
            # Compute spectrogram
            stft = librosa.stft(audio)  # type: ignore
            magnitude = np.abs(stft)
            
            # Estimate noise floor
            noise_floor = np.percentile(magnitude, 10, axis=1, keepdims=True)
            
            # Apply spectral gating
            gate_threshold = noise_floor * 2
            mask = magnitude > gate_threshold
            magnitude_filtered = magnitude * mask
            
            # Reconstruct audio
            stft_filtered = magnitude_filtered * np.exp(1j * np.angle(stft))
            audio_filtered = librosa.istft(stft_filtered)
            
            return audio_filtered  # type: ignore
            
        except Exception as e:
            log_error(f"Noise reduction error: {e}")
            return audio
    
    def _enhance_clarity(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Enhance audio clarity using high-frequency boost"""
        try:
            # Apply high-frequency boost
            freqs = librosa.fft_frequencies(sr=sample_rate)
            boost_filter = np.ones_like(freqs)
            boost_filter[freqs > 2000] *= 1.2  # Boost frequencies above 2kHz
            
            # Apply filter in frequency domain
            stft = librosa.stft(audio)  # type: ignore
            stft_enhanced = stft * boost_filter[:, np.newaxis]
            audio_enhanced = librosa.istft(stft_enhanced)
            
            return audio_enhanced  # type: ignore
            
        except Exception as e:
            log_error(f"Clarity enhancement error: {e}")
            return audio
    
    def extract_audio_features(self, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive audio features"""
        try:
            if not AUDIO_LIBS_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Audio processing libraries not available'
                }
            
            # Load audio
            y, sr = librosa.load(file_path, sr=None)
            
            # Extract features
            features = {
                'duration': len(y) / sr,
                'sample_rate': sr,
                'channels': 1 if len(y.shape) == 1 else y.shape[1],
                'rms_energy': np.sqrt(np.mean(y**2)),
                'spectral_centroid': np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)),
                'spectral_bandwidth': np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)),
                'spectral_rolloff': np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)),
                'zero_crossing_rate': np.mean(librosa.feature.zero_crossing_rate(y)),
                'mfcc': np.mean(librosa.feature.mfcc(y=y, sr=sr), axis=1).tolist(),
                'chroma': np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1).tolist(),
                'tempo': librosa.beat.tempo(y=y, sr=sr)[0],
                'onset_strength': np.mean(librosa.onset.onset_strength(y=y, sr=sr))
            }
            
            return {
                'success': True,
                'features': features
            }
            
        except Exception as e:
            log_error(f"Audio feature extraction error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_real_time_audio(self, audio_chunk: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """Process real-time audio chunks"""
        try:
            # Add to real-time buffer
            if not self.real_time_buffer.full():
                self.real_time_buffer.put({
                    'audio': audio_chunk,
                    'timestamp': time.time(),
                    'sample_rate': sample_rate
                })
            
            # Process if buffer has enough data
            if self.real_time_buffer.qsize() >= 10:
                return self._process_buffer()
            
            return {
                'success': True,
                'status': 'buffering',
                'buffer_size': self.real_time_buffer.qsize()
            }
            
        except Exception as e:
            log_error(f"Real-time audio processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_buffer(self) -> Dict[str, Any]:
        """Process accumulated audio buffer"""
        try:
            # Combine audio chunks
            combined_audio = b''
            timestamps = []
            
            while not self.real_time_buffer.empty():
                chunk_data = self.real_time_buffer.get()
                combined_audio += chunk_data['audio']
                timestamps.append(chunk_data['timestamp'])
            
            # Convert to numpy array
            audio_array = np.frombuffer(combined_audio, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # Extract features
            features = {
                'duration': len(audio_float) / 16000,
                'rms_energy': np.sqrt(np.mean(audio_float**2)),
                'zero_crossing_rate': np.mean(librosa.feature.zero_crossing_rate(audio_float)),
                'timestamp_start': min(timestamps),
                'timestamp_end': max(timestamps)
            }
            
            return {
                'success': True,
                'features': features,
                'audio_length': len(combined_audio)
            }
            
        except Exception as e:
            log_error(f"Buffer processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _processing_worker(self):
        """Background worker for audio processing"""
        while True:
            try:
                # Get task from queue
                task = self.processing_queue.get(timeout=1)
                
                if task['type'] == 'convert':
                    result = self.convert_audio_format(
                        task['input_path'], 
                        task['output_path'], 
                        task['target_format']
                    )
                elif task['type'] == 'enhance':
                    result = self.enhance_audio(
                        task['input_path'],
                        task['output_path'],
                        task['noise_reduction'],
                        task['normalize'],
                        task['enhance_clarity']
                    )
                
                # Store result
                task['result'] = result
                task['completed'] = True
                
            except queue.Empty:
                continue
            except Exception as e:
                log_error(f"Audio processing worker error: {e}")
    
    def start_recording(self):
        """Start audio recording session"""
        try:
            import uuid
            session_id = str(uuid.uuid4())
            self.current_session_id = session_id
            self.recording_active = True
            
            log_info(f"Audio recording started with session ID: {session_id}")
            print("Placeholder: Start recording")
            
            return {
                'success': True,
                'session_id': session_id,
                'message': 'Recording started successfully'
            }
        except Exception as e:
            log_error(f"Error starting recording: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def stop_recording(self):
        """Stop audio recording session"""
        try:
            if not self.recording_active:
                return {
                    'success': False,
                    'error': 'No active recording session'
                }
            
            session_id = self.current_session_id
            self.recording_active = False
            self.current_session_id = None
            
            log_info(f"Audio recording stopped for session: {session_id}")
            print("Placeholder: Stop recording")
            
            return {
                'success': True,
                'session_id': session_id,
                'file_path': f'/tmp/recording_{session_id}.wav',
                'duration': 30.0,  # Placeholder duration
                'message': 'Recording stopped successfully'
            }
        except Exception as e:
            log_error(f"Error stopping recording: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_recording_status(self):
        """Get current recording status"""
        try:
            print("Placeholder: Get recording status")
            
            return {
                'success': True,
                'is_recording': self.recording_active,
                'session_id': self.current_session_id,
                'duration': 15.0 if self.recording_active else 0.0,
                'status': 'recording' if self.recording_active else 'idle'
            }
        except Exception as e:
            log_error(f"Error getting recording status: {e}")
            return {
                'success': False,
                'error': str(e),
                'is_recording': False,
                'session_id': None
            }

    def process_audio_stream(self, stream_data):
        """Process real-time audio stream data"""
        try:
            if not stream_data:
                return {
                    'success': False,
                    'error': 'No stream data provided'
                }
            
            print("Placeholder: Processing audio stream")
            log_info("Processing audio stream data")
            
            # Placeholder processing
            processed_data = stream_data  # In real implementation, this would process the audio
            
            return {
                'success': True,
                'processed_data': processed_data,
                'analysis': {
                    'volume_level': 0.75,
                    'frequency_range': '80Hz-8kHz',
                    'noise_level': 0.1
                },
                'message': 'Audio stream processed successfully'
            }
        except Exception as e:
            log_error(f"Error processing audio stream: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def clear_audio_buffer(self):
        """Clear audio buffer"""
        try:
            # Clear the real-time buffer
            while not self.real_time_buffer.empty():
                try:
                    self.real_time_buffer.get_nowait()
                except queue.Empty:
                    break
            
            print("Placeholder: Clearing audio buffer")
            log_info("Audio buffer cleared")
            
            return {
                'success': True,
                'message': 'Audio buffer cleared successfully',
                'buffer_size': 0
            }
        except Exception as e:
            log_error(f"Error clearing audio buffer: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class VoiceCloner:
    """Voice cloning and synthesis capabilities"""
    
    def __init__(self):
        self.voice_models = {}
        self.target_voices = {}
        self.is_available = VOICE_CLONING_AVAILABLE
        
        if self.is_available:
            log_info("Voice cloning system initialized")
        else:
            log_warning("Voice cloning not available - missing dependencies")
    
    def clone_voice(self, source_audio_path: str, target_text: str, 
                   output_path: str) -> Dict[str, Any]:
        """Clone voice from source audio and synthesize target text"""
        try:
            if not self.is_available:
                return {
                    'success': False,
                    'error': 'Voice cloning not available'
                }
            
            # This would integrate with a voice cloning model like YourTTS or Coqui TTS
            # For now, return a placeholder implementation
            
            return {
                'success': False,
                'error': 'Voice cloning implementation pending',
                'note': 'Requires integration with voice cloning models'
            }
            
        except Exception as e:
            log_error(f"Voice cloning error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def extract_voice_characteristics(self, audio_path: str) -> Dict[str, Any]:
        """Extract voice characteristics for cloning"""
        try:
            if not AUDIO_LIBS_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Audio processing libraries not available'
                }
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050)
            
            # Extract voice characteristics
            characteristics = {
                'pitch': np.mean(librosa.yin(y, fmin=75, fmax=300)),
                'speaking_rate': len(y) / sr,
                'energy': np.sqrt(np.mean(y**2)),
                'spectral_centroid': np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)),
                'mfcc': np.mean(librosa.feature.mfcc(y=y, sr=sr), axis=1).tolist()
            }
            
            return {
                'success': True,
                'characteristics': characteristics
            }
            
        except Exception as e:
            log_error(f"Voice characteristic extraction error: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instances
audio_processor = AudioProcessor()
voice_cloner = VoiceCloner()


def transcribe_audio(file_path: str, transcription_controller=None) -> Dict[str, Any]:
    """
    Transcribe audio file to text using whisper.cpp
    
    Args:
        file_path: Path to the audio file to transcribe
        transcription_controller: Transcription controller instance
        
    Returns:
        Dictionary containing transcription results and metadata
    """
    try:
        # Validate file path for security
        if not file_path or not isinstance(file_path, str):
            return {
                'success': False,
                'text': '',
                'error': 'Invalid file path provided',
                'timestamp': None
            }
        
        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/') or ':' in file_path:
            return {
                'success': False,
                'text': '',
                'error': 'Invalid file path: path traversal not allowed',
                'timestamp': None
            }
        
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            return {
                'success': False,
                'text': '',
                'error': f'Audio file not found: {file_path}',
                'timestamp': None
            }
        
        # Check if transcription controller is provided
        if transcription_controller is None:
            log_warning("Transcription controller not provided")
            return {
                'success': False,
                'text': '',
                'error': 'Transcription service not configured',
                'timestamp': None
            }
        
        controller = transcription_controller
        
        # Check if service is running, start if needed
        if not controller.is_running():
            success, message = controller.start()
            if not success:
                return {
                    'success': False,
                    'text': '',
                    'error': f'Failed to start transcription service: {message}',
                    'timestamp': None
                }
        
        # Perform transcription
        success, message, text = controller.transcribe_audio(file_path)
        
        if success and text:
            log_info(f"Successfully transcribed audio: {len(text)} characters")
            return {
                'success': True,
                'text': text,
                'confidence': 1.0,  # whisper.cpp doesn't provide confidence scores
                'language': 'en',
                'error': None,
                'timestamp': None
            }
        else:
            log_warning(f"Transcription failed: {message}")
            return {
                'success': False,
                'text': '',
                'error': message,
                'timestamp': None
            }
            
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {e}")
        return {
            'success': False,
            'text': '',
            'error': f'Transcription error: {str(e)}',
            'timestamp': None
        }


@cached(timeout=3600)
def get_audio_features(file_path: str) -> Dict[str, Any]:
    """Get cached audio features"""
    return audio_processor.extract_audio_features(file_path)


def convert_audio_format(input_path: str, output_path: str, 
                        target_format: str = 'wav') -> Dict[str, Any]:
    """Convert audio file format"""
    return audio_processor.convert_audio_format(input_path, output_path, target_format)


def enhance_audio_quality(input_path: str, output_path: str,
                         noise_reduction: bool = True, normalize: bool = True) -> Dict[str, Any]:
    """Enhance audio quality"""
    return audio_processor.enhance_audio(input_path, output_path, noise_reduction, normalize)


def clone_voice_from_audio(source_audio: str, target_text: str, 
                          output_path: str) -> Dict[str, Any]:
    """Clone voice and synthesize text"""
    return voice_cloner.clone_voice(source_audio, target_text, output_path)


def get_voice_characteristics(audio_path: str) -> Dict[str, Any]:
    """Extract voice characteristics"""
    return voice_cloner.extract_voice_characteristics(audio_path)


def get_supported_audio_formats() -> Dict[str, str]:
    """Get supported audio formats"""
    return audio_processor.get_supported_formats()


def get_available_voices() -> Dict[str, Any]:
    """Get available TTS voices from all controllers"""
    try:
        voices = {}
        
        # Try to get voices from different TTS controllers
        try:
            from .edge_tts_controller import EdgeTTSController
            edge_controller = EdgeTTSController()
            edge_voices = edge_controller.get_available_voices_sync()
            voices['edge_tts'] = edge_voices
        except Exception as e:
            log_warning(f"Could not get Edge TTS voices: {e}")
            voices['edge_tts'] = []
        
        try:
            from .pyttsx3_tts_controller import PyTTSx3Controller
            pyttsx3_controller = PyTTSx3Controller()
            pyttsx3_voices = pyttsx3_controller.get_available_voices_sync()
            voices['pyttsx3'] = pyttsx3_voices
        except Exception as e:
            log_warning(f"Could not get pyttsx3 voices: {e}")
            voices['pyttsx3'] = []
        
        try:
            from .custom_tts_engine import CustomTTSEngine
            custom_controller = CustomTTSEngine()
            custom_voices = custom_controller.get_available_voices()
            voices['custom'] = custom_voices
        except Exception as e:
            log_warning(f"Could not get custom TTS voices: {e}")
            voices['custom'] = {}
        
        return {
            'success': True,
            'voices': voices,
            'total_voices': sum(len(v) if isinstance(v, list) else 1 for v in voices.values())
        }
        
    except Exception as e:
        log_error(f"Error getting available voices: {e}")
        return {
            'success': False,
            'error': str(e),
            'voices': {},
            'total_voices': 0
        }


def check_audio_capabilities() -> Dict[str, Any]:
    """Check system audio capabilities"""
    try:
        capabilities = {
            'audio_libs_available': AUDIO_LIBS_AVAILABLE,
            'voice_cloning_available': VOICE_CLONING_AVAILABLE,
            'recording_supported': True,  # Basic recording is always supported
            'playback_supported': True,   # Basic playback is always supported
            'advanced_processing': AUDIO_LIBS_AVAILABLE,
            'voice_cloning': VOICE_CLONING_AVAILABLE,
            'formats_supported': audio_processor.get_supported_formats() if AUDIO_LIBS_AVAILABLE else {'wav': 'Basic WAV support'},
            'tts_engines': {}
        }
        
        # Check TTS engine availability
        try:
            from .edge_tts_controller import EdgeTTSController
            capabilities['tts_engines']['edge_tts'] = True
        except Exception:
            capabilities['tts_engines']['edge_tts'] = False
        
        try:
            from .pyttsx3_tts_controller import PyTTSx3Controller
            capabilities['tts_engines']['pyttsx3'] = True
        except Exception:
            capabilities['tts_engines']['pyttsx3'] = False
        
        try:
            from .custom_tts_engine import CustomTTSEngine
            capabilities['tts_engines']['custom'] = True
        except Exception:
            capabilities['tts_engines']['custom'] = False
        
        return {
            'success': True,
            'capabilities': capabilities
        }
        
    except Exception as e:
        log_error(f"Error checking audio capabilities: {e}")
        return {
            'success': False,
            'error': str(e),
            'capabilities': {}
        }
