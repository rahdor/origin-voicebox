"""
Platform detection for backend selection.
"""

import os
import platform
from typing import Literal


def is_apple_silicon() -> bool:
    """
    Check if running on Apple Silicon (arm64 macOS).

    Returns:
        True if on Apple Silicon, False otherwise
    """
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def get_backend_type() -> Literal["mlx", "pytorch", "replicate"]:
    """
    Detect the best backend for the current platform.

    Priority:
    1. TTS_BACKEND env var if set
    2. REPLICATE_API_TOKEN/KEY present → use Replicate
    3. Apple Silicon with MLX → use MLX
    4. Otherwise → PyTorch

    Returns:
        Backend type string
    """
    # Explicit override
    backend_env = os.environ.get("TTS_BACKEND", "").lower()
    if backend_env in ("mlx", "pytorch", "replicate"):
        return backend_env

    # Auto-detect Replicate (cloud deployment)
    if os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY"):
        return "replicate"

    # Local backends
    if is_apple_silicon():
        try:
            import mlx
            return "mlx"
        except ImportError:
            return "pytorch"
    return "pytorch"
