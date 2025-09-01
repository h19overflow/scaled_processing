# """
# Document ingestion endpoints for file upload and processing.
# Integrates with Kafka event bus for asynchronous document processing.
# """

# import logging
# import uuid
# from datetime import datetime
# from typing import Dict, Any

# from fastapi import APIRouter, UploadFile, File, HTTPException, status
# from fastapi.responses import JSONResponse

# from ...data_models.document import (
#     ParsedDocument, 
#     DocumentMetadata, 
#     FileType, 
#     ProcessingStatus
# )
# from ...messaging.producers_n_consumers.event_bus import EventBus, EventType

# # Setup logging
# logger = logging.getLogger(__name__)
# if not logger.handlers:
#     handler = logging.StreamHandler()
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     logger.setLevel(logging.INFO)

# router = APIRouter()

# # Create event bus instance (cached for performance)
# _cached_event_bus = None

# def get_event_bus() -> EventBus:
#     """Get cached event bus instance."""
#     global _cached_event_bus
#     if _cached_event_bus is None:
#         _cached_event_bus = EventBus()
#         logger.info("Event bus initialized for ingestion endpoint")
#     return _cached_event_bus


# @router.post("/upload", response_model=Dict[str, Any])
# async def upload_document(
#     file: UploadFile = File(...),
#     user_id: str = "default_user"
# ) -> Dict[str, Any]:
#     """
#     Upload document and trigger processing pipeline.
    
#     **Route:** `POST /api/v1/upload`
    
#     **Browser Access:** Upload via form or API client
    
#     **cURL Example:**
#     ```bash
#     curl -X POST 'http://localhost:8001/api/v1/upload' \
#          -F 'file=@document.pdf' \
#          -F 'user_id=test_user'
#     ```
    
#     Args:
#         file: Uploaded file (PDF, DOCX, TXT, Image)
#         user_id: ID of the user uploading the document
        
#     Returns:
#         Dict containing document_id and upload status
        
#     Raises:
#         HTTPException: If file upload or processing fails
#     """
#     try:
#         # Validate file
#         if not file.filename:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Filename is required"
#             )
        
#         # Read file content
#         file_content = await file.read()
#         if not file_content:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="File content is empty"
#             )
        
#         # Generate document ID
#         document_id = str(uuid.uuid4())
        
#         # Determine file type
#         file_type = _determine_file_type(file.filename, file.content_type)
        
#         # Create document metadata
#         metadata = DocumentMetadata(
#             document_id=document_id,
#             file_type=file_type,
#             upload_timestamp=datetime.utcnow(),
#             user_id=user_id,
#             file_size=len(file_content)
#         )
        
#         # For steel thread test, create basic parsed document
#         # In full implementation, this would involve actual document parsing
#         parsed_document = ParsedDocument(
#             document_id=document_id,
#             content=f"[Content from {file.filename}] - Steel thread test",
#             metadata=metadata,
#             page_count=1,
#             extracted_images=[],
#             tables=[]
#         )
        
#         # Get event bus and publish document received event
#         event_bus = get_event_bus()
        
#         # Create event data
#         event_data = {
#             "document_id": document_id,
#             "filename": file.filename,
#             "user_id": user_id,
#             "file_size": len(file_content),
#             "upload_timestamp": datetime.utcnow().isoformat(),
#             "parsed_content": parsed_document.content,
#             "page_count": parsed_document.page_count
#         }
        
#         # Publish to Kafka
#         success = event_bus.publish(
#             event_type=EventType.DOCUMENT_RECEIVED,
#             event_data=event_data,
#             key=document_id
#         )
        
#         if not success:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Failed to publish document received event"
#             )
        
#         logger.info(f"Document uploaded and event published: {document_id}")
        
#         return {
#             "document_id": document_id,
#             "filename": file.filename,
#             "status": ProcessingStatus.UPLOADED.value,
#             "message": "Document uploaded successfully and processing started",
#             "file_size": len(file_content),
#             "upload_timestamp": metadata.upload_timestamp.isoformat()
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Upload failed: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Upload failed: {str(e)}"
#         )


# @router.get("/status/{document_id}")
# async def get_document_status(document_id: str) -> Dict[str, Any]:
#     """
#     Get processing status for a document.
    
#     **Route:** `GET /api/v1/status/{document_id}`
    
#     **Browser Access:** `http://localhost:8001/api/v1/status/your-document-id`
    
#     **Example:** `http://localhost:8001/api/v1/status/abc123-def456-ghi789`
    
#     Args:
#         document_id: ID of the document
        
#     Returns:
#         Dict containing document processing status
#     """
#     # For steel thread test, return mock status
#     return {
#         "document_id": document_id,
#         "status": ProcessingStatus.UPLOADED.value,
#         "message": "Steel thread test - document in processing queue"
#     }


# @router.get("/topics")
# async def get_available_topics() -> Dict[str, Any]:
#     """
#     Get list of available Kafka topics for monitoring.
    
#     **Route:** `GET /api/v1/topics`
    
#     **Browser Access:** `http://localhost:8001/api/v1/topics`
    
#     **Description:** View all Kafka topics and producer statistics for system monitoring
    
#     Returns:
#         Dict containing topic information
#     """
#     try:
#         event_bus = get_event_bus()
#         topics = event_bus.get_topics()
#         producer_stats = event_bus.get_producer_stats()
        
#         return {
#             "topics": topics,
#             "producer_stats": producer_stats,
#             "message": "Event bus topic information"
#         }
        
#     except Exception as e:
#         logger.error(f"Failed to get topics: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to get topic information: {str(e)}"
#         )


# # HELPER FUNCTIONS

# def _determine_file_type(filename: str, content_type: str = None) -> FileType:
#     """Determine file type from filename and content type."""
#     filename_lower = filename.lower()
    
#     if filename_lower.endswith('.pdf'):
#         return FileType.PDF
#     elif filename_lower.endswith(('.docx', '.doc')):
#         return FileType.DOCX  
#     elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
#         return FileType.IMAGE
#     elif filename_lower.endswith(('.txt', '.md')):
#         return FileType.TEXT
#     else:
#         # Default to text for unknown types
#         return FileType.TEXT