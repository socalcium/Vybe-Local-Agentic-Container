"""
Advanced Model Management System
Comprehensive model lifecycle management with versioning, optimization, and monitoring.
"""
import os
import json
import hashlib
import threading
import time
import psutil
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from flask import current_app
from sqlalchemy import and_, func

from ..models import db
from ..utils.error_handling import ApplicationError, ErrorCode
from ..utils.input_validation import AdvancedInputValidator

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model status enumeration"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    OPTIMIZING = "optimizing"
    READY = "ready"
    ERROR = "error"
    DEPRECATED = "deprecated"


class ModelPriority(Enum):
    """Model priority levels for resource management"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ModelMetadata:
    """Model metadata structure"""
    name: str
    version: str
    file_path: str
    file_size: bytes
    file_hash: str
    model_type: str
    parameters: int
    architecture: str
    quantization: Optional[str]
    context_length: int
    created_at: datetime
    last_used: Optional[datetime]
    use_count: int
    memory_usage: Optional[int]
    load_time: Optional[float]
    avg_inference_time: Optional[float]
    priority: ModelPriority
    status: ModelStatus
    tags: List[str]
    config: Dict[str, Any]


@dataclass
class ModelPerformanceMetrics:
    """Model performance tracking"""
    model_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    memory_peak: int
    memory_avg: int
    cpu_usage_avg: float
    last_updated: datetime


class ModelOptimizer:
    """Model optimization utilities"""
    
    @staticmethod
    def detect_optimal_settings(model_path: str) -> Dict[str, Any]:
        """Detect optimal settings for model based on hardware"""
        try:
            # Get system specs
            cpu_count = psutil.cpu_count() or 4  # Default to 4 if None
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Basic optimization settings
            settings = {
                'n_threads': min(cpu_count - 1, 8),  # Leave one CPU core free
                'n_ctx': 2048,  # Default context length
                'n_batch': 512,  # Batch size
                'n_gpu_layers': 0,  # CPU-only for now
                'use_mmap': True,
                'use_mlock': memory_gb > 16,  # Only if enough RAM
                'rope_freq_base': 10000.0,
                'rope_freq_scale': 1.0
            }
            
            # Adjust based on available memory
            if memory_gb < 8:
                settings.update({
                    'n_ctx': 1024,
                    'n_batch': 256,
                    'use_mlock': False
                })
            elif memory_gb > 32:
                settings.update({
                    'n_ctx': 4096,
                    'n_batch': 1024
                })
            
            return settings
            
        except Exception as e:
            logger.error(f"Failed to detect optimal settings: {e}")
            return {
                'n_threads': 4,
                'n_ctx': 2048,
                'n_batch': 512,
                'n_gpu_layers': 0,
                'use_mmap': True,
                'use_mlock': False
            }


class ModelManager:
    """Advanced model management with lifecycle control"""
    
    def __init__(self, models_directory: str = "models"):
        self.models_directory = Path(models_directory)
        self.models_directory.mkdir(exist_ok=True)
        
        self.loaded_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, ModelMetadata] = {}
        self.performance_metrics: Dict[str, ModelPerformanceMetrics] = {}
        self.model_locks: Dict[str, threading.Lock] = {}
        
        self.validator = AdvancedInputValidator()
        self.optimizer = ModelOptimizer()
        
        # Configuration
        self.max_loaded_models = 3
        self.memory_threshold = 0.85  # 85% memory usage threshold
        self.cleanup_interval = 300  # 5 minutes
        self.metrics_retention_days = 30
        
        # Start background tasks
        self._start_background_tasks()
        
        # Load existing models metadata
        self._load_models_metadata()
    
    def scan_models_directory(self) -> List[Dict[str, Any]]:
        """Scan models directory and update metadata"""
        discovered_models = []
        
        try:
            for model_file in self.models_directory.glob("*.gguf"):
                if model_file.is_file():
                    model_info = self._analyze_model_file(model_file)
                    if model_info:
                        discovered_models.append(model_info)
                        
                        # Update or create metadata
                        if model_info['name'] not in self.model_metadata:
                            self._create_model_metadata(model_info)
            
            logger.info(f"Discovered {len(discovered_models)} models")
            return discovered_models
            
        except Exception as e:
            logger.error(f"Failed to scan models directory: {e}")
            return []
    
    def load_model(self, model_name: str, priority: ModelPriority = ModelPriority.NORMAL, 
                   force_reload: bool = False) -> Dict[str, Any]:
        """Load a model with resource management"""
        try:
            # Check if model exists
            if model_name not in self.model_metadata:
                raise ApplicationError(
                    f"Model '{model_name}' not found",
                    ErrorCode.DATA_NOT_FOUND
                )
            
            metadata = self.model_metadata[model_name]
            
            # Check if already loaded
            if model_name in self.loaded_models and not force_reload:
                self._update_model_usage(model_name)
                return {
                    'name': model_name,
                    'status': 'already_loaded',
                    'memory_usage': metadata.memory_usage
                }
            
            # Get or create lock for this model
            if model_name not in self.model_locks:
                self.model_locks[model_name] = threading.Lock()
            
            with self.model_locks[model_name]:
                # Check memory and unload if necessary
                self._manage_memory_for_loading(model_name, priority)
                
                # Update status
                metadata.status = ModelStatus.LOADING
                
                start_time = time.time()
                
                # Load the model (placeholder for actual loading logic)
                model_instance = self._load_model_instance(metadata)
                
                load_time = time.time() - start_time
                
                # Update metadata
                metadata.load_time = load_time
                metadata.last_used = datetime.utcnow()
                metadata.use_count += 1
                metadata.status = ModelStatus.READY
                metadata.memory_usage = self._estimate_memory_usage(model_instance)
                
                # Store loaded model
                self.loaded_models[model_name] = {
                    'instance': model_instance,
                    'metadata': metadata,
                    'loaded_at': datetime.utcnow(),
                    'priority': priority
                }
                
                logger.info(f"Model '{model_name}' loaded successfully in {load_time:.2f}s")
                
                return {
                    'name': model_name,
                    'status': 'loaded',
                    'load_time': load_time,
                    'memory_usage': metadata.memory_usage
                }
                
        except Exception as e:
            if model_name in self.model_metadata:
                self.model_metadata[model_name].status = ModelStatus.ERROR
            
            logger.error(f"Failed to load model '{model_name}': {e}")
            raise ApplicationError(
                f"Failed to load model: {e}",
                ErrorCode.MODEL_ERROR
            )
    
    def unload_model(self, model_name: str, force: bool = False) -> Dict[str, Any]:
        """Unload a model and free resources"""
        try:
            if model_name not in self.loaded_models:
                return {'name': model_name, 'status': 'not_loaded'}
            
            model_info = self.loaded_models[model_name]
            
            # Check if model can be unloaded (priority check)
            if not force and model_info['priority'] == ModelPriority.CRITICAL:
                raise ApplicationError(
                    f"Cannot unload critical model '{model_name}' without force flag",
                    ErrorCode.AUTHORIZATION_FAILED
                )
            
            with self.model_locks.get(model_name, threading.Lock()):
                # Clean up model instance
                if 'instance' in model_info:
                    del model_info['instance']
                
                # Remove from loaded models
                del self.loaded_models[model_name]
                
                # Update metadata
                if model_name in self.model_metadata:
                    self.model_metadata[model_name].status = ModelStatus.UNLOADED
                    self.model_metadata[model_name].memory_usage = None
                
                # Force garbage collection
                gc.collect()
                
                logger.info(f"Model '{model_name}' unloaded successfully")
                
                return {
                    'name': model_name,
                    'status': 'unloaded',
                    'freed_memory': model_info['metadata'].memory_usage or 0
                }
                
        except Exception as e:
            logger.error(f"Failed to unload model '{model_name}': {e}")
            raise ApplicationError(
                f"Failed to unload model: {e}",
                ErrorCode.MODEL_ERROR
            )
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get comprehensive model information"""
        if model_name not in self.model_metadata:
            raise ApplicationError(
                f"Model '{model_name}' not found",
                ErrorCode.DATA_NOT_FOUND
            )
        
        metadata = self.model_metadata[model_name]
        is_loaded = model_name in self.loaded_models
        
        info = asdict(metadata)
        info.update({
            'is_loaded': is_loaded,
            'performance_metrics': self.performance_metrics.get(model_name)
        })
        
        if is_loaded:
            loaded_info = self.loaded_models[model_name]
            info.update({
                'loaded_at': loaded_info['loaded_at'].isoformat(),
                'priority': loaded_info['priority'].name
            })
        
        return info
    
    def list_models(self, status_filter: Optional[ModelStatus] = None) -> List[Dict[str, Any]]:
        """List all models with optional status filtering"""
        models = []
        
        for model_name, metadata in self.model_metadata.items():
            if status_filter is None or metadata.status == status_filter:
                models.append(self.get_model_info(model_name))
        
        # Sort by priority and last used
        models.sort(key=lambda x: (
            -x['priority'].value if isinstance(x['priority'], ModelPriority) else -1,
            x['last_used'] or datetime.min
        ), reverse=True)
        
        return models
    
    def optimize_model_settings(self, model_name: str) -> Dict[str, Any]:
        """Optimize model settings for current hardware"""
        if model_name not in self.model_metadata:
            raise ApplicationError(
                f"Model '{model_name}' not found",
                ErrorCode.DATA_NOT_FOUND
            )
        
        metadata = self.model_metadata[model_name]
        
        # Get optimal settings
        optimal_settings = self.optimizer.detect_optimal_settings(metadata.file_path)
        
        # Update model config
        metadata.config.update(optimal_settings)
        
        # If model is loaded, apply settings
        if model_name in self.loaded_models:
            # Reload with new settings
            self.unload_model(model_name, force=True)
            self.load_model(model_name)
        
        logger.info(f"Optimized settings for model '{model_name}'")
        
        return {
            'model': model_name,
            'status': 'optimized',
            'settings': optimal_settings
        }
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'disk': {
                    'free': psutil.disk_usage('/').free,
                    'total': psutil.disk_usage('/').total
                },
                'loaded_models': len(self.loaded_models),
                'max_models': self.max_loaded_models
            }
            
        except Exception as e:
            logger.error(f"Failed to get system resources: {e}")
            return {}
    
    def _analyze_model_file(self, model_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze model file and extract metadata"""
        try:
            stat = model_path.stat()
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(model_path)
            
            # Extract model info from filename (basic parsing)
            name = model_path.stem
            
            return {
                'name': name,
                'file_path': str(model_path),
                'file_size': stat.st_size,
                'file_hash': file_hash,
                'modified_at': datetime.fromtimestamp(stat.st_mtime)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze model file {model_path}: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def _create_model_metadata(self, model_info: Dict[str, Any]) -> ModelMetadata:
        """Create metadata object for discovered model"""
        metadata = ModelMetadata(
            name=model_info['name'],
            version="1.0",  # Default version
            file_path=model_info['file_path'],
            file_size=model_info['file_size'],
            file_hash=model_info['file_hash'],
            model_type="llama",  # Default type
            parameters=7000000000,  # Default parameter count
            architecture="llama2",  # Default architecture
            quantization="Q4_K_M",  # Default quantization
            context_length=2048,  # Default context length
            created_at=model_info.get('modified_at', datetime.utcnow()),
            last_used=None,
            use_count=0,
            memory_usage=None,
            load_time=None,
            avg_inference_time=None,
            priority=ModelPriority.NORMAL,
            status=ModelStatus.UNLOADED,
            tags=[],
            config=self.optimizer.detect_optimal_settings(model_info['file_path'])
        )
        
        self.model_metadata[model_info['name']] = metadata
        return metadata
    
    def _load_model_instance(self, metadata: ModelMetadata) -> Any:
        """Load actual model instance (placeholder)"""
        # This would integrate with actual model loading library
        # For now, return a mock object
        return {
            'name': metadata.name,
            'path': metadata.file_path,
            'config': metadata.config,
            'loaded_at': datetime.utcnow()
        }
    
    def _estimate_memory_usage(self, model_instance: Any) -> int:
        """Estimate memory usage of loaded model"""
        # This would calculate actual memory usage
        # For now, return estimated usage based on file size
        return int(1.5 * 1024 * 1024 * 1024)  # 1.5GB estimate
    
    def _update_model_usage(self, model_name: str):
        """Update model usage statistics"""
        if model_name in self.model_metadata:
            metadata = self.model_metadata[model_name]
            metadata.last_used = datetime.utcnow()
            metadata.use_count += 1
    
    def _manage_memory_for_loading(self, model_name: str, priority: ModelPriority):
        """Manage memory by unloading models if necessary"""
        memory = psutil.virtual_memory()
        
        # If memory usage is high, unload lower priority models
        if memory.percent > self.memory_threshold * 100:
            self._unload_low_priority_models(priority)
        
        # If we have too many loaded models, unload least recently used
        if len(self.loaded_models) >= self.max_loaded_models:
            self._unload_lru_model(priority)
    
    def _unload_low_priority_models(self, required_priority: ModelPriority):
        """Unload models with lower priority"""
        to_unload = []
        
        for name, model_info in self.loaded_models.items():
            if model_info['priority'].value < required_priority.value:
                to_unload.append(name)
        
        for model_name in to_unload:
            try:
                self.unload_model(model_name, force=True)
                logger.info(f"Unloaded lower priority model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to unload model {model_name}: {e}")
    
    def _unload_lru_model(self, required_priority: ModelPriority):
        """Unload least recently used model"""
        if not self.loaded_models:
            return
        
        # Find LRU model that can be unloaded
        lru_model = None
        lru_time = datetime.utcnow()
        
        for name, model_info in self.loaded_models.items():
            if (model_info['priority'].value < required_priority.value and
                model_info['metadata'].last_used and
                model_info['metadata'].last_used < lru_time):
                lru_model = name
                lru_time = model_info['metadata'].last_used
        
        if lru_model:
            try:
                self.unload_model(lru_model, force=True)
                logger.info(f"Unloaded LRU model: {lru_model}")
            except Exception as e:
                logger.error(f"Failed to unload LRU model {lru_model}: {e}")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        def cleanup_task():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self._cleanup_unused_models()
                    self._update_performance_metrics()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_unused_models(self):
        """Clean up unused models and old metrics"""
        now = datetime.utcnow()
        cleanup_threshold = now - timedelta(hours=2)  # Unload after 2 hours of inactivity
        
        to_unload = []
        for name, model_info in self.loaded_models.items():
            if (model_info['priority'] != ModelPriority.CRITICAL and
                model_info['metadata'].last_used and
                model_info['metadata'].last_used < cleanup_threshold):
                to_unload.append(name)
        
        for model_name in to_unload:
            try:
                self.unload_model(model_name, force=True)
                logger.info(f"Auto-unloaded inactive model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to auto-unload model {model_name}: {e}")
    
    def _update_performance_metrics(self):
        """Update performance metrics for loaded models"""
        for model_name in self.loaded_models:
            if model_name not in self.performance_metrics:
                self.performance_metrics[model_name] = ModelPerformanceMetrics(
                    model_name=model_name,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    avg_response_time=0.0,
                    min_response_time=float('inf'),
                    max_response_time=0.0,
                    memory_peak=0,
                    memory_avg=0,
                    cpu_usage_avg=0.0,
                    last_updated=datetime.utcnow()
                )
    
    def _load_models_metadata(self):
        """Load existing models metadata from storage"""
        # This would load from database or file
        # For now, scan directory on startup
        self.scan_models_directory()


# Global model manager instance
model_manager = None


def init_model_manager(models_directory: str = "models") -> ModelManager:
    """Initialize the global model manager"""
    global model_manager
    model_manager = ModelManager(models_directory)
    logger.info("Model manager initialized successfully")
    return model_manager


def get_model_manager() -> ModelManager:
    """Get the global model manager instance"""
    if model_manager is None:
        raise ApplicationError(
            "Model manager not initialized",
            ErrorCode.CONFIG_ERROR
        )
    return model_manager
