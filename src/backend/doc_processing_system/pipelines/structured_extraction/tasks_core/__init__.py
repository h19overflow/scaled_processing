"""
Nodes package for structured extraction demo.
Contains LangGraph node functions.
"""

from .config_gen import generate_config
from .read_markdown import read_markdown

__all__ = [
    "generate_config",
    "read_markdown",
]
