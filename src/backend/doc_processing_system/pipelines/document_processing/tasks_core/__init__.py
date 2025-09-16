"""
Task modules for document processing flow.
"""

from .duplicate_detection_task import duplicate_detection_task
from .docling_processing_task import docling_processing_task
from .document_saving_task import document_saving_task

__all__ = [
    "duplicate_detection_task",
    "docling_processing_task",
    "document_saving_task",
]