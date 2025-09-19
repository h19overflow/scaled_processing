# main.py
from fastapi import FastAPI
from fastapi.security import HTTPBearer
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()
from src.backend.doc_processing_system.services.gmail_email_listener.cloud.gmail_service import GmailService
from src.backend.doc_processing_system.services.gmail_email_listener.cloud.gmail_auth_manager import GmailAuthManager

# Import routers
from src.backend.api.endpoints.gmail_endpoints.gmail_auth import router as gmail_auth_router
from src.backend.api.endpoints.gmail_endpoints.gmail_service import router as gmail_service_router
from src.backend.api.endpoints.health import router as health_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App state will be stored in app.state instead of globals


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    try:
        # Initialize app state
        app.state.gmail_service = None
        app.state.auth_manager = None
        app.state.startup_time = asyncio.get_event_loop().time()
        app.state.request_count = 0

        # Get paths from environment variables
        client_secrets_path = os.getenv("GMAIL_CLIENT_SECRETS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")
        auto_setup_watch = os.getenv("AUTO_SETUP_GMAIL_WATCH", "false").lower() == "true"

        if not client_secrets_path or not token_path:
            raise ValueError("GMAIL_CLIENT_SECRETS_PATH and GMAIL_TOKEN_PATH environment variables must be set")

        app.state.auth_manager = GmailAuthManager(client_secrets_path, token_path)

        # Only create gmail_service and setup watch if tokens exist
        if os.path.exists(token_path) and auto_setup_watch:
            app.state.gmail_service = GmailService(app.state.auth_manager)
            await setup_gmail_watch(app)
            logger.info("Gmail monitoring started successfully")
        else:
            logger.info("Gmail tokens not found. Use /auth/login to authenticate first.")

        yield  # Application runs here

    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {e}")
        yield  # Still yield even on error to let app start


app = FastAPI(title="Gmail Event Monitor", version="1.0.0", lifespan=lifespan)
security = HTTPBearer()

# Include routers
app.include_router(gmail_auth_router)
app.include_router(gmail_service_router)
app.include_router(health_router)


# HELPER FUNCTIONS

async def setup_gmail_watch(app: FastAPI):
    """Setup Gmail watch for push notifications"""
    try:
        if not app.state.gmail_service:
            raise Exception("Gmail service not initialized")

        watch_request = {
            'labelIds': ['INBOX'],
            'topicName': 'projects/gmail-monitor-project-472511/topics/gmail-notifications',
            'labelFilterBehavior': 'INCLUDE'
        }

        # Run synchronous call in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, app.state.gmail_service.setup_watch, watch_request)
        logger.info(f"Gmail watch setup successful. Expires: {result.get('expiration')}")

        # Schedule watch renewal (every 6 days to be safe)
        asyncio.create_task(schedule_watch_renewal(app))

    except Exception as e:
        logger.error(f"Failed to setup Gmail watch: {e}")
        raise


async def schedule_watch_renewal(app: FastAPI):
    """Schedule automatic renewal of Gmail watch every 6 days"""
    while True:
        await asyncio.sleep(6 * 24 * 3600)  # 6 days
        try:
            await setup_gmail_watch(app)
            logger.info("Gmail watch renewed successfully")
        except Exception as e:
            logger.error(f"Failed to renew Gmail watch: {e}")
