"""
Extraction pipeline messaging components.
Handles field discovery, agent scaling, and extraction events.
"""

from .extraction_producer import ExtractionProducer

__all__ = [
    "ExtractionProducer"
]