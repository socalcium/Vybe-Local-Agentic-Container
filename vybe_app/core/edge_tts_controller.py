"""
Edge TTS Controller for Vybe - High-quality text-to-speech using Microsoft Edge TTS
Supports 17+ languages with various voices and styles.
"""

import asyncio
import os
import io
import base64
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

EDGE_TTS_AVAILABLE = False
_EDGE_TTS_MOD = None

from ..logger import logger


class EdgeTTSController:
    """Controller for managing Microsoft Edge TTS functionality"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        # Use user data directory for output
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.output_dir = output_dir or user_data_dir / "workspace" / "tts_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.available = False
        self.default_voice = "en-US-AriaNeural"  # High-quality English voice
        self.default_rate = "+0%"  # Normal speaking rate
        self.default_pitch = "+0Hz"  # Normal pitch
        
        # Voice cache
        self._voices_cache = None
        
        # Attempt import lazily to avoid linter import errors when package is absent
        global _EDGE_TTS_MOD, EDGE_TTS_AVAILABLE
        try:
            if _EDGE_TTS_MOD is None:
                import importlib
                _EDGE_TTS_MOD = importlib.import_module('edge_tts')
            self.available = True
            EDGE_TTS_AVAILABLE = True
        except Exception:
            self.available = False
            EDGE_TTS_AVAILABLE = False
            logger.info("edge-tts not available - using offline TTS by default")
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get all available voices from Edge TTS"""
        if not self.available or _EDGE_TTS_MOD is None:
            return []
            
        if self._voices_cache is not None:
            return self._voices_cache
            
        try:
            voices = await _EDGE_TTS_MOD.list_voices()
            # Format voices for frontend consumption
            self._voices_cache = [
                {
                    'name': voice['Name'],
                    'short_name': voice['ShortName'],
                    'language': voice['Locale'],
                    'language_name': voice.get('LocaleName', voice['Locale']),
                    'gender': voice['Gender'],
                    'suggested_codec': voice.get('SuggestedCodec', 'audio-24khz-48kbitrate-mono-mp3'),
                    'friendly_name': voice.get('FriendlyName', voice['ShortName'])
                }
                for voice in voices
            ]
            return self._voices_cache
        except Exception as e:
            logger.error(f"Failed to fetch available voices: {e}")
            return []
    
    def get_available_voices_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for getting available voices"""
        if not self.available:
            return []
            
        try:
            # Run in new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, create a new one in a thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.get_available_voices())
                        return future.result(timeout=10)
                else:
                    return loop.run_until_complete(self.get_available_voices())
            except RuntimeError:
                return asyncio.run(self.get_available_voices())
        except Exception as e:
            logger.error(f"Failed to get voices synchronously: {e}")
            return []
    
    async def synthesize_speech_async(
        self, 
        text: str, 
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """
        Synthesize speech from text using Edge TTS
        
        Args:
            text: Text to synthesize
            voice: Voice name (e.g., "en-US-AriaNeural")
            rate: Speech rate (e.g., "+0%", "+50%", "-20%")
            pitch: Pitch (e.g., "+0Hz", "+50Hz", "-20Hz")
            output_file: Output file path (optional)
            
        Returns:
            Path to generated audio file or None if failed
        """
        if not self.available or _EDGE_TTS_MOD is None:
            logger.warning("Edge TTS not available")
            return None
            
        if not text.strip():
            logger.warning("Empty text provided for TTS")
            return None
        
        # Use defaults if not specified
        voice = voice or self.default_voice
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch
        
        try:
            # Create communicate object
            communicate = _EDGE_TTS_MOD.Communicate(text, voice, rate=rate, pitch=pitch)
            
            # Generate output file path if not provided
            output_path: Path
            if output_file is None:
                import hashlib
                import time
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                timestamp = int(time.time())
                output_path = self.output_dir / f"tts_{timestamp}_{text_hash}.mp3"
            else:
                output_path = Path(output_file)
                
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the audio
            await communicate.save(str(output_path))
            
            if output_path.exists():
                logger.info(f"TTS audio generated: {output_path}")
                return str(output_path)
            else:
                logger.error("TTS audio file was not created")
                return None
                
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            return None
    
    def synthesize_speech(
        self, 
        text: str, 
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """
        Synchronous wrapper for synthesize_speech_async
        
        Args:
            text: Text to synthesize
            voice: Voice name (e.g., "en-US-AriaNeural")
            rate: Speech rate (e.g., "+0%", "+50%", "-20%")
            pitch: Pitch (e.g., "+0Hz", "+50Hz", "-20Hz")
            output_file: Output file path (optional)
            
        Returns:
            Path to generated audio file or None if failed
        """
        if not self.available:
            return None
            
        try:
            # Run in new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, create a new one in a thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            self.synthesize_speech_async(text, voice, rate, pitch, output_file)
                        )
                        return future.result(timeout=30)
                else:
                    return loop.run_until_complete(
                        self.synthesize_speech_async(text, voice, rate, pitch, output_file)
                    )
            except RuntimeError:
                return asyncio.run(
                    self.synthesize_speech_async(text, voice, rate, pitch, output_file)
                )
        except Exception as e:
            logger.error(f"Failed to synthesize speech synchronously: {e}")
            return None
    
    async def get_audio_base64_async(
        self, 
        text: str, 
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> Optional[str]:
        """
        Get synthesized speech as base64-encoded audio data
        
        Args:
            text: Text to synthesize
            voice: Voice name
            rate: Speech rate
            pitch: Pitch
            
        Returns:
            Base64-encoded audio data or None if failed
        """
        if not self.available or _EDGE_TTS_MOD is None:
            return None
            
        voice = voice or self.default_voice
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch
        
        try:
            communicate = _EDGE_TTS_MOD.Communicate(text, voice, rate=rate, pitch=pitch)
            
            # Collect audio data in memory
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    if "data" in chunk:
                        audio_data += chunk["data"]
            
            if audio_data:
                # Encode as base64
                return base64.b64encode(audio_data).decode('utf-8')
            else:
                logger.error("No audio data generated")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate base64 audio: {e}")
            return None
    
    def get_audio_base64(
        self, 
        text: str, 
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> Optional[str]:
        """Synchronous wrapper for get_audio_base64_async"""
        if not self.available:
            return None
            
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            self.get_audio_base64_async(text, voice, rate, pitch)
                        )
                        return future.result(timeout=30)
                else:
                    return loop.run_until_complete(
                        self.get_audio_base64_async(text, voice, rate, pitch)
                    )
            except RuntimeError:
                return asyncio.run(
                    self.get_audio_base64_async(text, voice, rate, pitch)
                )
        except Exception as e:
            logger.error(f"Failed to get base64 audio synchronously: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get TTS system status"""
        return {
            'available': self.available,
            'engine': 'Microsoft Edge TTS' if self.available else 'Not Available',
            'default_voice': self.default_voice,
            'output_directory': str(self.output_dir),
            'voices_cached': self._voices_cache is not None,
            'voice_count': len(self._voices_cache) if self._voices_cache else 0
        }
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        voices = self.get_available_voices_sync()
        languages = list(set(voice['language'] for voice in voices))
        return sorted(languages)
    
    def get_voices_for_language(self, language: str) -> List[Dict[str, Any]]:
        """Get available voices for a specific language"""
        voices = self.get_available_voices_sync()
        return [voice for voice in voices if voice['language'] == language]
    
    def start_tts(self) -> bool:
        """Start TTS service (placeholder for compatibility)"""
        logger.info("EdgeTTS service started")
        return True
    
    def stop_tts(self) -> bool:
        """Stop TTS service (placeholder for compatibility)"""
        logger.info("EdgeTTS service stopped")
        return True
    
    def get_tts_status(self) -> Dict[str, Any]:
        """Get TTS service status (placeholder for compatibility)"""
        return {
            'running': self.available,
            'controller': 'EdgeTTS',
            'voices_available': len(self.get_available_voices_sync()) if self.available else 0
        }


# No global instance to avoid importing optional dependency at import time

def get_edge_tts_controller() -> EdgeTTSController:
    """Factory for EdgeTTSController; returns a lazily-initialized instance."""
    return EdgeTTSController()
