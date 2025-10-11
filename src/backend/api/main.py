# main.py
from fastapi import FastAPI
from fastapi.security import HTTPBearer
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# python -m uvicorn src.backend.api.main:app --reload --host 0.0.0.0 --port 8000

load_dotenv()

# Import routers
from src.backend.api.endpoints.health import router as health_router
from src.backend.api.endpoints.document_processing import router as document_processing_router
from src.backend.api.endpoints.document_health import router as document_health_router

# Import document processing services
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
from src.backend.doc_processing_system.config.settings import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App state will be stored in app.state instead of globals


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    try:
        # Initialize app state
        app.state.startup_time = asyncio.get_event_loop().time()
        app.state.request_count = 0

        # Initialize document processing services
        logger.info("Initializing document processing services...")

        # Job tracker
        app.state.job_tracker = JobTracker()
        logger.info("Job tracker initialized")

        # Kafka producer
        settings = get_settings()
        kafka_broker = settings.KAFKA_BOOTSTRAP_SERVERS[0] if settings.KAFKA_BOOTSTRAP_SERVERS else "localhost:9092"
        app.state.kafka_producer = ProducerHandler(broker=kafka_broker)
        logger.info(f"Kafka producer initialized: {kafka_broker}")

        # Database manager
        app.state.db_manager = ConnectionManager()
        logger.info("Database manager initialized")


        yield  # Application runs here

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        yield  # Still yield even on error to let app start
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down services...")
        if hasattr(app.state, 'kafka_producer'):
            app.state.kafka_producer.close()
        if hasattr(app.state, 'db_manager'):
            app.state.db_manager.close_connections()


app = FastAPI(
    title="Document Processing Microservice",
    description="Malaysian utility bill processing API with Kafka integration",
    version="1.0.0",
    lifespan=lifespan
)
security = HTTPBearer()

# Include routers
app.include_router(document_processing_router)
app.include_router(document_health_router)
app.include_router(health_router)

