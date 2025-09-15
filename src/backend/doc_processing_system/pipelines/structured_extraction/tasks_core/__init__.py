"""
Nodes package for structured extraction demo.
Contains LangGraph node functions.
"""

from .chunking import chunk_document
# from .classification import classify_document
from .config_gen import generate_config

__all__ = [
    "chunk_document",
    # "classify_document",
    "generate_config"
]
