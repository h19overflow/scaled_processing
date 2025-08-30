# Implementation Guide - Sprint 0 Foundation

## Quick Start Guide

### Prerequisites
- Python 3.12+ with uv package manager
- Docker Desktop (for service orchestration)
- Git (for version control)

### Environment Setup

1. **Clone and Navigate**
```bash
cd C:\Users\User\Projects\scaled_processing
```

2. **Create Environment File**
```bash
# Create .env file with required variables
echo "GEMINI_API_KEY=your_gemini_key" > .env
echo "POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/document_processing" >> .env
```

3. **Install Dependencies**
```bash
uv sync  # Install all dependencies
```

4. **Start Services** 
```bash
docker-compose up -d  # Start all infrastructure services
```

### Verify Installation

**Test Configuration Loading:**
```python
# Quick test script
from src.backend.doc_processing_system.config.settings import get_settings

settings = get_settings()
print(f"✅ Config loaded: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
```

**Check Service Status:**
```bash
docker ps  # Should show 5 running containers
```

**Access Service UIs:**
- Kafdrop (Kafka UI): http://localhost:9000
- ChromaDB: http://localhost:8000
- PostgreSQL: localhost:5432

## Architecture Overview

### Layer Structure
```
src/backend/doc_processing_system/
├── config/           # Configuration management
├── data_models/      # All data structures
├── api/             # FastAPI endpoints (Sprint 1)
├── messaging/       # Kafka producers/consumers (Sprint 1) 
├── core_services/   # Document processing (Sprint 3)
├── agents/          # AI agents (Sprint 7+)
├── orchestration/   # Prefect workflows (Sprint 3)
└── query/           # Query processing (Sprint 5)
```

### Data Model Organization
```python
# Import pattern - always use specific imports
from data_models.document import Document, FileType
from data_models.chunk import Chunk, TextChunk
from data_models.events import DocumentReceivedEvent
from data_models.extraction import ExtractionResult
from data_models.query import QueryType, UserQuery
```

### Configuration Usage
```python
# Singleton pattern - use globally
from config.settings import get_settings

settings = get_settings()
kafka_servers = settings.KAFKA_BOOTSTRAP_SERVERS
```

## Development Workflow

### 1. Adding New Models
```python
# Always extend existing models, don't create new ones
from data_models.document import Document

class EnhancedDocument(Document):
    # Add new fields only
    processing_metadata: Dict[str, Any] = {}
```

### 2. Event-Driven Pattern
```python
# Publisher
from data_models.events import DocumentReceivedEvent
event = DocumentReceivedEvent(
    document_id="doc_123",
    parsed_document=parsed_doc,
    timestamp=datetime.now()
)
# Send via Kafka producer

# Consumer  
def handle_document_received(event: DocumentReceivedEvent):
    # Process the event
    pass
```

### 3. Interface Compliance
```python
# Always implement required interface methods
class MyDocument(Document):
    def get_content(self) -> str:
        # Must implement this method
        return self.content
    
    def validate(self) -> bool:
        # Must implement this method
        return len(self.content) > 0
```

## Testing Strategy

### Unit Tests
```python
# Test individual models
def test_document_validation():
    doc = Document(
        filename="test.pdf",
        file_type="pdf",
        user_id="user_123",
        file_size=1024
    )
    assert doc.validate() == True
```

### Integration Tests  
```python
# Test event flow
def test_kafka_message_flow():
    # 1. Publish event
    producer.send_document_received("test_doc")
    
    # 2. Verify consumer receives it
    messages = consumer.poll(timeout=5.0)
    assert len(messages) == 1
```

### Service Tests
```bash
# Test Docker services
docker-compose ps  # All should be "Up"
curl http://localhost:9000  # Kafdrop should respond
curl http://localhost:8000/api/v1/heartbeat  # ChromaDB health
```

## Common Patterns

### 1. Error Handling
```python
try:
    result = some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Always include context in errors
    raise ProcessingError(f"Failed to process document {doc_id}: {e}")
```

### 2. Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.info(f"Processing document {document_id}")
logger.error(f"Failed to process: {error_details}")
```

### 3. Type Safety
```python
# Always use type hints
from typing import List, Dict, Optional

def process_chunks(chunks: List[TextChunk]) -> List[ValidatedEmbedding]:
    results: List[ValidatedEmbedding] = []
    # Implementation
    return results
```

## Next Sprint Preparation

### Sprint 1: Messaging Pipeline
- **FastAPI endpoint** - Uses Document and UploadFile models
- **Kafka Producer** - Uses DocumentReceivedEvent
- **Kafka Consumer** - Handles DocumentReceivedEvent
- **Integration test** - End-to-end message flow

### Key Files to Create:
```
messaging/
├── base_producer.py        # Abstract Kafka producer
├── base_consumer.py        # Abstract Kafka consumer  
├── document_producer.py    # Document-specific producer
├── document_consumer.py    # Document-specific consumer
└── event_bus.py           # Central event routing

api/  
├── endpoints/
│   └── upload.py          # File upload endpoint
└── main.py                # FastAPI application
```

## Troubleshooting

### Common Issues

1. **Pydantic Import Error**
```python
# Fix: Use pydantic-settings
from pydantic_settings import BaseSettings  # Not from pydantic
```

2. **Docker Connection Error**
```bash
# Fix: Start Docker Desktop
docker --version  # Should work
docker ps         # Should list containers
```

3. **Configuration Not Loading**
```bash
# Fix: Check .env file exists and has proper format
cat .env  # Should show KEY=value pairs
```

4. **Import Errors**
```python
# Fix: Use absolute imports from project root
from src.backend.doc_processing_system.data_models import Document
# Not: from data_models import Document
```

### Performance Tips

1. **Lazy Loading**: Import models only when needed
2. **Singleton Config**: Use get_settings() globally
3. **Connection Pooling**: Reuse Kafka connections
4. **Type Checking**: Use mypy for static analysis

## Code Quality Standards

### File Organization
- Maximum 150 lines per file
- One class per file (except small helper classes)
- Clear imports at top
- Docstrings for all public methods

### Naming Conventions
```python
# Classes: PascalCase
class DocumentProcessor:

# Functions: snake_case
def process_document():

# Constants: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 1024 * 1024

# Variables: snake_case
document_id = "doc_123"
```

### Documentation
```python
def process_document(file_path: str) -> Document:
    """
    Process a document file and return Document instance.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Document: Processed document with metadata
        
    Raises:
        ProcessingError: If document cannot be processed
    """
```

This foundation supports rapid development of the remaining sprints while maintaining code quality and architectural consistency.