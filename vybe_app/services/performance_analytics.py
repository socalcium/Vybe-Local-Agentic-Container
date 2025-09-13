"""
Performance Analytics Service - System performance monitoring and analytics
Provides request analytics, user behavior tracking, and performance metrics
"""

import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import statistics
import psutil

from flask import request, g, current_app
from sqlalchemy import and_, func, desc

from ..models import db, User, UserSession, UserActivity
from ..utils.error_handling import ApplicationError, ErrorCode
from ..utils.input_validation import AdvancedInputValidator


class MetricType(Enum):
    """Performance metric types"""
    REQUEST_COUNT = "request_count"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DATABASE_QUERIES = "database_queries"
    USER_ACTIONS = "user_actions"
    MODEL_INFERENCE = "model_inference"


class TimeWindow(Enum):
    """Time window for analytics"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    timestamp: datetime
    metric_type: MetricType
    value: float
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = {}


@dataclass
class RequestMetrics:
    """Request-level metrics"""
    start_time: float
    end_time: Optional[float] = None
    status_code: Optional[int] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    response_size: Optional[int] = None
    database_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    error_type: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time period"""
    time_window: TimeWindow
    start_time: datetime
    end_time: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    error_rate: float = 0.0
    avg_memory_usage: float = 0.0
    avg_cpu_usage: float = 0.0
    top_endpoints: Optional[List[Dict[str, Any]]] = None
    top_errors: Optional[List[Dict[str, Any]]] = None
    unique_users: int = 0

    def __post_init__(self):
        if self.top_endpoints is None:
            self.top_endpoints = []
        if self.top_errors is None:
            self.top_errors = []


class PerformanceAnalytics:
    """Main performance analytics service"""

    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self.metrics_buffer = deque(maxlen=10000)  # In-memory buffer for recent metrics
        self.request_metrics: Dict[str, RequestMetrics] = {}  # Active requests
        self.aggregated_cache: Dict[str, AggregatedMetrics] = {}  # Cached aggregations
        self._lock = threading.RLock()
        
        # Performance tracking using Any type to avoid complex type checking
        self.endpoint_stats: Dict[str, Any] = defaultdict(lambda: {
            'count': 0, 'total_time': 0.0, 'errors': 0, 'response_times': deque(maxlen=1000)
        })
        self.user_stats: Dict[str, Any] = defaultdict(lambda: {
            'requests': 0, 'last_seen': None, 'endpoints': set(), 'errors': 0
        })
        self.error_stats: Dict[str, int] = defaultdict(int)
        
        # System metrics tracking
        self.system_metrics = deque(maxlen=1000)
        self._start_system_monitoring()

    def _start_system_monitoring(self):
        """Start background system monitoring"""
        def monitor_system():
            while True:
                try:
                    self._collect_system_metrics()
                    time.sleep(60)  # Collect every minute
                except Exception as e:
                    print(f"System monitoring error: {e}")
                    time.sleep(60)

        monitoring_thread = threading.Thread(target=monitor_system, daemon=True)
        monitoring_thread.start()

    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk I/O (handle potential AttributeError)
            disk_io = psutil.disk_io_counters()
            
            # Network I/O (handle potential AttributeError)  
            network_io = psutil.net_io_counters()
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            metrics = {
                'timestamp': datetime.utcnow(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / 1024 / 1024,
                'memory_available_mb': memory.available / 1024 / 1024,
                'disk_read_mb': getattr(disk_io, 'read_bytes', 0) / 1024 / 1024 if disk_io else 0,
                'disk_write_mb': getattr(disk_io, 'write_bytes', 0) / 1024 / 1024 if disk_io else 0,
                'network_sent_mb': getattr(network_io, 'bytes_sent', 0) / 1024 / 1024 if network_io else 0,
                'network_recv_mb': getattr(network_io, 'bytes_recv', 0) / 1024 / 1024 if network_io else 0,
                'process_memory_mb': process_memory.rss / 1024 / 1024,
                'process_cpu_percent': process.cpu_percent()
            }
            
            with self._lock:
                self.system_metrics.append(metrics)
                
        except Exception as e:
            print(f"Failed to collect system metrics: {e}")

    def start_request_tracking(self, request_id: Optional[str] = None) -> str:
        """Start tracking a request"""
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}_{id(request)}"
        
        # Get request info
        endpoint = getattr(request, 'endpoint', 'unknown')
        method = getattr(request, 'method', 'unknown')
        user_id = getattr(g, 'current_user_id', None)
        ip_address = request.remote_addr if hasattr(request, 'remote_addr') else None
        user_agent = request.headers.get('User-Agent') if hasattr(request, 'headers') else None
        
        metrics = RequestMetrics(
            start_time=time.time(),
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        with self._lock:
            self.request_metrics[request_id] = metrics
        
        return request_id

    def end_request_tracking(self, request_id: str, status_code: int = 200, 
                           response_size: Optional[int] = None, error_type: Optional[str] = None):
        """End tracking a request and record metrics"""
        with self._lock:
            if request_id not in self.request_metrics:
                return
            
            metrics = self.request_metrics[request_id]
            metrics.end_time = time.time()
            metrics.status_code = status_code
            metrics.response_size = response_size
            metrics.error_type = error_type
            
            # Calculate response time
            response_time = metrics.end_time - metrics.start_time
            
            # Update endpoint statistics using Any type handling
            endpoint_key = f"{metrics.method}:{metrics.endpoint}"
            endpoint_stat = self.endpoint_stats[endpoint_key]
            endpoint_stat['count'] += 1
            endpoint_stat['total_time'] += response_time
            endpoint_stat['response_times'].append(response_time)
            
            if status_code >= 400:
                endpoint_stat['errors'] += 1
                if error_type:
                    self.error_stats[error_type] += 1
            
            # Update user statistics using Any type handling
            if metrics.user_id:
                user_stat = self.user_stats[metrics.user_id]
                user_stat['requests'] += 1
                user_stat['last_seen'] = datetime.utcnow()
                user_stat['endpoints'].add(endpoint_key)
                if status_code >= 400:
                    user_stat['errors'] += 1
            
            # Add to metrics buffer
            metric = PerformanceMetric(
                timestamp=datetime.fromtimestamp(metrics.start_time),
                metric_type=MetricType.RESPONSE_TIME,
                value=response_time,
                metadata={
                    'endpoint': metrics.endpoint,
                    'method': metrics.method,
                    'status_code': status_code,
                    'user_id': metrics.user_id,
                    'response_size': response_size,
                    'error_type': error_type
                },
                tags={
                    'endpoint': endpoint_key,
                    'status': 'success' if status_code < 400 else 'error'
                }
            )
            
            self.metrics_buffer.append(metric)
            
            # Clean up
            del self.request_metrics[request_id]

    def record_user_action(self, user_id: str, action: str, 
                          metadata: Optional[Dict[str, Any]] = None):
        """Record a user action for analytics"""
        try:
            # Create user activity record
            user_activity = UserActivity()
            user_activity.user_id = user_id
            user_activity.activity_type = action
            user_activity.created_at = datetime.utcnow()
            user_activity.details = json.dumps(metadata or {})
            
            db.session.add(user_activity)
            db.session.commit()
            
            # Add to metrics
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                metric_type=MetricType.USER_ACTIONS,
                value=1.0,
                metadata=metadata or {},
                tags={'action': action, 'user_id': user_id}
            )
            
            with self._lock:
                self.metrics_buffer.append(metric)
                
        except Exception as e:
            print(f"Failed to record user action: {e}")

    def record_model_inference(self, model_name: str, inference_time: float,
                             input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
                             error: bool = False):
        """Record model inference metrics"""
        metadata = {
            'model_name': model_name,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'error': error
        }
        
        metric = PerformanceMetric(
            timestamp=datetime.utcnow(),
            metric_type=MetricType.MODEL_INFERENCE,
            value=inference_time,
            metadata=metadata,
            tags={
                'model': model_name,
                'status': 'error' if error else 'success'
            }
        )
        
        with self._lock:
            self.metrics_buffer.append(metric)

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        with self._lock:
            current_time = datetime.utcnow()
            last_minute = current_time - timedelta(minutes=1)
            last_hour = current_time - timedelta(hours=1)
            
            # Recent metrics from buffer
            recent_metrics = [m for m in self.metrics_buffer 
                            if m.timestamp >= last_minute]
            
            # Current system metrics
            latest_system = self.system_metrics[-1] if self.system_metrics else {}
            
            # Active requests
            active_requests = len(self.request_metrics)
            
            # Calculate rates
            requests_per_minute = len([m for m in recent_metrics 
                                     if m.metric_type == MetricType.RESPONSE_TIME])
            
            # Recent response times
            recent_response_times = [m.value for m in recent_metrics 
                                   if m.metric_type == MetricType.RESPONSE_TIME]
            
            avg_response_time = statistics.mean(recent_response_times) if recent_response_times else 0.0
            
            # Error rate
            recent_errors = len([m for m in recent_metrics 
                               if m.metadata.get('status_code', 200) >= 400])
            error_rate = (recent_errors / max(len(recent_response_times), 1)) * 100
            
            return {
                'timestamp': current_time.isoformat(),
                'active_requests': active_requests,
                'requests_per_minute': requests_per_minute,
                'avg_response_time_ms': avg_response_time * 1000,
                'error_rate_percent': error_rate,
                'system': {
                    'cpu_percent': latest_system.get('cpu_percent', 0),
                    'memory_percent': latest_system.get('memory_percent', 0),
                    'memory_used_mb': latest_system.get('memory_used_mb', 0),
                    'process_memory_mb': latest_system.get('process_memory_mb', 0)
                },
                'top_endpoints': self._get_top_endpoints(5),
                'recent_errors': self._get_recent_errors(5)
            }

    def _get_top_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top endpoints by request count"""
        endpoints = []
        
        for endpoint, stats in self.endpoint_stats.items():
            if stats['count'] > 0:
                avg_time = stats['total_time'] / stats['count']
                error_rate = (stats['errors'] / stats['count']) * 100
                
                endpoints.append({
                    'endpoint': endpoint,
                    'requests': stats['count'],
                    'avg_response_time_ms': avg_time * 1000,
                    'error_rate_percent': error_rate,
                    'total_errors': stats['errors']
                })
        
        return sorted(endpoints, key=lambda x: x['requests'], reverse=True)[:limit]

    def _get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent error information"""
        errors = []
        
        for error_type, count in self.error_stats.items():
            errors.append({
                'error_type': error_type,
                'count': count
            })
        
        return sorted(errors, key=lambda x: x['count'], reverse=True)[:limit]

    def get_aggregated_metrics(self, time_window: TimeWindow, 
                             start_time: Optional[datetime] = None, 
                             end_time: Optional[datetime] = None) -> AggregatedMetrics:
        """Get aggregated metrics for a time period"""
        if end_time is None:
            end_time = datetime.utcnow()
        
        if start_time is None:
            if time_window == TimeWindow.HOUR:
                start_time = end_time - timedelta(hours=1)
            elif time_window == TimeWindow.DAY:
                start_time = end_time - timedelta(days=1)
            elif time_window == TimeWindow.WEEK:
                start_time = end_time - timedelta(weeks=1)
            elif time_window == TimeWindow.MONTH:
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(minutes=1)
        
        # Check cache
        cache_key = f"{time_window.value}_{start_time.isoformat()}_{end_time.isoformat()}"
        if cache_key in self.aggregated_cache:
            cached = self.aggregated_cache[cache_key]
            # Return cached if not too old
            if (datetime.utcnow() - cached.end_time).total_seconds() < 300:  # 5 minutes
                return cached
        
        # Calculate aggregated metrics
        with self._lock:
            # Filter metrics by time window
            relevant_metrics = [m for m in self.metrics_buffer 
                              if start_time <= m.timestamp <= end_time 
                              and m.metric_type == MetricType.RESPONSE_TIME]
            
            if not relevant_metrics:
                aggregated = AggregatedMetrics(
                    time_window=time_window,
                    start_time=start_time,
                    end_time=end_time
                )
            else:
                response_times = [m.value for m in relevant_metrics]
                status_codes = [m.metadata.get('status_code', 200) for m in relevant_metrics]
                
                successful = len([sc for sc in status_codes if sc < 400])
                failed = len(relevant_metrics) - successful
                
                # Calculate percentiles
                sorted_times = sorted(response_times)
                p95_idx = int(0.95 * len(sorted_times))
                p99_idx = int(0.99 * len(sorted_times))
                
                aggregated = AggregatedMetrics(
                    time_window=time_window,
                    start_time=start_time,
                    end_time=end_time,
                    total_requests=len(relevant_metrics),
                    successful_requests=successful,
                    failed_requests=failed,
                    avg_response_time=statistics.mean(response_times),
                    min_response_time=min(response_times),
                    max_response_time=max(response_times),
                    p95_response_time=sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0,
                    p99_response_time=sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0,
                    error_rate=(failed / len(relevant_metrics)) * 100,
                    top_endpoints=self._get_top_endpoints(),
                    top_errors=self._get_recent_errors()
                )
            
            # Cache result
            self.aggregated_cache[cache_key] = aggregated
            
            return aggregated

    def get_user_behavior_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get user behavior analytics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Query user activities using correct field name
            activities = db.session.query(UserActivity).filter(
                UserActivity.created_at >= start_time
            ).all()
            
            # Analyze user behavior
            user_actions = defaultdict(int)
            action_trends = defaultdict(lambda: defaultdict(int))
            user_engagement: Dict[str, Any] = defaultdict(lambda: {'actions': 0, 'unique_days': set()})
            
            for activity in activities:
                user_actions[activity.activity_type] += 1
                day_key = activity.created_at.date().isoformat()
                action_trends[activity.activity_type][day_key] += 1
                user_engagement[activity.user_id]['actions'] += 1
                user_engagement[activity.user_id]['unique_days'].add(day_key)
            
            # Calculate engagement metrics
            total_users = len(user_engagement)
            active_users = len([u for u, data in user_engagement.items() 
                              if len(data['unique_days']) >= 2])
            
            avg_actions_per_user = (sum(data['actions'] for data in user_engagement.values()) 
                                  / max(total_users, 1))
            
            return {
                'period_days': days,
                'total_users': total_users,
                'active_users': active_users,
                'retention_rate': (active_users / max(total_users, 1)) * 100,
                'avg_actions_per_user': avg_actions_per_user,
                'top_actions': dict(sorted(user_actions.items(), 
                                         key=lambda x: x[1], reverse=True)[:10]),
                'action_trends': dict(action_trends)
            }
            
        except Exception as e:
            raise ApplicationError(f"Failed to get user behavior analytics: {e}", 
                                 ErrorCode.DATABASE_ERROR)

    def export_metrics(self, start_time: datetime, end_time: datetime, 
                      format: str = 'json') -> Dict[str, Any]:
        """Export metrics for external analysis"""
        try:
            with self._lock:
                # Filter metrics by time range
                relevant_metrics = [m for m in self.metrics_buffer 
                                  if start_time <= m.timestamp <= end_time]
                
                if format == 'json':
                    return {
                        'export_info': {
                            'start_time': start_time.isoformat(),
                            'end_time': end_time.isoformat(),
                            'total_metrics': len(relevant_metrics),
                            'generated_at': datetime.utcnow().isoformat()
                        },
                        'metrics': [asdict(m) for m in relevant_metrics],
                        'aggregated': asdict(self.get_aggregated_metrics(
                            TimeWindow.DAY, start_time, end_time))
                    }
                else:
                    raise ApplicationError(f"Unsupported export format: {format}", 
                                         ErrorCode.VALIDATION_ERROR)
                    
        except Exception as e:
            raise ApplicationError(f"Failed to export metrics: {e}", 
                                 ErrorCode.DATABASE_ERROR)

    def cleanup_old_metrics(self):
        """Clean up old metrics beyond retention period"""
        cutoff_time = datetime.utcnow() - timedelta(days=self.retention_days)
        
        with self._lock:
            # Clean up in-memory buffer
            self.metrics_buffer = deque(
                [m for m in self.metrics_buffer if m.timestamp >= cutoff_time],
                maxlen=self.metrics_buffer.maxlen
            )
            
            # Clean up cache
            old_cache_keys = [k for k, v in self.aggregated_cache.items() 
                            if v.end_time < cutoff_time]
            for key in old_cache_keys:
                del self.aggregated_cache[key]


# Global analytics instance
analytics = None


def init_analytics(retention_days: int = 30) -> PerformanceAnalytics:
    """Initialize the global analytics instance"""
    global analytics
    analytics = PerformanceAnalytics(retention_days)
    return analytics


def get_analytics() -> PerformanceAnalytics:
    """Get the global analytics instance"""
    if analytics is None:
        raise ApplicationError("Analytics not initialized", ErrorCode.CONFIG_ERROR)
    return analytics
