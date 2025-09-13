"""
Hardware Safety and Capability Detection System for Vybe
Provides hardware protection, capability detection, and safe denial for incompatible systems
"""

import psutil
import platform
import os
import threading
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import subprocess
import sys

from ..logger import log_info, log_warning, log_error

# Optional hardware monitoring libraries
try:
    import pynvml  # GPU monitoring (nvidia-ml-py package)
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    log_warning("pynvml not available - GPU monitoring features disabled")

try:
    from packaging import version
    PACKAGING_AVAILABLE = True
except ImportError:
    PACKAGING_AVAILABLE = False
    log_warning("packaging not available - version comparison features disabled")


class HardwareTier(Enum):
    """Hardware capability tiers"""
    MINIMAL = "minimal"      # Basic functionality only
    STANDARD = "standard"    # Standard features
    PERFORMANCE = "performance"  # High performance features
    UNSUPPORTED = "unsupported"  # Cannot run safely


class SafetyLevel(Enum):
    """Safety levels for hardware protection"""
    SAFE = "safe"           # Safe to run all features
    LIMITED = "limited"     # Limited features only
    RESTRICTED = "restricted"  # Severely restricted
    BLOCKED = "blocked"     # Cannot run safely


@dataclass
class HardwareSpecs:
    """Hardware specifications"""
    cpu_cores: int
    cpu_frequency: float
    memory_gb: float
    disk_space_gb: float
    gpu_memory_gb: Optional[float] = None
    gpu_name: Optional[str] = None
    os_version: str = ""
    python_version: str = ""


@dataclass
class SafetyThresholds:
    """Safety thresholds for hardware protection"""
    min_cpu_cores: int = 2
    min_memory_gb: float = 4.0
    min_disk_space_gb: float = 10.0
    max_cpu_usage_percent: float = 85.0
    max_memory_usage_percent: float = 90.0
    max_disk_usage_percent: float = 95.0
    max_temperature_celsius: float = 85.0
    max_gpu_temp_celsius: float = 80.0
    max_vram_usage_percent: float = 95.0
    emergency_cpu_threshold: float = 95.0
    emergency_memory_threshold: float = 98.0
    emergency_temp_threshold: float = 90.0
    operation_timeout_seconds: int = 300  # 5 minutes max for operations


class HardwareSafetyMonitor:
    """Monitors hardware safety and prevents damage"""
    
    def __init__(self):
        self.specs: Optional[HardwareSpecs] = None
        self.thresholds = SafetyThresholds()
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.safety_alerts: List[Dict[str, Any]] = []
        self.emergency_shutdown = False
        self.active_operations: Dict[str, Dict[str, Any]] = {}  # Track active operations for timeout
        self.operation_lock = threading.Lock()
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # GPU monitoring
        self.gpu_available = False
        self.gpu_handle = None
        
        # Initialize hardware detection
        self._detect_hardware()
        self._init_gpu_monitoring()
    
    def _detect_hardware(self):
        """Detect and analyze hardware capabilities"""
        try:
            # CPU information
            cpu_cores = psutil.cpu_count(logical=True) or 1
            cpu_freq = psutil.cpu_freq()
            cpu_frequency = cpu_freq.current if cpu_freq else 0.0
            
            # Memory information
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            
            # Disk information
            disk = psutil.disk_usage('/')
            disk_space_gb = disk.total / (1024**3)
            
            # GPU information
            gpu_memory_gb = None
            gpu_name = None
            if PYNVML_AVAILABLE:
                try:
                    pynvml.nvmlInit()
                    gpu_count = pynvml.nvmlDeviceGetCount()
                    if gpu_count > 0:
                        gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        gpu_info = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
                        gpu_memory_gb = float(gpu_info.total) / (1024**3)
                        gpu_name = pynvml.nvmlDeviceGetName(gpu_handle).decode('utf-8')
                        self.gpu_handle = gpu_handle
                        self.gpu_available = True
                except Exception as e:
                    log_warning(f"GPU detection failed: {e}")
                    self.gpu_available = False
            else:
                log_info("pynvml not available - GPU monitoring disabled")
                self.gpu_available = False
            
            # OS and Python version
            os_version = f"{platform.system()} {platform.release()}"
            python_version = sys.version.split()[0]
            
            self.specs = HardwareSpecs(
                cpu_cores=cpu_cores,
                cpu_frequency=cpu_frequency,
                memory_gb=memory_gb,
                disk_space_gb=disk_space_gb,
                gpu_memory_gb=gpu_memory_gb,
                gpu_name=gpu_name,
                os_version=os_version,
                python_version=python_version
            )
            
            log_info(f"Hardware detected: {cpu_cores} cores, {memory_gb:.1f}GB RAM, {disk_space_gb:.1f}GB disk")
            
        except Exception as e:
            log_error(f"Hardware detection failed: {e}")
            self.specs = None
    
    def _init_gpu_monitoring(self):
        """Initialize GPU monitoring capabilities"""
        if not self.gpu_available:
            return
        
        try:
            # Test GPU temperature monitoring
            if self.gpu_handle:
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
                    log_info(f"GPU temperature monitoring initialized: {temp}°C")
                except Exception as e:
                    log_warning(f"GPU temperature monitoring unavailable: {e}")
                    
                # Test memory monitoring
                try:
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                    # Ensure we're working with numeric values
                    mem_used = float(mem_info.used) if hasattr(mem_info, 'used') else 0.0
                    mem_total = float(mem_info.total) if hasattr(mem_info, 'total') else 1.0
                    usage_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0.0
                    log_info(f"GPU memory monitoring initialized: {usage_percent:.1f}% used")
                except Exception as e:
                    log_warning(f"GPU memory monitoring unavailable: {e}")
        except Exception as e:
            log_error(f"GPU monitoring initialization failed: {e}")
            self.gpu_available = False
    
    def get_current_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive current performance metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'cpu_temperature': self._get_cpu_temperature(),
            'gpu_temperature': self._get_gpu_temperature(),
            'vram_usage': self._get_vram_usage(),
            'active_operations': len(self.active_operations),
            'emergency_shutdown': self.emergency_shutdown
        }
        
        # Add to performance history
        self.performance_history.append(metrics)
        if len(self.performance_history) > self.max_history_size:
            self.performance_history.pop(0)
        
        return metrics
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """Get current CPU temperature (Linux/Windows specific)"""
        try:
            # Try different methods for CPU temperature
            if platform.system() == "Linux":
                # Try reading from thermal zone (Linux)
                thermal_files = [
                    "/sys/class/thermal/thermal_zone0/temp",
                    "/sys/class/thermal/thermal_zone1/temp"
                ]
                for thermal_file in thermal_files:
                    try:
                        with open(thermal_file, 'r') as f:
                            temp_millic = int(f.read().strip())
                            return temp_millic / 1000.0  # Convert from millicelsius
                    except (FileNotFoundError, ValueError, PermissionError):
                        continue
            elif platform.system() == "Windows":
                # Windows temperature monitoring requires WMI or third-party tools
                # For now, return None as it's complex to implement reliably
                pass
            
            return None
        except Exception as e:
            log_warning(f"Failed to get CPU temperature: {e}")
            return None
    
    def check_safety_thresholds(self) -> Tuple[SafetyLevel, List[str]]:
        """Check current metrics against safety thresholds"""
        metrics = self.get_current_performance_metrics()
        alerts = []
        safety_level = SafetyLevel.SAFE
        
        # Check CPU usage
        if metrics['cpu_usage'] > self.thresholds.emergency_cpu_threshold:
            alerts.append(f"CRITICAL: CPU usage at {metrics['cpu_usage']:.1f}%")
            safety_level = SafetyLevel.BLOCKED
        elif metrics['cpu_usage'] > self.thresholds.max_cpu_usage_percent:
            alerts.append(f"WARNING: High CPU usage at {metrics['cpu_usage']:.1f}%")
            if safety_level == SafetyLevel.SAFE:
                safety_level = SafetyLevel.LIMITED
        
        # Check memory usage
        if metrics['memory_usage'] > self.thresholds.emergency_memory_threshold:
            alerts.append(f"CRITICAL: Memory usage at {metrics['memory_usage']:.1f}%")
            safety_level = SafetyLevel.BLOCKED
        elif metrics['memory_usage'] > self.thresholds.max_memory_usage_percent:
            alerts.append(f"WARNING: High memory usage at {metrics['memory_usage']:.1f}%")
            if safety_level == SafetyLevel.SAFE:
                safety_level = SafetyLevel.LIMITED
        
        # Check temperatures
        if metrics['cpu_temperature'] and metrics['cpu_temperature'] > self.thresholds.emergency_temp_threshold:
            alerts.append(f"CRITICAL: CPU temperature at {metrics['cpu_temperature']:.1f}°C")
            safety_level = SafetyLevel.BLOCKED
        
        if metrics['gpu_temperature'] and metrics['gpu_temperature'] > self.thresholds.max_gpu_temp_celsius:
            alerts.append(f"WARNING: GPU temperature at {metrics['gpu_temperature']:.1f}°C")
            if safety_level == SafetyLevel.SAFE:
                safety_level = SafetyLevel.LIMITED
        
        return safety_level, alerts

    def enhanced_monitoring_check(self) -> Dict[str, Any]:
        """
        Enhanced comprehensive system monitoring with detailed safety checks
        """
        # Get current metrics
        gpu_temp = self._get_gpu_temperature()
        vram_info = self._get_vram_usage()
        cpu_usage = psutil.cpu_percent(interval=1)
        if isinstance(cpu_usage, list):
            cpu_usage = sum(cpu_usage) / len(cpu_usage)
        cpu_usage = float(cpu_usage) if cpu_usage is not None else 0.0
        
        memory_info = psutil.virtual_memory()
        
        # Handle VRAM info safely
        vram_used = 0.0
        vram_percent = 0.0
        if isinstance(vram_info, dict):
            vram_used = vram_info.get('used_gb', 0.0)
            vram_percent = vram_info.get('usage_percent', 0.0)
        elif isinstance(vram_info, (int, float)):
            vram_percent = float(vram_info)
        
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'gpu': {
                'temperature': gpu_temp,
                'vram_usage': vram_info,
                'memory_usage_gb': vram_used,
                'temperature_safe': gpu_temp < 85.0 if gpu_temp is not None else True,
                'vram_safe': vram_percent < 90.0
            },
            'cpu': {
                'usage_percent': cpu_usage,
                'usage_safe': cpu_usage < 85.0
            },
            'memory': {
                'usage_percent': memory_info.percent,
                'available_gb': memory_info.available / (1024**3),
                'usage_safe': memory_info.percent < 90.0
            },
            'overall_safety_status': 'SAFE',
            'recommendations': []
        }
        
        # Analyze safety and add recommendations
        if not monitoring_data['gpu']['temperature_safe']:
            monitoring_data['overall_safety_status'] = 'WARNING'
            monitoring_data['recommendations'].append(f"GPU temperature high: {gpu_temp}°C")
            
        if not monitoring_data['gpu']['vram_safe']:
            monitoring_data['overall_safety_status'] = 'WARNING'
            monitoring_data['recommendations'].append("VRAM usage high - consider reducing batch size")
            
        if not monitoring_data['cpu']['usage_safe']:
            monitoring_data['overall_safety_status'] = 'WARNING'
            monitoring_data['recommendations'].append("CPU usage high - reduce concurrent operations")
            
        if not monitoring_data['memory']['usage_safe']:
            monitoring_data['overall_safety_status'] = 'CRITICAL'
            monitoring_data['recommendations'].append("Memory usage critical - stop non-essential processes")
        
        return monitoring_data
    
    def _test_gpu_monitoring(self):
        """Test GPU monitoring capabilities"""
        if not self.gpu_available or not self.gpu_handle or not PYNVML_AVAILABLE:
            return
            
        try:
            import pynvml
            # Test GPU monitoring capability
            temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            log_info(f"GPU monitoring initialized - current temp: {temp}°C")
        except Exception as e:
            log_warning(f"GPU monitoring initialization failed: {e}")
            self.gpu_available = False
    
    def _get_gpu_temperature(self) -> Optional[float]:
        """Get current GPU temperature"""
        if not self.gpu_available or not self.gpu_handle or not PYNVML_AVAILABLE:
            return None
        
        try:
            temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            return float(temp)
        except Exception as e:
            log_warning(f"Failed to get GPU temperature: {e}")
            return None
    
    def _get_vram_usage(self) -> Optional[float]:
        """Get current VRAM usage percentage"""
        if not self.gpu_available or not self.gpu_handle or not PYNVML_AVAILABLE:
            return None
        
        try:
            gpu_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            usage_percent = (float(gpu_info.used) / float(gpu_info.total)) * 100
            return usage_percent
        except Exception as e:
            log_warning(f"Failed to get VRAM usage: {e}")
            return None
    
    def register_operation(self, operation_id: str, operation_type: str, timeout_seconds: Optional[int] = None) -> bool:
        """Register a new operation for timeout monitoring"""
        with self.operation_lock:
            if self.emergency_shutdown:
                return False
            
            timeout = timeout_seconds or self.thresholds.operation_timeout_seconds
            self.active_operations[operation_id] = {
                'type': operation_type,
                'start_time': datetime.now(),
                'timeout': timeout,
                'status': 'running'
            }
            return True
    
    def unregister_operation(self, operation_id: str):
        """Unregister completed operation"""
        with self.operation_lock:
            if operation_id in self.active_operations:
                self.active_operations[operation_id]['status'] = 'completed'
                del self.active_operations[operation_id]
    
    def emergency_stop_all(self):
        """Emergency stop for all operations"""
        log_warning("EMERGENCY STOP: Terminating all operations")
        
        with self.operation_lock:
            self.emergency_shutdown = True
            for operation_id, operation in self.active_operations.items():
                operation['status'] = 'emergency_stopped'
                log_warning(f"Emergency stopped operation: {operation_id} ({operation['type']})")
        
        # This would implement actual operation termination
        # For now, just set the flag to prevent new operations
    
    def reset_emergency_stop(self):
        """Reset emergency stop state (admin only)"""
        with self.operation_lock:
            self.emergency_shutdown = False
            self.active_operations.clear()
        log_info("Emergency stop reset - operations can resume")
    
    def _check_operation_timeouts(self):
        """Check for operations that have exceeded timeout"""
        current_time = datetime.now()
        
        with self.operation_lock:
            timed_out_operations = []
            
            for operation_id, operation in self.active_operations.items():
                if operation['status'] == 'running':
                    elapsed = (current_time - operation['start_time']).total_seconds()
                    if elapsed > operation['timeout']:
                        timed_out_operations.append(operation_id)
            
            for operation_id in timed_out_operations:
                operation = self.active_operations[operation_id]
                log_warning(f"Operation timeout: {operation_id} ({operation['type']}) - {elapsed:.1f}s")
                operation['status'] = 'timed_out'
                
                alert = {
                    'timestamp': current_time.isoformat(),
                    'level': 'warning',
                    'type': 'operation_timeout',
                    'operation_id': operation_id,
                    'operation_type': operation['type'],
                    'elapsed_seconds': elapsed
                }
                self.safety_alerts.append(alert)

    def get_hardware_tier(self) -> HardwareTier:
        """Determine hardware capability tier"""
        if not self.specs:
            return HardwareTier.UNSUPPORTED
        
        # Check minimum requirements
        if (self.specs.cpu_cores < self.thresholds.min_cpu_cores or
            self.specs.memory_gb < self.thresholds.min_memory_gb or
            self.specs.disk_space_gb < self.thresholds.min_disk_space_gb):
            return HardwareTier.UNSUPPORTED
        
        # Determine tier based on capabilities
        if self.specs.cpu_cores >= 8 and self.specs.memory_gb >= 16:
            return HardwareTier.PERFORMANCE
        elif self.specs.cpu_cores >= 4 and self.specs.memory_gb >= 8:
            return HardwareTier.STANDARD
        else:
            return HardwareTier.MINIMAL
    
    def get_safety_level(self) -> SafetyLevel:
        """Get current safety level based on hardware monitoring"""
        if not self.specs:
            return SafetyLevel.BLOCKED
        
        # Check current resource usage
        cpu_usage = psutil.cpu_percent(interval=1)
        if isinstance(cpu_usage, list):
            cpu_usage = sum(cpu_usage) / len(cpu_usage)
        cpu_usage = float(cpu_usage) if cpu_usage is not None else 0.0
        
        memory_usage = float(psutil.virtual_memory().percent)
        disk_usage = float(psutil.disk_usage('/').percent)
        
        # Check GPU temperature if available
        gpu_temp = self._get_gpu_temperature()
        if gpu_temp and gpu_temp > self.thresholds.max_gpu_temp_celsius:
            return SafetyLevel.BLOCKED
        
        # Check for critical conditions
        if (cpu_usage > self.thresholds.max_cpu_usage_percent or
            memory_usage > self.thresholds.max_memory_usage_percent or
            disk_usage > self.thresholds.max_disk_usage_percent):
            return SafetyLevel.BLOCKED
        
        # Check for high usage
        if (cpu_usage > 70 or memory_usage > 80 or disk_usage > 90):
            return SafetyLevel.RESTRICTED
        
        # Check for moderate usage
        if (cpu_usage > 50 or memory_usage > 60 or disk_usage > 80):
            return SafetyLevel.LIMITED
        
        return SafetyLevel.SAFE
    
    def start_monitoring(self):
        """Start hardware safety monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        log_info("Hardware safety monitoring started")
    
    def stop_monitoring(self):
        """Stop hardware safety monitoring"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        log_info("Hardware safety monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                current_time = datetime.now()
                
                # Get current resource usage
                cpu_usage_raw = psutil.cpu_percent(interval=1)
                if isinstance(cpu_usage_raw, list):
                    cpu_usage = sum(cpu_usage_raw) / len(cpu_usage_raw)
                else:
                    cpu_usage = float(cpu_usage_raw) if cpu_usage_raw is not None else 0.0
                
                memory_usage = float(psutil.virtual_memory().percent)
                disk_usage = float(psutil.disk_usage('/').percent)
                
                # Get GPU metrics
                gpu_temp = self._get_gpu_temperature()
                vram_usage = self._get_vram_usage()
                
                # Record performance data
                performance_data = {
                    'timestamp': current_time.isoformat(),
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'disk_usage': disk_usage,
                    'gpu_temperature': gpu_temp,
                    'vram_usage': vram_usage,
                    'safety_level': self.get_safety_level().value
                }
                
                self.performance_history.append(performance_data)
                
                # Limit history size
                if len(self.performance_history) > self.max_history_size:
                    self.performance_history = self.performance_history[-self.max_history_size:]
                
                # Check for safety violations
                self._check_safety_violations(cpu_usage, memory_usage, disk_usage, gpu_temp, vram_usage)
                
                # Check operation timeouts
                self._check_operation_timeouts()
                
                # Sleep between checks
                time.sleep(5)
                
            except Exception as e:
                log_error(f"Hardware monitoring error: {e}")
                time.sleep(10)
    
    def _check_safety_violations(self, cpu_usage: float, memory_usage: float, disk_usage: float, 
                                gpu_temp: Optional[float] = None, vram_usage: Optional[float] = None):
        """Check for safety violations and take action"""
        violations = []
        
        if cpu_usage > self.thresholds.max_cpu_usage_percent:
            violations.append(f"CPU usage critical: {cpu_usage:.1f}%")
        
        if memory_usage > self.thresholds.max_memory_usage_percent:
            violations.append(f"Memory usage critical: {memory_usage:.1f}%")
        
        if disk_usage > self.thresholds.max_disk_usage_percent:
            violations.append(f"Disk usage critical: {disk_usage:.1f}%")
        
        if gpu_temp and gpu_temp > self.thresholds.max_gpu_temp_celsius:
            violations.append(f"GPU temperature critical: {gpu_temp:.1f}°C")
        
        if vram_usage and vram_usage > self.thresholds.max_vram_usage_percent:
            violations.append(f"VRAM usage critical: {vram_usage:.1f}%")
        
        if violations:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'level': 'critical',
                'violations': violations,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'gpu_temp': gpu_temp,
                'vram_usage': vram_usage
            }
            
            self.safety_alerts.append(alert)
            log_warning(f"Hardware safety violation: {', '.join(violations)}")
            
            # Take immediate action for critical violations
            if (cpu_usage > self.thresholds.emergency_cpu_threshold or 
                memory_usage > self.thresholds.emergency_memory_threshold or
                (gpu_temp and gpu_temp > self.thresholds.emergency_temp_threshold)):
                self._emergency_throttle()
    
    def _emergency_throttle(self):
        """Emergency throttling to prevent hardware damage"""
        if self.emergency_shutdown:
            return
        
        self.emergency_shutdown = True
        log_warning("EMERGENCY: Hardware protection activated - throttling operations")
        
        # This would implement actual throttling mechanisms
        # For now, just log the event
    
    def get_safety_report(self) -> Dict[str, Any]:
        """Get comprehensive safety report"""
        if not self.specs:
            return {
                'status': 'error',
                'message': 'Hardware detection failed'
            }
        
        current_safety = self.get_safety_level()
        hardware_tier = self.get_hardware_tier()
        
        # Get recent performance data
        recent_performance = self.performance_history[-10:] if self.performance_history else []
        
        return {
            'status': 'ok',
            'hardware_specs': {
                'cpu_cores': self.specs.cpu_cores,
                'cpu_frequency': self.specs.cpu_frequency,
                'memory_gb': self.specs.memory_gb,
                'disk_space_gb': self.specs.disk_space_gb,
                'gpu_memory_gb': self.specs.gpu_memory_gb,
                'gpu_name': self.specs.gpu_name,
                'os_version': self.specs.os_version,
                'python_version': self.specs.python_version
            },
            'hardware_tier': hardware_tier.value,
            'safety_level': current_safety.value,
            'current_usage': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'safety_thresholds': {
                'max_cpu_usage': self.thresholds.max_cpu_usage_percent,
                'max_memory_usage': self.thresholds.max_memory_usage_percent,
                'max_disk_usage': self.thresholds.max_disk_usage_percent
            },
            'recent_performance': recent_performance,
            'safety_alerts': self.safety_alerts[-5:],  # Last 5 alerts
            'emergency_shutdown': self.emergency_shutdown,
            'monitoring_active': self.monitoring
        }


class CapabilityDetector:
    """Detects system capabilities and provides safe denial for incompatible systems"""
    
    def __init__(self):
        self.safety_monitor = HardwareSafetyMonitor()
        self.minimum_requirements = {
            'cpu_cores': 2,
            'memory_gb': 4.0,
            'disk_space_gb': 10.0,
            'os_supported': ['Windows', 'Linux', 'Darwin'],
            'python_version': '3.8.0'
        }
        self.recommended_requirements = {
            'cpu_cores': 4,
            'memory_gb': 8.0,
            'disk_space_gb': 20.0,
            'gpu_memory_gb': 4.0
        }
    
    def check_system_compatibility(self) -> Dict[str, Any]:
        """Check if system meets minimum requirements"""
        if not self.safety_monitor.specs:
            return {
                'compatible': False,
                'reason': 'Hardware detection failed',
                'recommendations': ['Ensure system meets minimum requirements']
            }
        
        specs = self.safety_monitor.specs
        issues = []
        warnings = []
        
        # Check CPU cores
        if specs.cpu_cores < self.minimum_requirements['cpu_cores']:
            issues.append(f"Insufficient CPU cores: {specs.cpu_cores} (minimum: {self.minimum_requirements['cpu_cores']})")
        elif specs.cpu_cores < self.recommended_requirements['cpu_cores']:
            warnings.append(f"Low CPU cores: {specs.cpu_cores} (recommended: {self.recommended_requirements['cpu_cores']})")
        
        # Check memory
        if specs.memory_gb < self.minimum_requirements['memory_gb']:
            issues.append(f"Insufficient memory: {specs.memory_gb:.1f}GB (minimum: {self.minimum_requirements['memory_gb']}GB)")
        elif specs.memory_gb < self.recommended_requirements['memory_gb']:
            warnings.append(f"Low memory: {specs.memory_gb:.1f}GB (recommended: {self.recommended_requirements['memory_gb']}GB)")
        
        # Check disk space
        if specs.disk_space_gb < self.minimum_requirements['disk_space_gb']:
            issues.append(f"Insufficient disk space: {specs.disk_space_gb:.1f}GB (minimum: {self.minimum_requirements['disk_space_gb']}GB)")
        elif specs.disk_space_gb < self.recommended_requirements['disk_space_gb']:
            warnings.append(f"Low disk space: {specs.disk_space_gb:.1f}GB (recommended: {self.recommended_requirements['disk_space_gb']}GB)")
        
        # Check OS compatibility
        current_os = platform.system()
        if current_os not in self.minimum_requirements['os_supported']:
            issues.append(f"Unsupported operating system: {current_os}")
        
        # Check Python version
        if self._compare_versions(specs.python_version, self.minimum_requirements['python_version']) < 0:
            issues.append(f"Python version too old: {specs.python_version} (minimum: {self.minimum_requirements['python_version']})")
        
        # Check GPU (optional but recommended)
        if not specs.gpu_memory_gb:
            warnings.append("No dedicated GPU detected - some features may be limited")
        elif specs.gpu_memory_gb < self.recommended_requirements['gpu_memory_gb']:
            warnings.append(f"Low GPU memory: {specs.gpu_memory_gb:.1f}GB (recommended: {self.recommended_requirements['gpu_memory_gb']}GB)")
        
        compatible = len(issues) == 0
        
        return {
            'compatible': compatible,
            'hardware_tier': self.safety_monitor.get_hardware_tier().value,
            'issues': issues,
            'warnings': warnings,
            'specs': {
                'cpu_cores': specs.cpu_cores,
                'memory_gb': specs.memory_gb,
                'disk_space_gb': specs.disk_space_gb,
                'gpu_memory_gb': specs.gpu_memory_gb,
                'os': specs.os_version,
                'python_version': specs.python_version
            },
            'recommendations': self._generate_recommendations(issues, warnings)
        }
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare version strings"""
        if not PACKAGING_AVAILABLE:
            log_warning("packaging not available - using basic string comparison")
            # Basic string comparison fallback
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            else:
                return 0
                
        try:
            from packaging import version
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except Exception as e:
            log_warning(f"Version comparison failed: {e}")
            return 0
    
    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Generate recommendations based on issues and warnings"""
        recommendations = []
        
        if issues:
            recommendations.append("System does not meet minimum requirements:")
            recommendations.extend([f"• {issue}" for issue in issues])
            recommendations.append("Please upgrade your hardware or use a different system.")
        
        if warnings:
            recommendations.append("Performance recommendations:")
            recommendations.extend([f"• {warning}" for warning in warnings])
            recommendations.append("Consider upgrading for better performance.")
        
        if not issues and not warnings:
            recommendations.append("System meets all requirements. Ready to run Vybe!")
        
        return recommendations
    
    def get_safe_denial_message(self) -> str:
        """Get user-friendly denial message for incompatible systems"""
        compatibility = self.check_system_compatibility()
        
        if compatibility['compatible']:
            return "System is compatible with Vybe."
        
        message = "⚠️ System Compatibility Check Failed\n\n"
        message += "Your system does not meet the minimum requirements to run Vybe safely:\n\n"
        
        for issue in compatibility['issues']:
            message += f"• {issue}\n"
        
        message += "\nRecommendations:\n"
        for rec in compatibility['recommendations']:
            message += f"• {rec}\n"
        
        message += "\nFor your safety and to prevent system damage, Vybe cannot start on this system."
        message += "\n\nPlease upgrade your hardware or use a compatible system."
        
        return message


# Global instances with lazy initialization to prevent race conditions
_hardware_safety_monitor = None
_capability_detector = None
_safety_lock = threading.Lock()


def get_hardware_safety_monitor():
    """Get hardware safety monitor instance with thread-safe lazy initialization"""
    global _hardware_safety_monitor
    if _hardware_safety_monitor is None:
        with _safety_lock:
            if _hardware_safety_monitor is None:
                _hardware_safety_monitor = HardwareSafetyMonitor()
    return _hardware_safety_monitor


def get_capability_detector():
    """Get capability detector instance with thread-safe lazy initialization"""
    global _capability_detector
    if _capability_detector is None:
        with _safety_lock:
            if _capability_detector is None:
                _capability_detector = CapabilityDetector()
    return _capability_detector


# Backwards compatibility - keep these names but use lazy initialization
def hardware_safety_monitor():
    return get_hardware_safety_monitor()


def capability_detector():
    return get_capability_detector()


def initialize_hardware_safety():
    """Initialize hardware safety system"""
    # Start monitoring
    get_hardware_safety_monitor().start_monitoring()
    
    # Check compatibility
    compatibility = get_capability_detector().check_system_compatibility()
    
    if not compatibility['compatible']:
        log_warning("System compatibility check failed")
        log_warning(f"Issues: {compatibility['issues']}")
    
    log_info("Hardware safety system initialized")
    return compatibility


def get_hardware_safety_report() -> Dict[str, Any]:
    """Get hardware safety report"""
    return get_hardware_safety_monitor().get_safety_report()


def check_system_compatibility() -> Dict[str, Any]:
    """Check system compatibility"""
    return get_capability_detector().check_system_compatibility()


def get_safe_denial_message() -> str:
    """Get safe denial message for incompatible systems"""
    return get_capability_detector().get_safe_denial_message()
