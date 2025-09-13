"""
Stub/Mock implementations for packages that don't support Python 3.13
This allows the app to start and function without these optional dependencies
"""
import warnings

class CoquiTTSStub:
    """Stub implementation for coqui-tts"""
    
    def __init__(self, *args, **kwargs):
        warnings.warn("Coqui-TTS not available - using stub implementation")
    
    def tts(self, text, *args, **kwargs):
        warnings.warn("TTS functionality disabled - Coqui-TTS not available")
        return None
    
    def synthesize(self, text, *args, **kwargs):
        warnings.warn("TTS functionality disabled - Coqui-TTS not available") 
        return None

class TransformersStub:
    """Stub implementation for transformers if it fails"""
    
    class AutoTokenizer:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            warnings.warn("Transformers not available - using stub")
            return TransformersStub.TokenizerStub()
    
    class AutoModel:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            warnings.warn("Transformers not available - using stub")
            return TransformersStub.ModelStub()
    
    class TokenizerStub:
        def encode(self, text, *args, **kwargs):
            return [1, 2, 3]  # Dummy tokens
        
        def decode(self, tokens, *args, **kwargs):
            return "dummy text"
    
    class ModelStub:
        def __call__(self, *args, **kwargs):
            return {"logits": [[0.5, 0.3, 0.2]]}

class TorchStub:
    """Stub implementation for torch if it fails"""
    
    def __init__(self):
        self._is_stub = True
        self.__version__ = "stub-0.0.0"
        self.cuda = self.CudaStub()
        self.version = self.VersionStub()
    
    class CudaStub:
        def is_available(self):
            return False
        
        def device_count(self):
            return 0
    
    class VersionStub:
        def __init__(self):
            self.cuda = None
    
    @staticmethod
    def tensor(data):
        warnings.warn("PyTorch not available - using stub")
        return data
    
    @staticmethod
    def load(*args, **kwargs):
        warnings.warn("PyTorch not available - using stub")
        return {}
    
    class nn:
        class Module:
            def __init__(self):
                pass
            
            def forward(self, x):
                return x

def get_safe_import(module_name, stub_class=None):
    """
    Safely import a module, returning a stub if import fails
    """
    try:
        import importlib
        module = importlib.import_module(module_name)
        
        # Additional validation for critical modules
        if module_name == 'torch' and hasattr(module, 'cuda'):
            # Test if CUDA is actually working
            try:
                if module.cuda.is_available():
                    module.cuda.device_count()  # Test CUDA functionality
            except Exception:
                warnings.warn(f"PyTorch CUDA functionality not available - using CPU-only mode")
        
        return module
    except ImportError as e:
        warnings.warn(f"Failed to import {module_name}: {e}")
        if stub_class:
            return stub_class()
        return None
    except Exception as e:
        warnings.warn(f"Unexpected error importing {module_name}: {e}")
        if stub_class:
            return stub_class()
        return None

# Convenience functions
def get_coqui_tts():
    """Get coqui-tts or stub implementation"""
    return get_safe_import('coqui_tts', CoquiTTSStub)

def get_transformers():
    """Get transformers or stub implementation"""  
    return get_safe_import('transformers', TransformersStub)

def get_torch():
    """Get torch or stub implementation"""
    return get_safe_import('torch', TorchStub)

def get_dependency_status():
    """Get status of all critical dependencies"""
    status = {
        'coqui_tts': {
            'available': False,
            'version': None,
            'message': 'Not available - TTS features will be limited'
        },
        'transformers': {
            'available': False,
            'version': None,
            'message': 'Not available - Some AI features may be limited'
        },
        'torch': {
            'available': False,
            'version': None,
            'cuda_available': False,
            'message': 'Not available - GPU acceleration disabled'
        }
    }
    
    # Check each dependency
    coqui_tts = get_coqui_tts()
    if coqui_tts and not hasattr(coqui_tts, '_is_stub'):
        status['coqui_tts']['available'] = True
        status['coqui_tts']['version'] = getattr(coqui_tts, '__version__', 'unknown')
        status['coqui_tts']['message'] = 'Available'
    
    transformers = get_transformers()
    if transformers and not hasattr(transformers, '_is_stub'):
        status['transformers']['available'] = True
        status['transformers']['version'] = getattr(transformers, '__version__', 'unknown')
        status['transformers']['message'] = 'Available'
    
    torch = get_torch()
    if torch and not hasattr(torch, '_is_stub'):
        status['torch']['available'] = True
        status['torch']['version'] = getattr(torch, '__version__', 'unknown')
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            status['torch']['cuda_available'] = True
            status['torch']['message'] = 'Available with CUDA support'
        else:
            status['torch']['message'] = 'Available (CPU only)'
    
    return status
