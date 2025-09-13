"""
Resource Cleanup Manager for Vybe Application
Provides centralized management of background threads, global variables, and resource cleanup.
"""

import threading
import time
import gc
import psutil
from typing import Dict, List, Any, Optional, Callable, TypedDict
from datetime import datetime
import logging

from ..logger import log_info, log_warning, log_error

logger = logging.getLogger(__name__)


class ResourceCleanupManager:
    """
    Centralized resource cleanup manager that tracks and properly shuts down
    all background threads, global variables, and system resources.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ResourceCleanupManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the resource cleanup manager"""
        self.background_threads: Dict[str, threading.Thread] = {}
        self.global_variables: Dict[str, Any] = {}
        self.cleanup_handlers: List[Dict[str, Any]] = []
        self.is_shutdown = False
        self.cleanup_lock = threading.Lock()
        
        # Register default cleanup handlers
        self._register_default_handlers()
        
        logger.info("Resource cleanup manager initialized")
    
    def _register_default_handlers(self):
        """Register default cleanup handlers for common resources"""
        try:
            # Cache manager cleanup
            from .cache_manager import cleanup_cache_manager
            self.register_cleanup_handler("cache_manager", cleanup_cache_manager, priority=1)
            
            # Resource manager cleanup
            from ..core.system_monitor import SystemMonitor
            self.register_cleanup_handler("system_monitor", self._cleanup_system_monitor, priority=2)
            
            # Job manager cleanup
            from ..core.job_manager import JobManager
            self.register_cleanup_handler("job_manager", self._cleanup_job_manager, priority=3)
            
            # Installation monitor cleanup
            from ..core.installation_monitor import installation_monitor
            self.register_cleanup_handler("installation_monitor", installation_monitor.stop_monitoring, priority=4)
            
        except Exception as e:
            logger.warning(f"Failed to register some default cleanup handlers: {e}")
    
    def register_background_thread(self, name: str, thread: threading.Thread):
        """Register a background thread for cleanup"""
        with self.cleanup_lock:
            self.background_threads[name] = thread
            logger.debug(f"Registered background thread: {name}")
    
    def unregister_background_thread(self, name: str):
        """Unregister a background thread"""
        with self.cleanup_lock:
            if name in self.background_threads:
                del self.background_threads[name]
                logger.debug(f"Unregistered background thread: {name}")
    
    def register_global_variable(self, name: str, variable: Any, cleanup_func: Optional[Callable] = None):
        """Register a global variable for cleanup"""
        with self.cleanup_lock:
            self.global_variables[name] = {
                'variable': variable,
                'cleanup_func': cleanup_func
            }
            logger.debug(f"Registered global variable: {name}")
    
    def unregister_global_variable(self, name: str):
        """Unregister a global variable"""
        with self.cleanup_lock:
            if name in self.global_variables:
                del self.global_variables[name]
                logger.debug(f"Unregistered global variable: {name}")
    
    def register_cleanup_handler(self, name: str, handler: Callable, priority: int = 5):
        """Register a cleanup handler function"""
        with self.cleanup_lock:
            handler_info = {
                'name': name,
                'handler': handler,
                'priority': priority
            }
            self.cleanup_handlers.append(handler_info)
            # Sort by priority (lower number = higher priority)
            self.cleanup_handlers.sort(key=lambda x: x['priority'])
            logger.debug(f"Registered cleanup handler: {name} (priority: {priority})")
    
    def register_file_handle(self, name: str, file_handle):
        """Register a file handle for cleanup"""
        def close_file():
            try:
                if hasattr(file_handle, 'close'):
                    file_handle.close()
                logger.debug(f"Closed file handle: {name}")
            except Exception as e:
                logger.error(f"Error closing file handle {name}: {e}")
        
        self.register_cleanup_handler(f"file_handle_{name}", close_file, priority=1)
    
    def get_memory_usage(self):
        """Get current memory usage statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss / (1024 * 1024),  # MB
                'vms': memory_info.vms / (1024 * 1024),  # MB
                'percent': process.memory_percent(),
                'available': psutil.virtual_memory().available / (1024 * 1024),  # MB
                'total': psutil.virtual_memory().total / (1024 * 1024)  # MB
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def unregister_cleanup_handler(self, name: str):
        """Unregister a cleanup handler"""
        with self.cleanup_lock:
            self.cleanup_handlers = [h for h in self.cleanup_handlers if h['name'] != name]
            logger.debug(f"Unregistered cleanup handler: {name}")
    
    def cleanup_all_resources(self, force: bool = False):
        """Clean up all registered resources"""
        if self.is_shutdown and not force:
            return
        
        logger.info("Starting comprehensive resource cleanup...")
        start_time = time.time()
        
        try:
            # Stop all background threads
            self._stop_all_background_threads()
            
            # Execute cleanup handlers in priority order
            self._execute_cleanup_handlers()
            
            # Clean up global variables
            self._cleanup_global_variables()
            
            # Force garbage collection
            self._force_garbage_collection()
            
            # Mark as shutdown
            self.is_shutdown = True
            
            cleanup_time = time.time() - start_time
            logger.info(f"Resource cleanup completed in {cleanup_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
    
    def _stop_all_background_threads(self):
        """Stop all registered background threads"""
        logger.info(f"Stopping {len(self.background_threads)} background threads...")
        
        with self.cleanup_lock:
            for name, thread in self.background_threads.items():
                try:
                    if thread.is_alive():
                        logger.debug(f"Stopping thread: {name}")
                        # Note: We can't directly stop threads, but we can wait for them
                        thread.join(timeout=5)
                        if thread.is_alive():
                            logger.warning(f"Thread {name} did not stop within timeout")
                except Exception as e:
                    logger.error(f"Error stopping thread {name}: {e}")
            
            # Clear the thread registry
            self.background_threads.clear()
    
    def _execute_cleanup_handlers(self):
        """Execute all registered cleanup handlers"""
        logger.info(f"Executing {len(self.cleanup_handlers)} cleanup handlers...")
        
        with self.cleanup_lock:
            for handler_info in self.cleanup_handlers:
                try:
                    name = handler_info['name']
                    handler = handler_info['handler']
                    priority = handler_info['priority']
                    
                    logger.debug(f"Executing cleanup handler: {name} (priority: {priority})")
                    handler()
                    
                except Exception as e:
                    logger.error(f"Error executing cleanup handler {name}: {e}")
    
    def _cleanup_global_variables(self):
        """Clean up registered global variables"""
        logger.info(f"Cleaning up {len(self.global_variables)} global variables...")
        
        with self.cleanup_lock:
            for name, var_info in self.global_variables.items():
                try:
                    variable = var_info['variable']
                    cleanup_func = var_info['cleanup_func']
                    
                    if cleanup_func:
                        logger.debug(f"Cleaning up global variable: {name}")
                        cleanup_func(variable)
                    else:
                        logger.debug(f"Clearing global variable: {name}")
                        variable = None
                        
                except Exception as e:
                    logger.error(f"Error cleaning up global variable {name}: {e}")
            
            # Clear the variable registry
            self.global_variables.clear()
    
    def _force_garbage_collection(self):
        """Force garbage collection to free memory"""
        try:
            logger.info("Forcing garbage collection...")
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            
            # Force garbage collection multiple times
            for i in range(3):
                collected = gc.collect()
                if collected > 0:
                    logger.debug(f"Garbage collection cycle {i+1} collected {collected} objects")
            
            # Get final memory usage
            final_memory = process.memory_info().rss
            memory_freed = initial_memory - final_memory
            
            if memory_freed > 0:
                logger.info(f"Garbage collection freed {memory_freed / (1024*1024):.2f} MB")
            else:
                logger.info("Garbage collection completed")
                
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
    
    def _cleanup_system_monitor(self):
        """Clean up system monitor resources"""
        try:
            from ..core.system_monitor import SystemMonitor
            # This would need to be implemented in SystemMonitor
            logger.debug("System monitor cleanup called")
        except Exception as e:
            logger.error(f"Error cleaning up system monitor: {e}")
    
    def _cleanup_job_manager(self):
        """Clean up job manager resources"""
        try:
            from ..core.job_manager import JobManager
            job_manager = JobManager()
            if job_manager.is_running():
                job_manager.stop()
                logger.debug("Job manager stopped")
        except Exception as e:
            logger.error(f"Error cleaning up job manager: {e}")

    def monitor_memory_usage(self, threshold_mb: float = 500.0):
        """Monitor memory usage and log warnings if threshold exceeded"""
        try:
            memory_stats = self.get_memory_usage()
            if memory_stats and memory_stats.get('rss', 0) > threshold_mb:
                logger.warning(f"High memory usage detected: {memory_stats['rss']:.2f} MB "
                             f"({memory_stats.get('percent', 0):.1f}% of system)")
                return True
            return False
        except Exception as e:
            logger.error(f"Error monitoring memory usage: {e}")
            return False

    def force_memory_cleanup(self):
        """Force immediate memory cleanup without full shutdown"""
        try:
            logger.info("Forcing immediate memory cleanup...")
            initial_memory = self.get_memory_usage()
            
            # Force garbage collection
            self._force_garbage_collection()
            
            # Try to compact memory (Python-specific)
            try:
                import ctypes
                if hasattr(ctypes, 'windll'):  # Windows
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
            except Exception:
                pass  # Not critical if this fails
            
            final_memory = self.get_memory_usage()
            if initial_memory and final_memory:
                freed = initial_memory.get('rss', 0) - final_memory.get('rss', 0)
                if freed > 0:
                    logger.info(f"Memory cleanup freed {freed:.2f} MB")
                    
        except Exception as e:
            logger.error(f"Error during forced memory cleanup: {e}")

    def cleanup_temp_files(self, temp_dir: Optional[str] = None):
        """Clean up temporary files"""
        import tempfile
        import os
        
        try:
            if temp_dir is None:
                temp_dir = tempfile.gettempdir()
            
            logger.info(f"Cleaning up temporary files in {temp_dir}")
            cleaned_count = 0
            
            # Look for Vybe-related temp files
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if 'vybe' in file.lower() or 'tmp' in file.lower():
                        try:
                            file_path = os.path.join(root, file)
                            # Only delete files older than 1 hour
                            if os.path.getctime(file_path) < time.time() - 3600:
                                os.remove(file_path)
                                cleaned_count += 1
                        except Exception:
                            continue  # Skip files we can't delete
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} temporary files")
                
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get status of all managed resources"""
        with self.cleanup_lock:
            return {
                'background_threads': {
                    name: {
                        'alive': thread.is_alive(),
                        'daemon': thread.daemon,
                        'name': thread.name
                    }
                    for name, thread in self.background_threads.items()
                },
                'global_variables': {
                    name: {
                        'has_cleanup_func': var_info['cleanup_func'] is not None,
                        'type': type(var_info['variable']).__name__
                    }
                    for name, var_info in self.global_variables.items()
                },
                'cleanup_handlers': len(self.cleanup_handlers),
                'is_shutdown': self.is_shutdown
            }
    
    def monitor_resource_usage(self):
        """Monitor and log resource usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            logger.info(f"Resource usage - Memory: {memory_info.rss / (1024*1024):.2f} MB, "
                       f"CPU: {cpu_percent:.1f}%, Active threads: {len(self.background_threads)}")
            
        except Exception as e:
            logger.error(f"Error monitoring resource usage: {e}")


# Global instance
resource_cleanup_manager = ResourceCleanupManager()


# Convenience functions
def register_background_thread(name: str, thread: threading.Thread):
    """Register a background thread for cleanup"""
    resource_cleanup_manager.register_background_thread(name, thread)


def register_global_variable(name: str, variable: Any, cleanup_func: Optional[Callable] = None):
    """Register a global variable for cleanup"""
    resource_cleanup_manager.register_global_variable(name, variable, cleanup_func)


def register_thread_cleanup(thread: threading.Thread, name: str, cleanup_func: Optional[Callable] = None):
    """Register a thread for cleanup"""
    resource_cleanup_manager.register_background_thread(name, thread)
    if cleanup_func:
        resource_cleanup_manager.register_cleanup_handler(f"{name}_cleanup", cleanup_func)


def register_cleanup_handler(name: str, handler: Callable, priority: int = 5):
    """Register a cleanup handler function"""
    resource_cleanup_manager.register_cleanup_handler(name, handler, priority)


def cleanup_all_resources(force: bool = False):
    """Clean up all registered resources"""
    resource_cleanup_manager.cleanup_all_resources(force)


def get_resource_status() -> Dict[str, Any]:
    """Get status of all managed resources"""
    return resource_cleanup_manager.get_resource_status()


# Automatic cleanup on application shutdown
import atexit
atexit.register(cleanup_all_resources)
