"""Core package for meshtastic_c2."""

# Expose top-level modules for easier imports in tests and runtime
from .config import load_config, Config
from .utils import setup_logging, get_short_name

__all__ = ["load_config", "Config", "setup_logging", "get_short_name"]
