"""
Task Configuration - Centralized configuration for all RAG processing tasks

Contains timeout, retry, and other configuration constants for modular tasks.
"""

# Task Configuration Constants
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds

# Timeout Configuration  
CHUNKING_TIMEOUT = 300  # 5 minutes
EMBEDDING_TIMEOUT = 600  # 10 minutes
STORAGE_TIMEOUT = 120   # 2 minutes

# Default Parameters
DEFAULT_CHUNK_SIZE = 700
DEFAULT_SEMANTIC_THRESHOLD = 0.75
DEFAULT_CONCURRENT_AGENTS = 10
DEFAULT_BOUNDARY_CONTEXT = 200
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
DEFAULT_CHUNKING_MODEL = "gemini-2.0-flash"
DEFAULT_BATCH_SIZE = 32
DEFAULT_COLLECTION_NAME = "rag_documents"