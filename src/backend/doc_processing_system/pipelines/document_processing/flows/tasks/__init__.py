"""
Task modules for document processing flow.
"""

from .duplicate_detection_task import duplicate_detection_task
from .docling_processing_task import docling_processing_task
from .vision_enriching_task import chunking_task
from .document_saving_task import document_saving_task
from .kafka_message_preparation_task import kafka_message_preparation_task

__all__ = [
    "duplicate_detection_task",
    "docling_processing_task",
    "vision_enriching_task.py",
    "document_saving_task",
    "kafka_message_preparation_task"
]