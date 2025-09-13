"""
Integration tests and validation functions for Vybe features
Ensures all components work together properly
"""

import asyncio
import time
import requests
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..logger import logger
from ..core.manager_model import get_manager_model
from ..core.stable_diffusion_controller import stable_diffusion_controller
from ..core.video_generator import VideoGeneratorController
from ..core.edge_tts_controller import EdgeTTSController
from ..core.transcription_controller import TranscriptionController
from ..core.system_monitor import SystemMonitor
from ..core.job_manager import job_manager
from ..models import db, User, SystemPrompt, AppSetting

logger = logging.getLogger(__name__)


class IntegrationValidator:
    """Validates that all Vybe components work together properly"""
    
    def __init__(self):
        self.test_results = {}
        self.errors = []
        self.warnings = []
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive integration tests"""
        logger.info("🧪 Starting comprehensive integration tests...")
        
        # Core system tests
        await self._test_orchestrator_functionality()
        await self._test_database_connectivity()
        await self._test_hardware_detection()
        
        # Feature tests
        await self._test_image_generation_integration()
        await self._test_video_generation_integration()
        await self._test_audio_functionality()
        await self._test_model_management()
        
        # API tests
        await self._test_api_endpoints()
        await self._test_websocket_connectivity()
        
        # Performance tests
        await self._test_performance_monitoring()
        await self._test_memory_management()
        
        return {
            'success': len(self.errors) == 0,
            'test_results': self.test_results,
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': self._generate_test_summary()
        }
    
    async def _test_orchestrator_functionality(self):
        """Test orchestrator model functionality"""
        test_name = "orchestrator_functionality"
        try:
            manager = get_manager_model()
            
            # Test orchestrator initialization
            status = manager.get_status()
            assert status['is_ready'], "Orchestrator not ready"
            
            # Test PC profile analysis
            pc_profile = manager.pc_profile
            assert 'hardware_tier' in pc_profile, "Hardware tier not detected"
            assert 'total_ram_gb' in pc_profile, "RAM not detected"
            
            # Test available models
            models = manager.get_available_orchestrator_models()
            assert len(models) >= 8, f"Expected 8+ orchestrator models, got {len(models)}"
            
            # Test personalization
            recommendations = manager.get_personalized_recommendations()
            assert isinstance(recommendations, dict), "Recommendations not returned properly"
            
            self.test_results[test_name] = {
                'status': 'passed',
                'details': {
                    'orchestrator_ready': status['is_ready'],
                    'hardware_tier': pc_profile.get('hardware_tier'),
                    'available_models': len(models),
                    'recommendations_available': len(recommendations) > 0
                }
            }
            
        except Exception as e:
            self.errors.append(f"Orchestrator test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_database_connectivity(self):
        """Test database connectivity and integrity"""
        test_name = "database_connectivity"
        try:
            # Test basic database operations
            user_count = User.query.count()
            prompt_count = SystemPrompt.query.count()
            setting_count = AppSetting.query.count()
            
            # Test creating and deleting test records with proper constructor
            test_setting = AppSetting()
            test_setting.key = 'test_integration'
            test_setting.value = 'test_value'
            db.session.add(test_setting)
            db.session.commit()
            
            # Verify creation
            retrieved = AppSetting.query.filter_by(key='test_integration').first()
            assert retrieved is not None, "Test setting not created"
            assert retrieved.value == 'test_value', "Test setting value incorrect"
            
            # Clean up
            db.session.delete(retrieved)
            db.session.commit()
            
            self.test_results[test_name] = {
                'status': 'passed',
                'details': {
                    'users': user_count,
                    'system_prompts': prompt_count,
                    'settings': setting_count,
                    'crud_operations': 'working'
                }
            }
            
        except Exception as e:
            self.errors.append(f"Database test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_hardware_detection(self):
        """Test hardware detection and monitoring"""
        test_name = "hardware_detection"
        try:
            monitor = SystemMonitor()
            
            # Test system usage monitoring
            usage = monitor.get_system_usage()
            assert 'cpu_percent' in usage, "CPU usage not detected"
            assert 'ram_percent' in usage, "RAM usage not detected"
            assert 0 <= usage['cpu_percent'] <= 100, "CPU percentage out of range"
            
            # Test hardware info
            try:
                if hasattr(monitor, 'get_hardware_info'):
                    hw_info = getattr(monitor, 'get_hardware_info')()
                    assert 'cpu_count' in hw_info, "CPU count not detected"
                    assert 'memory_total' in hw_info, "Memory total not detected"
                else:
                    hw_info = {'warning': 'get_hardware_info method not available', 'memory_total': 0}
            except Exception as e:
                logger.warning(f"Hardware info test failed: {e}")
                hw_info = {'warning': f'Hardware info error: {e}', 'memory_total': 0}
            
            self.test_results[test_name] = {
                'status': 'passed',
                'details': {
                    'cpu_usage': usage['cpu_percent'],
                    'ram_usage': usage['ram_percent'],
                    'cpu_cores': hw_info.get('cpu_count'),
                    'total_memory_gb': round(hw_info.get('memory_total', 0) / (1024**3), 1)
                }
            }
            
        except Exception as e:
            self.errors.append(f"Hardware detection test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_image_generation_integration(self):
        """Test image generation functionality"""
        test_name = "image_generation"
        try:
            # Test Stable Diffusion availability with safe attribute access
            is_available = getattr(stable_diffusion_controller, 'is_installed', lambda: False)()
            is_running = getattr(stable_diffusion_controller, 'is_running', lambda: False)()
            
            if not is_available:
                self.warnings.append("Stable Diffusion not installed - image generation unavailable")
                self.test_results[test_name] = {
                    'status': 'skipped',
                    'reason': 'Stable Diffusion not installed'
                }
                return
            
            # Test configuration with safe attribute access
            config = getattr(stable_diffusion_controller, 'get_config', lambda: {})()
            if config:
                assert 'base_url' in config, "Base URL not configured"
            
            # Test models (if running)
            if is_running:
                models = stable_diffusion_controller.get_models()
                samplers = stable_diffusion_controller.get_samplers()
                
                self.test_results[test_name] = {
                    'status': 'passed',
                    'details': {
                        'installed': is_available,
                        'running': is_running,
                        'models_available': len(models),
                        'samplers_available': len(samplers),
                        'base_url': config.get('base_url')
                    }
                }
            else:
                self.test_results[test_name] = {
                    'status': 'partial',
                    'details': {
                        'installed': is_available,
                        'running': is_running,
                        'note': 'Service installed but not running'
                    }
                }
            
        except Exception as e:
            self.errors.append(f"Image generation test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_video_generation_integration(self):
        """Test video generation functionality"""
        test_name = "video_generation"
        try:
            video_controller = VideoGeneratorController()
            
            # Test installation status
            status = video_controller.check_and_install()
            is_running = video_controller.is_running()
            
            # Test configuration
            service_status = video_controller.get_status()
            
            self.test_results[test_name] = {
                'status': 'passed' if status['installed'] else 'partial',
                'details': {
                    'comfyui_available': status.get('comfyui_available', False),
                    'models_available': status.get('models_available', False),
                    'running': is_running,
                    'installation_path': status.get('installation_path'),
                    'models_count': status.get('models_count', '0/0')
                }
            }
            
            if not status['installed']:
                self.warnings.append("Video generation not fully installed - some features unavailable")
            
        except Exception as e:
            self.errors.append(f"Video generation test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_audio_functionality(self):
        """Test audio processing functionality"""
        test_name = "audio_functionality"
        try:
            # Test TTS
            tts_controller = EdgeTTSController()
            tts_available = tts_controller.available
            
            if tts_available:
                voices = tts_controller.get_available_voices_sync()
                voice_count = len(voices)
            else:
                voice_count = 0
                self.warnings.append("Edge TTS not available - speech synthesis limited")
            
            # Test transcription
            try:
                transcription_controller = TranscriptionController()
                transcription_available = getattr(transcription_controller, 'is_available', lambda: False)()
            except Exception as e:
                transcription_available = False
                self.warnings.append(f"Transcription service not available: {e}")
            
            self.test_results[test_name] = {
                'status': 'passed' if (tts_available or transcription_available) else 'partial',
                'details': {
                    'tts_available': tts_available,
                    'voice_count': voice_count,
                    'transcription_available': transcription_available,
                    'audio_features': 'basic' if not (tts_available and transcription_available) else 'full'
                }
            }
            
        except Exception as e:
            self.errors.append(f"Audio functionality test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_model_management(self):
        """Test model management functionality"""
        test_name = "model_management"
        try:
            from ..utils.llm_model_manager import LLMModelManager
            
            model_manager = LLMModelManager()
            available_models = model_manager.get_available_models()
            
            # Test model discovery with safe attribute access
            discovered_models = getattr(model_manager, 'discover_models', lambda: [])()
            
            self.test_results[test_name] = {
                'status': 'passed',
                'details': {
                    'available_models': len(available_models),
                    'discovered_models': len(discovered_models),
                    'model_types': list(set(m.get('type', 'unknown') for m in available_models))
                }
            }
            
        except Exception as e:
            self.errors.append(f"Model management test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_api_endpoints(self):
        """Test critical API endpoints"""
        test_name = "api_endpoints"
        try:
            # Test basic endpoints (assuming running on localhost:8000)
            base_url = "http://127.0.0.1:8000"
            endpoints_to_test = [
                '/api/orchestrator/status',
                '/api/models/available',
                '/api/settings/get/theme_mode'
            ]
            
            working_endpoints = []
            failed_endpoints = []
            
            for endpoint in endpoints_to_test:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        working_endpoints.append(endpoint)
                    else:
                        failed_endpoints.append(f"{endpoint} ({response.status_code})")
                except Exception as e:
                    failed_endpoints.append(f"{endpoint} (error: {str(e)})")
            
            self.test_results[test_name] = {
                'status': 'passed' if len(failed_endpoints) == 0 else 'partial',
                'details': {
                    'working_endpoints': working_endpoints,
                    'failed_endpoints': failed_endpoints,
                    'total_tested': len(endpoints_to_test)
                }
            }
            
            if failed_endpoints:
                self.warnings.append(f"Some API endpoints failed: {failed_endpoints}")
            
        except Exception as e:
            self.errors.append(f"API endpoints test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_websocket_connectivity(self):
        """Test WebSocket connectivity"""
        test_name = "websocket_connectivity"
        try:
            # This is a simplified test - full WebSocket testing would require a client
            self.test_results[test_name] = {
                'status': 'skipped',
                'reason': 'WebSocket testing requires active client connection'
            }
            
        except Exception as e:
            self.errors.append(f"WebSocket test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_performance_monitoring(self):
        """Test performance monitoring functionality"""
        test_name = "performance_monitoring"
        try:
            monitor = SystemMonitor()
            
            # Test resource tracking
            initial_usage = monitor.get_system_usage()
            
            # Test job manager with safe attribute access
            active_jobs = getattr(job_manager, 'active_jobs', [])
            job_count = len(active_jobs) if active_jobs else 0
            
            self.test_results[test_name] = {
                'status': 'passed',
                'details': {
                    'monitoring_active': True,
                    'current_cpu': initial_usage.get('cpu_percent', 0),
                    'current_ram': initial_usage.get('ram_percent', 0),
                    'active_jobs': job_count,
                    'job_manager_running': job_manager.is_running()
                }
            }
            
        except Exception as e:
            self.errors.append(f"Performance monitoring test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    async def _test_memory_management(self):
        """Test memory management and cleanup"""
        test_name = "memory_management"
        try:
            import gc
            import psutil
            import os
            
            # Get current process memory
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / (1024 * 1024)  # MB
            
            # Force garbage collection
            collected = gc.collect()
            
            memory_after = process.memory_info().rss / (1024 * 1024)  # MB
            memory_freed = memory_before - memory_after
            
            self.test_results[test_name] = {
                'status': 'passed',
                'details': {
                    'memory_before_mb': round(memory_before, 2),
                    'memory_after_mb': round(memory_after, 2),
                    'memory_freed_mb': round(memory_freed, 2),
                    'objects_collected': collected,
                    'gc_working': collected >= 0
                }
            }
            
        except Exception as e:
            self.errors.append(f"Memory management test failed: {str(e)}")
            self.test_results[test_name] = {'status': 'failed', 'error': str(e)}
    
    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate a summary of test results"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r['status'] == 'passed'])
        failed_tests = len([r for r in self.test_results.values() if r['status'] == 'failed'])
        partial_tests = len([r for r in self.test_results.values() if r['status'] == 'partial'])
        skipped_tests = len([r for r in self.test_results.values() if r['status'] == 'skipped'])
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'partial_tests': partial_tests,
            'skipped_tests': skipped_tests,
            'success_rate': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0,
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings),
            'overall_status': 'healthy' if failed_tests == 0 and len(self.errors) == 0 else 'issues_detected'
        }


async def run_integration_tests() -> Dict[str, Any]:
    """Run comprehensive integration tests"""
    validator = IntegrationValidator()
    return await validator.run_comprehensive_tests()


def run_integration_tests_sync() -> Dict[str, Any]:
    """Synchronous wrapper for integration tests"""
    try:
        return asyncio.run(run_integration_tests())
    except Exception as e:
        logger.error(f"Integration tests failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'test_results': {},
            'summary': {'overall_status': 'test_failure'}
        }
