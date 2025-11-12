"""Dependency management utilities."""

import importlib
from typing import Optional, Any
from functools import wraps

class OptionalDependency:
    """Context manager for optional dependencies."""
    
    def __init__(self, module_name: str, fallback_msg: str = None):
        self.module_name = module_name
        self.fallback_msg = fallback_msg or f"{module_name} not available"
        self.module = None
        
    def __enter__(self):
        try:
            self.module = importlib.import_module(self.module_name)
            return self.module
        except ImportError:
            return None
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def require_dependency(module_name: str, error_msg: str = None):
    """Decorator to require a dependency for a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                importlib.import_module(module_name)
                return func(*args, **kwargs)
            except ImportError:
                msg = error_msg or f"{module_name} required for {func.__name__}"
                raise ImportError(msg)
        return wrapper
    return decorator

def safe_import(module_name: str, fallback: Any = None) -> Any:
    """Safely import a module with fallback."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return fallback