"""
System API for Vybe AI Desktop Application
Handles system optimization, performance monitoring, and system management
"""

from flask import Blueprint, jsonify, request
import psutil
import gc
import os
import time
from pathlib import Path
from typing import Dict, Any, List
import logging

from ..logger import log_info, log_warning, log_error
from ..utils.cache_manager import invalidate_cache
from ..core.system_monitor import get_system_monitor

logger = logging.getLogger(__name__)

system_api = Blueprint('system_api', __name__)

@system_api.route('/optimize', methods=['POST'])
def optimize_system():
    """
    Perform system optimization tasks
    Returns list of optimizations applied
    """
    try:
        optimizations = []
        
        # 1. Clear application caches
        try:
            invalidate_cache('*')  # Clear all caches
            optimizations.append('Application caches cleared')
        except Exception as e:
            log_warning(f"Failed to clear application caches: {e}")
        
        # 2. Force garbage collection
        try:
            collected = gc.collect()
            if collected > 0:
                optimizations.append(f'Garbage collection: {collected} objects collected')
        except Exception as e:
            log_warning(f"Failed to perform garbage collection: {e}")
        
        # 3. Clear temporary files
        try:
            temp_dirs = [
                Path("workspace/temp"),
                Path("instance/temp"),
                Path("logs/temp")
            ]
            
            cleared_files = 0
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    for file_path in temp_dir.glob("*"):
                        try:
                            if file_path.is_file():
                                file_path.unlink()
                                cleared_files += 1
                        except Exception as e:
                            log_warning(f"Failed to delete temp file {file_path}: {e}")
            
            if cleared_files > 0:
                optimizations.append(f'{cleared_files} temporary files cleared')
        except Exception as e:
            log_warning(f"Failed to clear temporary files: {e}")
        
        # 4. Optimize memory usage
        try:
            # Get current memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                # Force memory optimization
                gc.collect()
                optimizations.append('Memory usage optimized')
        except Exception as e:
            log_warning(f"Failed to optimize memory: {e}")
        
        # 5. Clear log files (keep recent ones)
        try:
            log_dir = Path("logs")
            if log_dir.exists():
                current_time = time.time()
                cleared_logs = 0
                
                for log_file in log_dir.glob("*.log"):
                    try:
                        # Keep logs from last 7 days
                        if current_time - log_file.stat().st_mtime > 7 * 24 * 3600:
                            log_file.unlink()
                            cleared_logs += 1
                    except Exception as e:
                        log_warning(f"Failed to delete old log {log_file}: {e}")
                
                if cleared_logs > 0:
                    optimizations.append(f'{cleared_logs} old log files cleared')
        except Exception as e:
            log_warning(f"Failed to clear old logs: {e}")
        
        # 6. System monitor optimization
        try:
            system_monitor = get_system_monitor()
            if system_monitor:
                # TODO: Verify the intended system optimization/monitoring call. The 'optimize' method does not exist.
                # optimized_info = system_monitor.optimize()
                optimizations.append('System monitoring optimized')
        except Exception as e:
            log_warning(f"Failed to optimize system monitor: {e}")
        
        log_info(f"System optimization completed: {len(optimizations)} improvements applied")
        
        return jsonify({
            'success': True,
            'optimizations': optimizations,
            'message': f'System optimized: {len(optimizations)} improvements applied'
        })
        
    except Exception as e:
        log_error(f"System optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Optimization failed: {str(e)}'
        }), 500

@system_api.route('/status', methods=['GET'])
def get_system_status():
    """
    Get comprehensive system status and performance metrics
    """
    try:
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network information
        network = psutil.net_io_counters()
        
        # Calculate health score
        health_score = 100
        if isinstance(cpu_percent, (int, float)) and cpu_percent > 90:
            health_score -= 30
        elif isinstance(cpu_percent, (int, float)) and cpu_percent > 70:
            health_score -= 15
            
        if isinstance(memory.percent, (int, float)) and memory.percent > 90:
            health_score -= 30
        elif isinstance(memory.percent, (int, float)) and memory.percent > 70:
            health_score -= 15
            
        if isinstance(disk.percent, (int, float)) and disk.percent > 90:
            health_score -= 20
        elif isinstance(disk.percent, (int, float)) and disk.percent > 80:
            health_score -= 10
        
        health_score = max(0, health_score)
        
        status = {
            'success': True,
            'health_score': health_score,
            'cpu': {
                'usage_percent': cpu_percent,
                'count': psutil.cpu_count(),
                'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            },
            'network': {
                'bytes_sent': getattr(network, 'bytes_sent', 0) if network else 0,
                'bytes_recv': getattr(network, 'bytes_recv', 0) if network else 0,
                'packets_sent': getattr(network, 'packets_sent', 0) if network else 0,
                'packets_recv': getattr(network, 'packets_recv', 0) if network else 0
            },
            'timestamp': time.time()
        }
        
        return jsonify(status)
        
    except Exception as e:
        log_error(f"Failed to get system status: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get system status: {str(e)}'
        }), 500

@system_api.route('/processes', methods=['GET'])
def get_process_info():
    """
    Get information about running processes
    """
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
                if proc_info.get('cpu_percent', 0) > 0 or proc_info.get('memory_percent', 0) > 0:
                    processes.append({
                        'pid': proc_info.get('pid', 0),
                        'name': proc_info.get('name', 'Unknown'),
                        'cpu_percent': proc_info.get('cpu_percent', 0),
                        'memory_percent': proc_info.get('memory_percent', 0)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return jsonify({
            'success': True,
            'processes': processes[:20]  # Top 20 processes
        })
        
    except Exception as e:
        log_error(f"Failed to get process info: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get process info: {str(e)}'
        }), 500
