from doc_processing_system.messaging.producer import ProducerHandler
from fastapi import Request
from pathlib import Path
from src.backend.doc_processing_system.core_deps.database.connection_manager import (
    ConnectionManager,
)
import logging


MAX_FILE_SIZE_MB = 50
PROCESSING_TIMEOUT_SECONDS = 120
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("./data/temp/uploads")


def get_kafka_producer(request: Request) -> ProducerHandler:
    """Dependency to get Kafka producer from app state."""
    return request.app.state.kafka_producer


def get_db_manager(request: Request) -> ConnectionManager:
    """Dependency to get database manager from app state."""
    return request.app.state.db_manager
