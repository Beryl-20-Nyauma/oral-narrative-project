"""GPU utility service for ML acceleration."""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_gpu_available = None
_device = None


def is_gpu_available() -> bool:
    """
    Check if GPU is available.
    
    Returns:
        True if CUDA GPU is available
    """
    global _gpu_available
    
    if _gpu_available is not None:
        return _gpu_available
    
    try:
        import torch
        _gpu_available = torch.cuda.is_available()
        
        if _gpu_available:
            logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("No GPU available, using CPU")
        
        return _gpu_available
        
    except ImportError:
        logger.warning("PyTorch not installed, GPU check failed")
        _gpu_available = False
        return False


def get_device() -> str:
    """
    Get the best available device.
    
    Returns:
        "cuda" if GPU available, otherwise "cpu"
    """
    global _device
    
    if _device is not None:
        return _device
    
    if is_gpu_available():
        _device = "cuda"
    else:
        _device = "cpu"
    
    return _device


def get_device_info() -> Dict[str, Any]:
    """
    Get detailed device information.
    
    Returns:
        Dict with device details
    """
    info = {
        "device": get_device(),
        "gpu_available": is_gpu_available(),
        "cuda_version": None,
        "gpu_name": None,
        "gpu_memory_total_gb": None,
        "gpu_memory_free_gb": None
    }
    
    if is_gpu_available():
        try:
            import torch
            
            info["cuda_version"] = torch.version.cuda
            info["gpu_name"] = torch.cuda.get_device_name(0)
            
            props = torch.cuda.get_device_properties(0)
            info["gpu_memory_total_gb"] = round(props.total_memory / (1024**3), 2)
            
            free_memory = torch.cuda.memory_reserved(0) - torch.cuda.memory_allocated(0)
            info["gpu_memory_free_gb"] = round(free_memory / (1024**3), 2)
            
        except Exception as e:
            info["error"] = str(e)
    
    return info


def clear_gpu_cache():
    """Clear GPU cache to free memory."""
    if is_gpu_available():
        try:
            import torch
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear GPU cache: {e}")


def get_torch_device():
    """
    Get PyTorch device object.
    
    Returns:
        torch.device object
    """
    import torch
    return torch.device(get_device())


def optimize_for_gpu():
    """
    Apply GPU optimizations.
    """
    if not is_gpu_available():
        return
    
    try:
        import torch
        
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        
        logger.info("GPU optimizations applied")
        
    except Exception as e:
        logger.warning(f"Failed to apply GPU optimizations: {e}")


def to_device(tensor_or_model):
    """
    Move tensor or model to the appropriate device.
    
    Args:
        tensor_or_model: PyTorch tensor or model
    
    Returns:
        Tensor or model on the correct device
    """
    device = get_device()
    
    if hasattr(tensor_or_model, 'to'):
        return tensor_or_model.to(device)
    
    return tensor_or_model
