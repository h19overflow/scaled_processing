# models.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class EmailNotification(BaseModel):
    history_id: str
    email_address: str
    timestamp: datetime = datetime.now()

class AttachmentInfo(BaseModel):
    filename: str
    size: int
    mime_type: str
    file_path: Optional[str] = None

class ProcessingResult(BaseModel):
    processed_at: datetime
    attachment_count: int
    success: bool
    error_message: Optional[str] = None

class EmailProcessingStatus(BaseModel):
    message_id: str
    subject: str
    sender: str
    processed: bool
    attachments: List[AttachmentInfo]
    processing_result: Optional[ProcessingResult] = None
