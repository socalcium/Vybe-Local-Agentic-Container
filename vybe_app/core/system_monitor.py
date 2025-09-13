"""
System Resource Monitoring for Vybe
Provides utilities for checking CPU, RAM, and GPU usage with advanced resource management.
"""

import psutil
import gc
import threading
import time
from typing import Dict, List, Any, Optional
from collections import deque
import os

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    pynvml = None
    PYNVML_AVAILABLE = False

from ..logger import log_info, log_warning, log_error, log_debug


class ResourceManager:
    """Advanced resource management and optimization"""
    
    def __init__(self):
        self.memory_threshold = 0.85  # 85% memory usage threshold
        self.cpu_threshold = 0.90     # 90% CPU usage threshold
        self.disk_threshold = 0.90    # 90% disk usage threshold
        
        # Resource history for trend analysis
        self.resource_history = {
            'memory': deque(maxlen=100),
            'cpu': deque(maxlen=100),
            'disk': deque(maxlen=100)
        }
        
        # Performance alerts
        self.alerts = []
        self.alert_lock = threading.Lock()
        
        # Automatic optimization settings
        self.auto_optimize = True
        self.optimization_thresholds = {
            'memory': 0.80,  # 80% memory usage triggers optimization
            'cpu': 0.85,     # 85% CPU usage triggers optimization
            'disk': 0.85     # 85% disk usage triggers optimization
        }
        
        # Optimization history
        self.optimization_history = deque(maxlen=50)
        
        # Start monitoring thread
        self.monitoring = True
        self._stop_monitoring_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
    
    def cleanup(self):
        """Clean up resources and stop monitoring"""
        try:
            self.monitoring = False
            self._stop_monitoring_event.set()
            
            if hasattr(self, "monitor_thread") and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            log_info("Resource manager cleanup completed")
        except Exception as e:
            log_error(f"Resource manager cleanup error: {e}")
    
    def get_memory_optimization_suggestions(self) -> List[str]:
        """Get memory optimization suggestions based on current usage"""
        suggestions = []
        memory = psutil.virtual_memory()
        
        if memory.percent > 80:
            suggestions.append("High memory usage detected")
            suggestions.append("Consider reducing model size or batch processing")
            suggestions.append("Close unused applications")
            
            if memory.percent > 90:
                suggestions.append("CRITICAL: Memory usage very high")
                suggestions.append("Immediate action required - restart services if needed")
        
        # Check for memory leaks
        if len(self.resource_history['memory']) > 10:
            recent_memory = list(self.resource_history['memory'])[-10:]
            if all(recent_memory[i] < recent_memory[i+1] for i in range(len(recent_memory)-1)):
                suggestions.append("Potential memory leak detected - increasing trend")
        
        return suggestions
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization"""
        optimization_results = {
            'garbage_collection': False,
            'memory_freed_mb': 0,
            'suggestions': []
        }
        
        # Force garbage collection
        try:
            initial_memory = psutil.virtual_memory().used
            collected = gc.collect()
            final_memory = psutil.virtual_memory().used
            memory_freed = initial_memory - final_memory
            
            optimization_results['garbage_collection'] = True
            optimization_results['memory_freed_mb'] = round(memory_freed / (1024 * 1024), 2)
            
            if memory_freed > 0:
                log_info(f"Memory optimization freed {optimization_results['memory_freed_mb']} MB")
            
        except Exception as e:
            log_error(f"Memory optimization failed: {e}")
            optimization_results['suggestions'].append("Memory optimization failed")
        
        # Add optimization suggestions
        optimization_results['suggestions'].extend(self.get_memory_optimization_suggestions())
        
        return optimization_results
    
    def check_resource_health(self) -> Dict[str, Any]:
        """Comprehensive resource health check"""
        health_status = {
            'overall_health': 'good',
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check memory
        memory = psutil.virtual_memory()
        if memory.percent > self.memory_threshold * 100:
            health_status['issues'].append(f"High memory usage: {memory.percent:.1f}%")
            health_status['overall_health'] = 'warning'
        
        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        if isinstance(cpu_percent, (int, float)) and cpu_percent > self.cpu_threshold * 100:
            health_status['issues'].append(f"High CPU usage: {cpu_percent:.1f}%")
            health_status['overall_health'] = 'warning'
        
        # Check disk space
        disk = psutil.disk_usage('/')
        if disk.percent > self.disk_threshold * 100:
            health_status['issues'].append(f"Low disk space: {disk.percent:.1f}% used")
            health_status['overall_health'] = 'warning'
        
        # Check for resource trends
        if len(self.resource_history['memory']) > 20:
            recent_memory = list(self.resource_history['memory'])[-20:]
            if recent_memory[-1] > recent_memory[0] * 1.2:  # 20% increase
                health_status['warnings'].append("Memory usage trending upward")
        
        # Generate recommendations
        if isinstance(memory.percent, (int, float)) and memory.percent > 70:
            health_status['recommendations'].append("Consider memory optimization")
        if isinstance(cpu_percent, (int, float)) and cpu_percent > 80:
            health_status['recommendations'].append("Reduce concurrent operations")
        if isinstance(disk.percent, (int, float)) and disk.percent > 80:
            health_status['recommendations'].append("Clean up disk space")
        
        return health_status
    
    def _monitor_resources(self):
        """Background resource monitoring"""
        while self.monitoring:
            try:
                # Record resource usage
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
                
                self.resource_history['memory'].append(memory.percent)
                self.resource_history['cpu'].append(cpu)
                self.resource_history['disk'].append(disk.percent)
                
                # Check for critical conditions and trigger automatic optimization
                if memory.percent > 95:
                    self._add_alert("CRITICAL: Memory usage above 95%", "critical")
                    self._trigger_automatic_optimization('memory', 'critical')
                elif memory.percent > self.optimization_thresholds['memory'] * 100:
                    self._add_alert("High memory usage detected", "warning")
                    self._trigger_automatic_optimization('memory', 'warning')
                
                if isinstance(cpu, (int, float)) and cpu > 95:
                    self._add_alert("CRITICAL: CPU usage above 95%", "critical")
                    self._trigger_automatic_optimization('cpu', 'critical')
                elif isinstance(cpu, (int, float)) and cpu > self.optimization_thresholds['cpu'] * 100:
                    self._add_alert("High CPU usage detected", "warning")
                    self._trigger_automatic_optimization('cpu', 'warning')
                
                # Check disk space
                if disk.percent > self.optimization_thresholds['disk'] * 100:
                    self._add_alert("Low disk space detected", "warning")
                    self._trigger_automatic_optimization('disk', 'warning')
                
                # Wait for monitoring interval or stop signal
                if hasattr(self, "_stop_monitoring_event") and self._stop_monitoring_event.is_set():
                    break
                self._stop_monitoring_event.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                log_error(f"Resource monitoring error: {e}")
                # Wait longer on error but remain interruptible
                self._stop_monitoring_event.wait(60)  # Wait longer on error
    
    def _add_alert(self, message: str, level: str):
        """Add resource alert"""
        with self.alert_lock:
            alert = {
                'timestamp': time.time(),
                'message': message,
                'level': level
            }
            self.alerts.append(alert)
            
            # Keep only recent alerts
            if len(self.alerts) > 50:
                self.alerts = self.alerts[-50:]
            
            log_warning(f"Resource alert: {message}")
    
    def get_alerts(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get resource alerts"""
        with self.alert_lock:
            if level:
                return [alert for alert in self.alerts if alert['level'] == level]
            return self.alerts.copy()
    
    def clear_alerts(self):
        """Clear all alerts"""
        with self.alert_lock:
            self.alerts.clear()
    
    def _trigger_automatic_optimization(self, resource_type: str, severity: str):
        """Trigger automatic resource optimization based on conditions"""
        if not self.auto_optimize:
            return
        
        # Prevent too frequent optimizations
        current_time = time.time()
        if self.optimization_history:
            last_optimization = self.optimization_history[-1]
            if current_time - last_optimization['timestamp'] < 300:  # 5 minutes cooldown
                return
        
        optimization_result = {
            'timestamp': current_time,
            'resource_type': resource_type,
            'severity': severity,
            'actions_taken': []
        }
        
        try:
            if resource_type == 'memory':
                if severity == 'critical':
                    # Critical memory optimization
                    result = self.optimize_memory()
                    optimization_result['actions_taken'].append('forced_garbage_collection')
                    
                    # Try to free more memory
                    self._force_memory_cleanup()
                    optimization_result['actions_taken'].append('force_memory_cleanup')
                    
                elif severity == 'warning':
                    # Warning level memory optimization
                    result = self.optimize_memory()
                    optimization_result['actions_taken'].append('garbage_collection')
            
            elif resource_type == 'cpu':
                if severity == 'critical':
                    # Critical CPU optimization
                    self._reduce_cpu_load()
                    optimization_result['actions_taken'].append('reduce_cpu_load')
                
                elif severity == 'warning':
                    # Warning level CPU optimization
                    self._optimize_cpu_usage()
                    optimization_result['actions_taken'].append('optimize_cpu_usage')
            
            elif resource_type == 'disk':
                # Disk space optimization
                self._cleanup_disk_space()
                optimization_result['actions_taken'].append('cleanup_disk_space')
            
            # Record optimization
            self.optimization_history.append(optimization_result)
            log_info(f"Automatic {resource_type} optimization triggered: {optimization_result['actions_taken']}")
            
        except Exception as e:
            log_error(f"Automatic optimization failed for {resource_type}: {e}")
    
    def _force_memory_cleanup(self):
        """Force aggressive memory cleanup"""
        try:
            # Force multiple garbage collection cycles
            for _ in range(3):
                gc.collect()
            
            # Clear Python's internal caches
            import sys
            if hasattr(sys, 'intern'):
                sys.intern.clear()
            
            # Clear module cache if possible
            if hasattr(sys, 'modules'):
                for module_name in list(sys.modules.keys()):
                    if module_name.startswith('_') or module_name in ['builtins', 'sys', 'os']:
                        continue
                    try:
                        module = sys.modules[module_name]
                        if hasattr(module, '__dict__'):
                            module.__dict__.clear()
                    except Exception as e:
                        log_debug(f"Could not clear module {module_name}: {e}")
                        pass
            
            log_info("Forced memory cleanup completed")
            
        except Exception as e:
            log_error(f"Forced memory cleanup failed: {e}")
    
    def _reduce_cpu_load(self):
        """Reduce CPU load by adjusting processing priorities"""
        try:
            # Import job manager to adjust processing
            from .job_manager import job_manager
            
            # Reduce concurrent job processing
            if hasattr(job_manager, 'max_workers') and job_manager.max_workers > 1:
                job_manager.max_workers = max(1, job_manager.max_workers - 1)
                log_info(f"Reduced job workers to {job_manager.max_workers}")
            
            # Add delay to reduce CPU usage
            time.sleep(1)
            
        except Exception as e:
            log_error(f"CPU load reduction failed: {e}")
    
    def _optimize_cpu_usage(self):
        """Optimize CPU usage patterns"""
        try:
            # Implement CPU usage optimization strategies
            # This could include adjusting thread priorities, reducing polling frequency, etc.
            pass
            
        except Exception as e:
            log_error(f"CPU optimization failed: {e}")
    
    def _cleanup_disk_space(self):
        """Clean up disk space by removing temporary files"""
        try:
            import tempfile
            import shutil
            
            # Clean up temporary files
            temp_dir = tempfile.gettempdir()
            temp_files_removed = 0
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        # Remove files older than 1 hour
                        if time.time() - os.path.getmtime(file_path) > 3600:
                            os.remove(file_path)
                            temp_files_removed += 1
                    except Exception as e:
                        log_debug(f"Could not remove temp file {file_path}: {e}")
                        continue
            
            if temp_files_removed > 0:
                log_info(f"Cleaned up {temp_files_removed} temporary files")
            
        except Exception as e:
            log_error(f"Disk cleanup failed: {e}")
    
    def configure_auto_optimization(self, enabled: Optional[bool] = None, thresholds: Optional[dict] = None):
        """Configure automatic optimization settings"""
        if enabled is not None:
            self.auto_optimize = enabled
        
        if thresholds:
            self.optimization_thresholds.update(thresholds)
        
        log_info(f"Auto-optimization configured: enabled={self.auto_optimize}, thresholds={self.optimization_thresholds}")
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get optimization history"""
        return list(self.optimization_history)
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)


class SystemMonitor:
    """Monitors system resources like CPU, RAM, and GPU."""

    def __init__(self):
        """Initialize the SystemMonitor."""
        self.gpu_initialized = False
        self.resource_manager = ResourceManager()
        
        if PYNVML_AVAILABLE and pynvml:
            try:
                pynvml.nvmlInit()
                self.gpu_initialized = True
                # Register cleanup with global cleanup system
                try:
                    from run import register_cleanup_function
                    register_cleanup_function(self.cleanup_nvml, "NVML GPU monitoring shutdown")
                except ImportError:
                    pass  # Fallback if run module not available
            except pynvml.NVMLError as e:
                log_warning(f"Could not initialize NVML for GPU monitoring: {e}")
                self.gpu_initialized = False
        else:
            log_warning("pynvml not available - GPU monitoring disabled")
            self.gpu_initialized = False

    def __del__(self):
        """Ensure NVML is shut down properly on exit."""
        self.cleanup_nvml()

    def cleanup_nvml(self):
        """Safely shutdown NVML with error handling"""
        if self.gpu_initialized and PYNVML_AVAILABLE and pynvml:
            try:
                pynvml.nvmlShutdown()
                self.gpu_initialized = False
                log_info("NVML GPU monitoring shutdown successfully")
            except Exception as e:
                log_warning(f"Error during NVML shutdown: {e}")
                # Force reset the flag even if shutdown failed
                self.gpu_initialized = False

    def get_system_usage(self):
        """Get CPU and RAM usage."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'ram_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'ram_used_gb': round(psutil.virtual_memory().used / (1024**3), 2),
            'ram_percent': psutil.virtual_memory().percent,
        }

    def get_gpu_usage(self):
        """Get GPU memory and utilization if available."""
        gpu_info = {'status': 'No GPU detected', 'gpus': []}
        
        # Try NVIDIA GPU detection first
        if self.gpu_initialized and PYNVML_AVAILABLE and pynvml:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    gpus = []
                    for i in range(device_count):
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        # Decode byte strings to standard strings
                        name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

                        # Ensure memory values are integers for calculations
                        total_memory = int(memory_info.total)
                        used_memory = int(memory_info.used)
                        
                        gpus.append({
                            'name': name,
                            'type': 'NVIDIA',
                            'total_memory_gb': round(total_memory / (1024**3), 2),
                            'used_memory_gb': round(used_memory / (1024**3), 2),
                            'memory_usage_percent': round((used_memory / total_memory) * 100, 2) if total_memory > 0 else 0,
                            'gpu_utilization_percent': utilization.gpu,
                            'memory_utilization_percent': utilization.memory,
                            'temperature_celsius': temperature
                        })
                    
                    return {'status': 'success', 'gpus': gpus}
                    
            except pynvml.NVMLError as e:
                gpu_info['status'] = f'NVIDIA driver/SMI error: {str(e)}'
            except Exception as e:
                gpu_info['status'] = f'NVIDIA detection error: {str(e)}'
        
        # Try alternative GPU detection methods
        try:
            # Try to detect GPU via system information
            import platform
            import subprocess
            
            if platform.system() == "Windows":
                # Try Windows GPU detection
                try:
                    result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        gpu_names = [line.strip() for line in lines[1:] if line.strip()]
                        if gpu_names:
                            detected_gpus = []
                            for name in gpu_names:
                                detected_gpus.append({
                                    'name': name,
                                    'type': 'Integrated/Other',
                                    'total_memory_gb': 'Unknown',
                                    'used_memory_gb': 'Unknown',
                                    'memory_usage_percent': 0,
                                    'gpu_utilization_percent': 0,
                                    'memory_utilization_percent': 0,
                                    'temperature_celsius': 'Unknown'
                                })
                            return {'status': 'detected_basic', 'gpus': detected_gpus}
                except Exception:
                    pass
            
            elif platform.system() == "Linux":
                # Try Linux GPU detection
                try:
                    result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        gpu_lines = [line for line in result.stdout.split('\n') 
                                   if 'VGA' in line or 'Display' in line or '3D' in line]
                        if gpu_lines:
                            detected_gpus = []
                            for line in gpu_lines:
                                # Extract GPU name from lspci output
                                parts = line.split(': ')
                                if len(parts) > 1:
                                    gpu_name = parts[1].strip()
                                    detected_gpus.append({
                                        'name': gpu_name,
                                        'type': 'Integrated/Other',
                                        'total_memory_gb': 'Unknown',
                                        'used_memory_gb': 'Unknown',
                                        'memory_usage_percent': 0,
                                        'gpu_utilization_percent': 0,
                                        'memory_utilization_percent': 0,
                                        'temperature_celsius': 'Unknown'
                                    })
                            return {'status': 'detected_basic', 'gpus': detected_gpus}
                except Exception:
                    pass
                    
        except Exception as e:
            gpu_info['status'] = f'Alternative GPU detection failed: {str(e)}'
        
        return gpu_info

    def get_model_memory_estimate(self, params_in_billions: float, quantization_level: str = 'Q4_K_M'):
        """
        Provide a rough estimate of RAM needed to load a model.
        
        Args:
            params_in_billions (float): The number of parameters in the model (e.g., 7.0 for a 7B model).
            quantization_level (str): The quantization level (e.g., 'Q4_K_M', 'Q8_0', 'F16').
            
        Returns:
            float: Estimated RAM in GB.
        """
        quant_multiplier = {
            'F32': 4.0, 'F16': 2.0, 'Q8': 1.0, 'Q6': 0.75,
            'Q5': 0.65, 'Q4': 0.6, 'Q3': 0.5, 'Q2': 0.4
        }
        
        best_multiplier = 1.2
        for key, value in quant_multiplier.items():
            if key.lower() in quantization_level.lower():
                best_multiplier = value
                break
        
        estimated_gb = (params_in_billions * best_multiplier) * 1.20
        return round(estimated_gb, 2)


system_monitor = SystemMonitor()

def get_system_info():
    """Get comprehensive system information for developer tools"""
    try:
        # Get basic system info
        system_usage = system_monitor.get_system_usage()
        gpu_info = system_monitor.get_gpu_usage()
        
        # Get disk usage
        disk_usage = psutil.disk_usage('/')
        
        # Prepare response
        info = {
            'cpu_percent': system_usage['cpu_percent'],
            'memory_percent': system_usage['ram_percent'],
            'memory_used': system_usage['ram_used_gb'] * (1024**3),  # Convert back to bytes
            'memory_total': system_usage['ram_total_gb'] * (1024**3),  # Convert back to bytes
            'disk_percent': (disk_usage.used / disk_usage.total) * 100,
            'disk_used': disk_usage.used,
            'disk_total': disk_usage.total
        }
        
        # Add GPU info if available
        if gpu_info['status'] in ['success', 'detected_basic'] and gpu_info['gpus']:
            gpu = gpu_info['gpus'][0]  # Use first GPU
            info['gpu_name'] = gpu['name']
            
            # Only add utilization data if it's available (NVIDIA GPUs)
            if gpu_info['status'] == 'success':
                info['gpu_percent'] = gpu['gpu_utilization_percent']
                info['gpu_memory_percent'] = gpu['memory_usage_percent']
            else:
                # For basic detection, show that GPU is detected but no utilization data
                info['gpu_percent'] = 0
                info['gpu_memory_percent'] = 0
        else:
            # Show the status for debugging
            info['gpu_status'] = gpu_info['status']
        
        return info
    except Exception as e:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used': 0,
            'memory_total': 0,
            'disk_percent': 0,
            'disk_used': 0,
            'disk_total': 0,
            'error': str(e)
        }

    def optimize(self):
        """
        Perform system optimization tasks.
        Returns a dictionary with optimization results.
        """
        try:
            log_info("System monitor optimization requested")
            
            # Perform basic optimizations
            optimization_results = {
                'success': True,
                'optimizations_applied': [],
                'timestamp': time.time()
            }
            
            # Force garbage collection
            try:
                collected = gc.collect()
                if collected > 0:
                    optimization_results['optimizations_applied'].append(f'Garbage collection: {collected} objects collected')
                    log_info(f"Garbage collection freed {collected} objects")
            except Exception as e:
                log_warning(f"Garbage collection failed: {e}")
            
            # Clear resource history to free memory
            try:
                if hasattr(self.resource_manager, 'resource_history'):
                    for key in self.resource_manager.resource_history:
                        self.resource_manager.resource_history[key].clear()
                    optimization_results['optimizations_applied'].append('Resource history cleared')
                    log_info("Resource history cleared")
            except Exception as e:
                log_warning(f"Failed to clear resource history: {e}")
            
            # Clear old alerts
            try:
                if hasattr(self.resource_manager, 'alerts'):
                    with self.resource_manager.alert_lock:
                        self.resource_manager.alerts.clear()
                    optimization_results['optimizations_applied'].append('Alert history cleared')
                    log_info("Alert history cleared")
            except Exception as e:
                log_warning(f"Failed to clear alerts: {e}")
            
            log_info(f"System monitor optimization completed: {len(optimization_results['optimizations_applied'])} optimizations applied")
            return optimization_results
            
        except Exception as e:
            log_error(f"System monitor optimization failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'optimizations_applied': [],
                'timestamp': time.time()
            }

def get_system_monitor():
    """Provide singleton access for API imports."""
    return system_monitor