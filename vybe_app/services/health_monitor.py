"""
System Health Dashboard
Comprehensive system monitoring and health tracking for Vybe AI.
"""
import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import current_app, jsonify
import logging
import json
import os
import sqlite3
from collections import deque

from ..utils.error_handling import ApplicationError, ErrorCode
from ..models import db

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """Comprehensive system health monitoring service"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.health_data = {
            'cpu': deque(maxlen=100),
            'memory': deque(maxlen=100),
            'disk': deque(maxlen=100),
            'network': deque(maxlen=100),
            'processes': deque(maxlen=50),
            'errors': deque(maxlen=200)
        }
        self.alerts = deque(maxlen=100)
        self.start_time = datetime.utcnow()
        
        # Thresholds for alerts
        self.thresholds = {
            'cpu_warning': 80,
            'cpu_critical': 95,
            'memory_warning': 80,
            'memory_critical': 95,
            'disk_warning': 85,
            'disk_critical': 95,
            'response_time_warning': 5.0,
            'response_time_critical': 10.0
        }
    
    def start_monitoring(self):
        """Start background monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("System health monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                timestamp = datetime.utcnow()
                
                # Collect system metrics
                cpu_data = self._get_cpu_metrics()
                memory_data = self._get_memory_metrics()
                disk_data = self._get_disk_metrics()
                network_data = self._get_network_metrics()
                process_data = self._get_process_metrics()
                
                # Store data with timestamp
                self.health_data['cpu'].append({
                    'timestamp': timestamp.isoformat(),
                    **cpu_data
                })
                
                self.health_data['memory'].append({
                    'timestamp': timestamp.isoformat(),
                    **memory_data
                })
                
                self.health_data['disk'].append({
                    'timestamp': timestamp.isoformat(),
                    **disk_data
                })
                
                self.health_data['network'].append({
                    'timestamp': timestamp.isoformat(),
                    **network_data
                })
                
                self.health_data['processes'].append({
                    'timestamp': timestamp.isoformat(),
                    **process_data
                })
                
                # Check for alerts
                self._check_alerts(cpu_data, memory_data, disk_data)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self._record_error('monitoring_loop', str(e))
            
            time.sleep(10)  # Monitor every 10 seconds
    
    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """Get CPU usage metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Load average is Unix-specific
            try:
                load_avg = getattr(os, 'getloadavg', lambda: [0, 0, 0])()
            except (AttributeError, OSError):
                load_avg = [0, 0, 0]
            
            return {
                'usage_percent': cpu_percent,
                'core_count': cpu_count,
                'frequency_mhz': cpu_freq.current if cpu_freq else 0,
                'load_average_1m': load_avg[0],
                'load_average_5m': load_avg[1],
                'load_average_15m': load_avg[2]
            }
        except Exception as e:
            logger.error(f"Error getting CPU metrics: {e}")
            return {'usage_percent': 0, 'core_count': 0, 'frequency_mhz': 0}
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total_bytes': memory.total,
                'available_bytes': memory.available,
                'used_bytes': memory.used,
                'usage_percent': memory.percent,
                'swap_total_bytes': swap.total,
                'swap_used_bytes': swap.used,
                'swap_percent': swap.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory metrics: {e}")
            return {'total_bytes': 0, 'used_bytes': 0, 'usage_percent': 0}
    
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """Get disk usage metrics"""
        try:
            disk_usage = psutil.disk_usage('/')
            
            # Get disk I/O stats safely
            try:
                disk_io = psutil.disk_io_counters()
                read_bytes = getattr(disk_io, 'read_bytes', 0) if disk_io else 0
                write_bytes = getattr(disk_io, 'write_bytes', 0) if disk_io else 0
                read_count = getattr(disk_io, 'read_count', 0) if disk_io else 0
                write_count = getattr(disk_io, 'write_count', 0) if disk_io else 0
            except Exception:
                read_bytes = write_bytes = read_count = write_count = 0
            
            return {
                'total_bytes': disk_usage.total,
                'used_bytes': disk_usage.used,
                'free_bytes': disk_usage.free,
                'usage_percent': (disk_usage.used / disk_usage.total) * 100,
                'read_bytes': read_bytes,
                'write_bytes': write_bytes,
                'read_count': read_count,
                'write_count': write_count
            }
        except Exception as e:
            logger.error(f"Error getting disk metrics: {e}")
            return {'total_bytes': 0, 'used_bytes': 0, 'usage_percent': 0}
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """Get network usage metrics"""
        try:
            # Get network I/O stats safely
            try:
                net_io = psutil.net_io_counters()
                bytes_sent = getattr(net_io, 'bytes_sent', 0) if net_io else 0
                bytes_recv = getattr(net_io, 'bytes_recv', 0) if net_io else 0
                packets_sent = getattr(net_io, 'packets_sent', 0) if net_io else 0
                packets_recv = getattr(net_io, 'packets_recv', 0) if net_io else 0
            except Exception:
                bytes_sent = bytes_recv = packets_sent = packets_recv = 0
            
            net_connections = len(psutil.net_connections())
            
            return {
                'bytes_sent': bytes_sent,
                'bytes_recv': bytes_recv,
                'packets_sent': packets_sent,
                'packets_recv': packets_recv,
                'connections_count': net_connections
            }
        except Exception as e:
            logger.error(f"Error getting network metrics: {e}")
            return {'bytes_sent': 0, 'bytes_recv': 0, 'connections_count': 0}
    
    def _get_process_metrics(self) -> Dict[str, Any]:
        """Get process-related metrics"""
        try:
            process_count = len(psutil.pids())
            current_process = psutil.Process()
            
            return {
                'total_processes': process_count,
                'vybe_memory_mb': current_process.memory_info().rss / (1024 * 1024),
                'vybe_cpu_percent': current_process.cpu_percent(),
                'vybe_threads': current_process.num_threads(),
                'vybe_open_files': len(current_process.open_files())
            }
        except Exception as e:
            logger.error(f"Error getting process metrics: {e}")
            return {'total_processes': 0, 'vybe_memory_mb': 0}
    
    def _check_alerts(self, cpu_data: Dict, memory_data: Dict, disk_data: Dict):
        """Check metrics against thresholds and generate alerts"""
        timestamp = datetime.utcnow()
        
        # CPU alerts
        if cpu_data.get('usage_percent', 0) > self.thresholds['cpu_critical']:
            self._create_alert('critical', 'CPU usage critical', 
                             f"CPU usage at {cpu_data['usage_percent']:.1f}%", timestamp)
        elif cpu_data.get('usage_percent', 0) > self.thresholds['cpu_warning']:
            self._create_alert('warning', 'CPU usage high', 
                             f"CPU usage at {cpu_data['usage_percent']:.1f}%", timestamp)
        
        # Memory alerts
        if memory_data.get('usage_percent', 0) > self.thresholds['memory_critical']:
            self._create_alert('critical', 'Memory usage critical', 
                             f"Memory usage at {memory_data['usage_percent']:.1f}%", timestamp)
        elif memory_data.get('usage_percent', 0) > self.thresholds['memory_warning']:
            self._create_alert('warning', 'Memory usage high', 
                             f"Memory usage at {memory_data['usage_percent']:.1f}%", timestamp)
        
        # Disk alerts
        if disk_data.get('usage_percent', 0) > self.thresholds['disk_critical']:
            self._create_alert('critical', 'Disk usage critical', 
                             f"Disk usage at {disk_data['usage_percent']:.1f}%", timestamp)
        elif disk_data.get('usage_percent', 0) > self.thresholds['disk_warning']:
            self._create_alert('warning', 'Disk usage high', 
                             f"Disk usage at {disk_data['usage_percent']:.1f}%", timestamp)
    
    def _create_alert(self, level: str, title: str, message: str, timestamp: datetime):
        """Create a system alert"""
        alert = {
            'id': f"alert_{int(timestamp.timestamp())}",
            'level': level,
            'title': title,
            'message': message,
            'timestamp': timestamp.isoformat(),
            'acknowledged': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"System alert [{level}]: {title} - {message}")
    
    def _record_error(self, component: str, error_message: str):
        """Record system error"""
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'component': component,
            'message': error_message,
            'severity': 'error'
        }
        
        self.health_data['errors'].append(error_data)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status summary"""
        try:
            # Get latest metrics
            latest_cpu = list(self.health_data['cpu'])[-1] if self.health_data['cpu'] else {}
            latest_memory = list(self.health_data['memory'])[-1] if self.health_data['memory'] else {}
            latest_disk = list(self.health_data['disk'])[-1] if self.health_data['disk'] else {}
            latest_network = list(self.health_data['network'])[-1] if self.health_data['network'] else {}
            latest_process = list(self.health_data['processes'])[-1] if self.health_data['processes'] else {}
            
            # Calculate uptime
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Get database status
            db_status = self._get_database_status()
            
            # Determine overall health
            overall_health = self._calculate_overall_health(latest_cpu, latest_memory, latest_disk)
            
            return {
                'overall_health': overall_health,
                'uptime_seconds': uptime_seconds,
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': latest_cpu,
                'memory': latest_memory,
                'disk': latest_disk,
                'network': latest_network,
                'processes': latest_process,
                'database': db_status,
                'active_alerts': len([a for a in self.alerts if not a.get('acknowledged', False)]),
                'monitoring_active': self.monitoring
            }
        except Exception as e:
            logger.error(f"Error getting current status: {e}")
            return {
                'overall_health': 'unknown',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _get_database_status(self) -> Dict[str, Any]:
        """Get database connection status"""
        try:
            # Test database connection with proper SQLAlchemy syntax
            start_time = time.time()
            # Use a simple query that's compatible with SQLAlchemy 2.x
            result = db.session.execute(db.text('SELECT 1 as test')).fetchone()
            response_time = time.time() - start_time
            
            return {
                'status': 'connected' if result else 'disconnected',
                'response_time_ms': response_time * 1000,
                'last_check': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _calculate_overall_health(self, cpu_data: Dict, memory_data: Dict, disk_data: Dict) -> str:
        """Calculate overall system health status"""
        try:
            cpu_usage = cpu_data.get('usage_percent', 0)
            memory_usage = memory_data.get('usage_percent', 0)
            disk_usage = disk_data.get('usage_percent', 0)
            
            # Check for critical conditions
            if (cpu_usage > self.thresholds['cpu_critical'] or 
                memory_usage > self.thresholds['memory_critical'] or 
                disk_usage > self.thresholds['disk_critical']):
                return 'critical'
            
            # Check for warning conditions
            if (cpu_usage > self.thresholds['cpu_warning'] or 
                memory_usage > self.thresholds['memory_warning'] or 
                disk_usage > self.thresholds['disk_warning']):
                return 'warning'
            
            return 'healthy'
        except Exception:
            return 'unknown'
    
    def get_historical_data(self, metric: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        if metric not in self.health_data:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            data for data in self.health_data[metric]
            if datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    def get_alerts(self, include_acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get system alerts"""
        if include_acknowledged:
            return list(self.alerts)
        else:
            return [alert for alert in self.alerts if not alert.get('acknowledged', False)]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.get('id') == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.utcnow().isoformat()
                return True
        return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of various services"""
        services = {}
        
        # Check Flask app
        try:
            services['flask'] = {
                'status': 'running' if current_app else 'stopped',
                'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds()
            }
        except Exception as e:
            services['flask'] = {'status': 'error', 'error': str(e)}
        
        # Check database
        services['database'] = self._get_database_status()
        
        # Check file system
        try:
            test_file = '/tmp/vybe_health_test'
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            services['filesystem'] = {'status': 'healthy'}
        except Exception as e:
            services['filesystem'] = {'status': 'error', 'error': str(e)}
        
        return services
    
    def update_thresholds(self, new_thresholds: Dict[str, float]) -> bool:
        """Update alert thresholds"""
        try:
            for key, value in new_thresholds.items():
                if key in self.thresholds and isinstance(value, (int, float)):
                    self.thresholds[key] = float(value)
            logger.info(f"Updated thresholds: {new_thresholds}")
            return True
        except Exception as e:
            logger.error(f"Error updating thresholds: {e}")
            return False


# Global monitor instance
health_monitor = SystemHealthMonitor()


def init_health_monitoring():
    """Initialize and start health monitoring"""
    health_monitor.start_monitoring()
    logger.info("System health monitoring initialized")


def get_health_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive health dashboard data"""
    return {
        'current_status': health_monitor.get_current_status(),
        'recent_alerts': health_monitor.get_alerts(),
        'service_status': health_monitor.get_service_status(),
        'cpu_history': health_monitor.get_historical_data('cpu', 1),
        'memory_history': health_monitor.get_historical_data('memory', 1),
        'thresholds': health_monitor.thresholds
    }
