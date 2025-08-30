"""
Startup script for the Document Processing System FastAPI server.
Run this to start the API server with proper configuration.
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src" / "backend"
sys.path.insert(0, str(src_path))

def start_server():
    """Start the FastAPI server with optimal settings."""
    print("=== Document Processing System API Server ===")
    print(f"Project root: {project_root}")
    print(f"Python path includes: {src_path}")
    print("")
    print("Starting server...")
    print("📖 API Documentation: http://localhost:8001/docs")
    print("📋 API Routes Info: http://localhost:8001/docs-info")
    print("❤️ Health Check: http://localhost:8001/health")
    print("")
    print("Available endpoints:")
    print("  POST /api/v1/upload - Upload document")
    print("  GET  /api/v1/status/{document_id} - Check status")
    print("  GET  /api/v1/topics - View Kafka topics")
    print("")
    print("ChromaDB is running on port 8000, FastAPI on 8001")
    print("")
    
    # Start the server
    uvicorn.run(
        "doc_processing_system.api.main:app",
        host="0.0.0.0",
        port=8001,  # Changed to avoid ChromaDB conflict
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()