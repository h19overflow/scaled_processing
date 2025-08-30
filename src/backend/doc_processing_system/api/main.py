"""
FastAPI application for document processing system.
Provides REST API endpoints for document upload and processing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .endpoints import ingestion

app = FastAPI(
    title="Document Processing System",
    description="Hybrid RAG system for document processing and querying",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Document Processing System API", "status": "healthy"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/docs-info")
async def docs_info():
    """API documentation information with full route URLs."""
    return {
        "message": "Document Processing System API",
        "version": "1.0.0",
        "documentation": {
            "interactive_docs": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "root": "/",
            "upload_document": "/api/v1/upload",
            "document_status": "/api/v1/status/{document_id}",
            "kafka_topics": "/api/v1/topics"
        },
        "usage_examples": {
            "upload_curl": "curl -X POST 'http://localhost:8001/api/v1/upload' -F 'file=@document.pdf' -F 'user_id=test_user'",
            "status_check": "http://localhost:8001/api/v1/status/{document_id}",
            "topics_info": "http://localhost:8001/api/v1/topics"
        },
        "note": "FastAPI runs on port 8001 (ChromaDB uses port 8000)"
    }