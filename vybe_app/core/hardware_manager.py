"""
Hardware Manager for Vybe
Detects, benchmarks, and classifies system hardware to enable intelligent resource management
"""

import os
import platform
import psutil
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

from ..models import db, AppSetting

# Import app for Flask application context
try:
    from .. import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    print("Warning: Flask app not available for hardware manager")

logger = logging.getLogger(__name__)


class HardwareManager:
    """
    Manages hardware detection, benchmarking, and performance tier classification.
    This enables Vybe to be self-optimizing based on available resources.
    """
    
    # Performance tier thresholds
    TIER_DEFINITIONS = {
        'high_end': {
            'min_ram_gb': 32,
            'min_vram_gb': 8,
            'min_cpu_cores': 8,
            'min_cpu_freq_ghz': 3.0,
            'description': 'High-end workstation capable of running large models and multiple concurrent tasks'
        },
        'mid_range': {
            'min_ram_gb': 16,
            'min_vram_gb': 6,  # Updated for 7B model requirements (GTX 1080 level)
            'min_cpu_cores': 6,
            'min_cpu_freq_ghz': 2.8,
            'description': 'GTX 1080+ level system suitable for 7B models with good performance'
        },
        'entry_level': {  # Renamed from low_end to be more descriptive
            'min_ram_gb': 12,  # Increased minimum for 7B models
            'min_vram_gb': 0,
            'min_cpu_cores': 2,
            'min_cpu_freq_ghz': 2.0,
            'description': 'Low-end system requiring optimized small models'
        },
        'minimal': {
            'min_ram_gb': 4,
            'min_vram_gb': 0,
            'min_cpu_cores': 2,
            'min_cpu_freq_ghz': 1.5,
            'description': 'Minimal system with basic capabilities only'
        }
    }
    
    # Model recommendations by tier
    MODEL_RECOMMENDATIONS = {
        'high_end': {
            'chat': ['llama-2-70b', 'mixtral-8x7b', 'llama-2-13b'],
            'image': ['sdxl', 'stable-diffusion-2.1'],
            'max_context': 32768,
            'keep_models_loaded': True,
            'concurrent_models': 3
        },
        'mid_range': {
            'chat': ['llama-2-7b', 'mistral-7b', 'phi-3-medium'],
            'image': ['stable-diffusion-1.5', 'sd-turbo'],
            'max_context': 32768,
            'keep_models_loaded': True,
            'concurrent_models': 2
        },
        'entry_level': {
            'chat': ['phi-3-mini', 'tinyllama', 'gemma-2b'],
            'image': ['sd-turbo'],
            'max_context': 32768,
            'keep_models_loaded': False,
            'concurrent_models': 1
        },
        'minimal': {
            'chat': ['tinyllama'],
            'image': [],  # No image generation on minimal systems
            'max_context': 32768,
            'keep_models_loaded': False,
            'concurrent_models': 1
        }
    }
    
    def __init__(self):
        """Initialize the Hardware Manager"""
        self.hardware_info = {}
        self.performance_tier = None
        self.benchmark_results = {}
        self.last_benchmark_time = None
        
        # Initialize NVIDIA monitoring if available
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.nvidia_available = True
                logger.info("NVIDIA GPU monitoring initialized")
            except Exception as e:
                self.nvidia_available = False
                logger.warning(f"NVIDIA GPU not available or monitoring failed to initialize: {e}")
        else:
            self.nvidia_available = False
            logger.info("pynvml not available - GPU monitoring disabled")
        
        # Load cached hardware info if available
        self._load_cached_info()
    
    def detect_hardware(self) -> Dict[str, Any]:
        """
        Detect and catalog system hardware capabilities
        
        Returns:
            Dictionary containing detailed hardware information
        """
        logger.info("Starting hardware detection...")
        
        hardware = {
            'timestamp': datetime.now().isoformat(),
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            },
            'cpu': self._detect_cpu(),
            'memory': self._detect_memory(),
            'gpu': self._detect_gpu(),
            'storage': self._detect_storage(),
            'network': self._detect_network()
        }
        
        self.hardware_info = hardware
        self._save_hardware_info()
        
        logger.info(f"Hardware detection complete: {hardware['cpu']['count']} cores, "
                   f"{hardware['memory']['total_gb']:.1f}GB RAM")
        
        return hardware
    
    def _detect_cpu(self) -> Dict[str, Any]:
        """Detect CPU information"""
        cpu_freq = psutil.cpu_freq()
        
        return {
            'count': psutil.cpu_count(logical=False) or 1,
            'count_logical': psutil.cpu_count(logical=True) or 1,
            'frequency_mhz': cpu_freq.current if cpu_freq else 0,
            'frequency_max_mhz': cpu_freq.max if cpu_freq else 0,
            'brand': platform.processor(),
            'architecture': platform.machine()
        }
    
    def _detect_memory(self) -> Dict[str, Any]:
        """Detect memory information"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'used_gb': mem.used / (1024**3),
            'percent_used': mem.percent,
            'swap_total_gb': swap.total / (1024**3),
            'swap_used_gb': swap.used / (1024**3)
        }
    
    def _detect_gpu(self) -> Dict[str, Any]:
        """Detect GPU information"""
        gpu_info = {
            'available': False,
            'count': 0,
            'devices': []
        }
        
        if self.nvidia_available:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                gpu_info['available'] = True
                gpu_info['count'] = device_count
                
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    gpu_info['devices'].append({
                        'index': i,
                        'name': name,
                        'memory_total_gb': float(mem_info.total) / (1024**3),
                        'memory_used_gb': float(mem_info.used) / (1024**3),
                        'memory_free_gb': float(mem_info.free) / (1024**3)
                    })
                    
            except Exception as e:
                logger.warning(f"Error detecting GPU: {e}")
        
        return gpu_info
    
    def _detect_storage(self) -> Dict[str, Any]:
        """Detect storage information"""
        disk = psutil.disk_usage('/')
        
        return {
            'total_gb': disk.total / (1024**3),
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'percent_used': disk.percent
        }
    
    def _detect_network(self) -> Dict[str, Any]:
        """Detect network capabilities"""
        return {
            'interfaces': len(psutil.net_if_addrs()),
            'has_internet': self._check_internet_connection()
        }
    
    def _check_internet_connection(self) -> bool:
        """Check if internet connection is available"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception as e:
            logger.debug(f"Internet connection check failed: {e}")
            return False
    
    def benchmark_system(self) -> Dict[str, Any]:
        """
        Run system benchmarks to measure actual performance
        
        Returns:
            Dictionary containing benchmark results
        """
        logger.info("Starting system benchmark...")
        
        benchmarks = {
            'timestamp': datetime.now().isoformat(),
            'cpu_benchmark': self._benchmark_cpu(),
            'memory_benchmark': self._benchmark_memory(),
            'gpu_benchmark': self._benchmark_gpu() if self.nvidia_available else None,
            'disk_benchmark': self._benchmark_disk()
        }
        
        self.benchmark_results = benchmarks
        self.last_benchmark_time = datetime.now()
        self._save_benchmark_results()
        
        logger.info("System benchmark complete")
        return benchmarks
    
    def _benchmark_cpu(self) -> Dict[str, Any]:
        """Run CPU benchmark"""
        logger.info("Running CPU benchmark...")
        
        # Simple CPU benchmark - calculate primes
        start_time = time.time()
        
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n**0.5) + 1):
                if n % i == 0:
                    return False
            return True
        
        # Find primes up to 50000
        prime_count = sum(1 for i in range(50000) if is_prime(i))
        
        elapsed_time = time.time() - start_time
        
        return {
            'prime_calculation_time': elapsed_time,
            'primes_found': prime_count,
            'score': 10000 / elapsed_time  # Higher is better
        }
    
    def _benchmark_memory(self) -> Dict[str, Any]:
        """Run memory benchmark"""
        logger.info("Running memory benchmark...")
        
        # Memory speed test - allocate and access large array
        start_time = time.time()
        
        try:
            # Allocate 100MB of data
            size = 100 * 1024 * 1024
            data = bytearray(size)
            
            # Write pattern
            for i in range(0, size, 4096):
                data[i] = i % 256
            
            # Read and verify
            checksum = sum(data[i] for i in range(0, size, 4096))
            
            elapsed_time = time.time() - start_time
            
            return {
                'allocation_size_mb': 100,
                'operation_time': elapsed_time,
                'throughput_mbps': (100 * 2) / elapsed_time,  # Read + write
                'checksum': checksum
            }
        except Exception as e:
            logger.warning(f"Memory benchmark failed: {e}")
            return {'error': str(e)}
    
    def _benchmark_gpu(self) -> Optional[Dict[str, Any]]:
        """Run GPU benchmark if available"""
        if not self.nvidia_available:
            return None
        
        logger.info("Running GPU benchmark...")
        
        try:
            # Get GPU utilization over a period
            samples = []
            for _ in range(10):
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                samples.append(util.gpu)
                time.sleep(0.1)
            
            return {
                'avg_utilization': sum(samples) / len(samples),
                'max_utilization': max(samples),
                'min_utilization': min(samples)
            }
        except Exception as e:
            logger.warning(f"GPU benchmark failed: {e}")
            return {'error': str(e)}
    
    def _benchmark_disk(self) -> Dict[str, Any]:
        """Run disk I/O benchmark"""
        logger.info("Running disk benchmark...")
        
        test_file = Path(__file__).parent.parent.parent / 'benchmark_test.tmp'
        test_size = 10 * 1024 * 1024  # 10MB
        
        try:
            # Write test
            write_start = time.time()
            with open(test_file, 'wb') as f:
                f.write(os.urandom(test_size))
            write_time = time.time() - write_start
            
            # Read test
            read_start = time.time()
            with open(test_file, 'rb') as f:
                data = f.read()
            read_time = time.time() - read_start
            
            # Cleanup
            test_file.unlink()
            
            return {
                'write_speed_mbps': (test_size / (1024 * 1024)) / write_time,
                'read_speed_mbps': (test_size / (1024 * 1024)) / read_time,
                'test_size_mb': test_size / (1024 * 1024)
            }
        except Exception as e:
            logger.warning(f"Disk benchmark failed: {e}")
            if test_file.exists():
                test_file.unlink()
            return {'error': str(e)}
    
    def classify_performance_tier(self) -> str:
        """
        Classify system into performance tier based on hardware
        
        Returns:
            Performance tier name (high_end, mid_range, low_end, minimal)
        """
        if not self.hardware_info:
            self.detect_hardware()
        
        hw = self.hardware_info
        
        # Extract key metrics
        ram_gb = hw['memory']['total_gb']
        cpu_cores = hw['cpu']['count']
        # Safely handle frequency calculation with explicit type conversion
        freq_max_mhz = hw['cpu']['frequency_max_mhz']
        if freq_max_mhz and isinstance(freq_max_mhz, (int, float)) and freq_max_mhz > 0:
            cpu_freq_ghz = float(freq_max_mhz) / 1000
        else:
            cpu_freq_ghz = 2.0  # Default fallback
        
        # GPU VRAM
        vram_gb = 0
        if hw['gpu']['available'] and hw['gpu']['devices']:
            vram_gb = hw['gpu']['devices'][0]['memory_total_gb']
        
        # Check tiers from highest to lowest
        for tier_name in ['high_end', 'mid_range', 'entry_level', 'minimal']:
            tier = self.TIER_DEFINITIONS[tier_name]
            
            if (ram_gb >= tier['min_ram_gb'] and
                cpu_cores >= tier['min_cpu_cores'] and
                cpu_freq_ghz >= tier['min_cpu_freq_ghz'] and
                vram_gb >= tier['min_vram_gb']):
                
                self.performance_tier = tier_name
                logger.info(f"System classified as: {tier_name} - {tier['description']}")
                self._save_performance_tier()
                return tier_name
        
        # Default to minimal if no tier matches
        self.performance_tier = 'minimal'
        logger.warning("System classified as minimal - performance may be limited")
        self._save_performance_tier()
        return 'minimal'
    
    def get_model_recommendations(self) -> Dict[str, Any]:
        """
        Get model recommendations based on hardware tier
        
        Returns:
            Dictionary containing recommended models and settings
        """
        if not self.performance_tier:
            self.classify_performance_tier()
        
        # Ensure performance_tier is not None
        tier = self.performance_tier or 'minimal'
        
        recommendations = self.MODEL_RECOMMENDATIONS.get(
            tier, 
            self.MODEL_RECOMMENDATIONS['minimal']
        )
        
        return {
            'tier': tier,
            'tier_description': self.TIER_DEFINITIONS[tier]['description'],
            'recommendations': recommendations,
            'hardware_summary': self._get_hardware_summary()
        }
    
    def _get_hardware_summary(self) -> str:
        """Get a concise hardware summary"""
        if not self.hardware_info:
            return "Hardware information not available"
        
        hw = self.hardware_info
        gpu_str = f", GPU: {hw['gpu']['devices'][0]['name']}" if hw['gpu']['available'] else ""
        
        return (f"CPU: {hw['cpu']['count']} cores, "
                f"RAM: {hw['memory']['total_gb']:.1f}GB{gpu_str}")
    
    def can_run_model(self, model_name: str, model_size_gb: float) -> Tuple[bool, str]:
        """
        Check if system can run a specific model
        
        Args:
            model_name: Name of the model
            model_size_gb: Size of model in GB
            
        Returns:
            Tuple of (can_run, reason)
        """
        if not self.hardware_info:
            self.detect_hardware()
        
        available_ram = self.hardware_info['memory']['available_gb']
        
        # Rule of thumb: need 2x model size in RAM for comfortable operation
        required_ram = model_size_gb * 2
        
        if available_ram < required_ram:
            return (False, f"Insufficient RAM: {available_ram:.1f}GB available, "
                          f"{required_ram:.1f}GB recommended")
        
        # Check GPU if model requires it
        if 'sdxl' in model_name.lower() or 'stable-diffusion' in model_name.lower():
            if not self.hardware_info['gpu']['available']:
                return (False, "GPU required for image generation models")
            
            vram = self.hardware_info['gpu']['devices'][0]['memory_total_gb']
            if vram < model_size_gb:
                return (False, f"Insufficient VRAM: {vram:.1f}GB available, "
                              f"{model_size_gb:.1f}GB required")
        
        return (True, "Model can run on this system")
    
    def get_resource_limits(self) -> Dict[str, Any]:
        """
        Get recommended resource limits based on hardware
        
        Returns:
            Dictionary containing resource limits
        """
        if not self.performance_tier:
            self.classify_performance_tier()
        
        # Ensure performance_tier is not None
        tier = self.performance_tier or 'minimal'
        tier_config = self.MODEL_RECOMMENDATIONS[tier]
        
        return {
            'max_context_length': tier_config['max_context'],
            'max_concurrent_models': tier_config['concurrent_models'],
            'keep_models_loaded': tier_config['keep_models_loaded'],
            'max_batch_size': 8 if self.performance_tier == 'high_end' else 
                             4 if self.performance_tier == 'mid_range' else 1,
            'enable_gpu_acceleration': self.hardware_info.get('gpu', {}).get('available', False)
        }
    
    def _save_hardware_info(self):
        """Save hardware info to database"""
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - cannot save hardware info to database")
                return
                
            with app.app_context():
                setting = AppSetting.query.filter_by(key='hardware_info').first()
                if not setting:
                    setting = AppSetting()
                    setting.key = 'hardware_info'
                setting.value = json.dumps(self.hardware_info)
                db.session.add(setting)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save hardware info: {e}")
    
    def _save_benchmark_results(self):
        """Save benchmark results to database"""
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - cannot save benchmark results to database")
                return
                
            with app.app_context():
                setting = AppSetting.query.filter_by(key='benchmark_results').first()
                if not setting:
                    setting = AppSetting()
                    setting.key = 'benchmark_results'
                setting.value = json.dumps(self.benchmark_results)
                db.session.add(setting)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save benchmark results: {e}")
    
    def _save_performance_tier(self):
        """Save performance tier to database"""
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - cannot save performance tier to database")
                return
                
            with app.app_context():
                setting = AppSetting.query.filter_by(key='performance_tier').first()
                if not setting:
                    setting = AppSetting()
                    setting.key = 'performance_tier'
                setting.value = self.performance_tier
                db.session.add(setting)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save performance tier: {e}")
    
    def _load_cached_info(self):
        """Load cached hardware info from database"""
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - cannot load cached hardware info from database")
                return
                
            with app.app_context():
                # Load hardware info
                hw_setting = AppSetting.query.filter_by(key='hardware_info').first()
                if hw_setting and hw_setting.value:
                    self.hardware_info = json.loads(hw_setting.value)
            
                # Load benchmark results
                bench_setting = AppSetting.query.filter_by(key='benchmark_results').first()
                if bench_setting and bench_setting.value:
                    self.benchmark_results = json.loads(bench_setting.value)
            
                # Load performance tier
                tier_setting = AppSetting.query.filter_by(key='performance_tier').first()
                if tier_setting and tier_setting.value:
                    self.performance_tier = tier_setting.value
            
            if self.hardware_info:
                logger.info("Loaded cached hardware information")
        except Exception as e:
            logger.warning(f"Could not load cached hardware info: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current hardware manager status"""
        return {
            'hardware_detected': bool(self.hardware_info),
            'performance_tier': self.performance_tier,
            'last_benchmark': self.last_benchmark_time.isoformat() if self.last_benchmark_time else None,
            'gpu_available': self.nvidia_available,
            'summary': self._get_hardware_summary()
        }


# Global instance
_hardware_manager: Optional[HardwareManager] = None


def get_hardware_manager() -> HardwareManager:
    """Get or create the global Hardware Manager instance"""
    global _hardware_manager
    if _hardware_manager is None:
        _hardware_manager = HardwareManager()
    return _hardware_manager


def initialize_hardware_manager():
    """Initialize Hardware Manager on application startup"""
    manager = get_hardware_manager()
    
    # Run initial hardware detection
    manager.detect_hardware()
    
    # Classify system tier
    tier = manager.classify_performance_tier()
    
    # Run benchmark if never done or > 30 days old
    if not manager.last_benchmark_time:
        logger.info("Running initial system benchmark...")
        manager.benchmark_system()
    
    logger.info(f"Hardware Manager initialized - System tier: {tier}")
    return manager

# Create global instance
try:
    hardware_manager = get_hardware_manager()
except Exception as e:
    logger.error(f"Failed to create hardware manager: {e}")
    # Create a minimal fallback instance
    hardware_manager = HardwareManager()