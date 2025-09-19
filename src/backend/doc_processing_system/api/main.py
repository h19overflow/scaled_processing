# main.py
from fastapi import FastAPI
from fastapi.security import HTTPBearer
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()
from src.backend.doc_processing_system.services.gmail_email_listener.gmail_service import GmailService
from src.backend.doc_processing_system.services.gmail_email_listener.gmail_auth_manager import GmailAuthManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
gmail_service = None
auth_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global gmail_service, auth_manager
    try:
        # Get paths from environment variables
        client_secrets_path = os.getenv("GMAIL_CLIENT_SECRETS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")

        if not client_secrets_path or not token_path:
            raise ValueError("GMAIL_CLIENT_SECRETS_PATH and GMAIL_TOKEN_PATH environment variables must be set")

        auth_manager = GmailAuthManager(client_secrets_path, token_path)
        gmail_service = GmailService(auth_manager)

        # Setup Gmail watch on startup
        await setup_gmail_watch()
        logger.info("Gmail monitoring started successfully")

        yield  # Application runs here

    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {e}")
        yield  # Still yield even on error to let app start


app = FastAPI(title="Gmail Event Monitor", version="1.0.0", lifespan=lifespan)
security = HTTPBearer()


async def setup_gmail_watch():
    """Setup Gmail watch for push notifications"""
    try:
        watch_request = {
            'labelIds': ['INBOX'],
            'topicName': 'projects/gmail-monitor-project/topics/gmail-notifications',
            'labelFilterBehavior': 'INCLUDE'
        }

        result = gmail_service.setup_watch(watch_request)
        logger.info(f"Gmail watch setup successful. Expires: {result.get('expiration')}")

        # Schedule watch renewal (every 6 days to be safe)
        asyncio.create_task(schedule_watch_renewal())

    except Exception as e:
        logger.error(f"Failed to setup Gmail watch: {e}")
        raise


async def schedule_watch_renewal():
    """Schedule automatic renewal of Gmail watch every 6 days"""
    while True:
        await asyncio.sleep(6 * 24 * 3600)  # 6 days
        try:
            await setup_gmail_watch()
            logger.info("Gmail watch renewed successfully")
        except Exception as e:
            logger.error(f"Failed to renew Gmail watch: {e}")
