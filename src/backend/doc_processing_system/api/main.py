# main.py
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import base64
import json
import logging
from typing import Optional
import asyncio
from datetime import datetime, timedelta

from src.backend.doc_processing_system.services.gmail_email_listener.gmail_service import GmailService
from src.backend.doc_processing_system.services.gmail_email_listener.gmail_auth_manager import GmailAuthManager
from src.backend.doc_processing_system.services.gmail_email_listener.models import ProcessingResult,EmailNotification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gmail Event Monitor", version="1.0.0")
security = HTTPBearer()

# Global services
gmail_service = None
auth_manager = GmailAuthManager("client_secrets.json")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global gmail_service
    try:
        gmail_service = GmailService(auth_manager)
        # Setup Gmail watch on startup
        await setup_gmail_watch()
        logger.info("Gmail monitoring started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {e}")


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
