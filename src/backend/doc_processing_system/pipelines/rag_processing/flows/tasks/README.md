# RAG Processing Tasks Module

This module contains the modular task definitions for the RAG processing pipeline. Each task is defined in its own file for better maintainability and separation of concerns.

## Module Structure

```
tasks/
├── __init__.py                    # Task imports and module exports
├── config.py                     # Centralized task configuration
├── semantic_chunking_task.py     # Stage 1: Semantic chunking
├── boundary_refinement_task.py   # Stage 2: Boundary refinement
├── chunk_formatting_task.py      # Stage 3: Chunk formatting
├── embeddings_generation_task.py # Stage 4: Embeddings generation
├── vector_storage_task.py        # Stage 5: Vector storage
└── README.md                     # This documentation
```

## Task Overview

### Stage 1: Semantic Chunking (`semantic_chunking_task.py`)
- **Purpose**: Initial document splitting using semantic similarity
- **Input**: Document file path and document ID
- **Output**: Initial chunks with metadata
- **Configuration**: Chunk size, semantic threshold
- **Timeout**: 150 seconds (half of chunking timeout)

### Stage 2: Boundary Refinement (`boundary_refinement_task.py`)
- **Purpose**: LLM-based boundary review and refinement
- **Input**: Stage 1 results (initial chunks)
- **Output**: Refined chunks with boundary decisions
- **Configuration**: Concurrent agents, model name, context window
- **Timeout**: 150 seconds (half of chunking timeout)

### Stage 3: Chunk Formatting (`chunk_formatting_task.py`)
- **Purpose**: Format chunks into TextChunk models and save to file
- **Input**: Stage 2 results (refined chunks)
- **Output**: Formatted TextChunk models and file path
- **Configuration**: None (quick formatting operation)
- **Timeout**: 60 seconds

### Stage 4: Embeddings Generation (`embeddings_generation_task.py`)
- **Purpose**: Generate vector embeddings from processed chunks
- **Input**: Chunks file path from Stage 3
- **Output**: Embeddings file with ValidatedEmbedding models
- **Configuration**: Model name, batch size
- **Timeout**: 600 seconds (10 minutes)

### Stage 5: Vector Storage (`vector_storage_task.py`)
- **Purpose**: Store embeddings in ChromaDB (placeholder implementation)
- **Input**: Embeddings file path from Stage 4
- **Output**: Storage confirmation and metadata
- **Configuration**: Collection name
- **Timeout**: 120 seconds (2 minutes)

## Configuration

All tasks use centralized configuration from `config.py`:

```python
# Retry Configuration
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
# ... other defaults
```

## Usage

Tasks are imported and used in the main flow:

```python
from .tasks import (
    semantic_chunking_task,
    boundary_refinement_task,
    chunk_formatting_task,
    generate_embeddings_task,
    store_vectors_task
)

# Usage in flow
stage1_result = await semantic_chunking_task(file_path, document_id)
stage2_result = await boundary_refinement_task(stage1_result)
# ... etc
```

## Error Handling

Each task includes:
- **Retry Logic**: Up to 3 retries with 30-second delays
- **Timeout Protection**: Individual timeouts per stage
- **Comprehensive Logging**: Detailed progress and error information
- **Exception Propagation**: Proper error handling with context

## Dependencies

Tasks have minimal dependencies and import components locally to avoid DLL loading issues:

- `prefect`: Task decoration and logging
- `pathlib`: File path handling
- `datetime`: Timestamp generation
- `typing`: Type hints
- Pipeline components (imported locally within tasks)

## Modular Benefits

This modular structure provides:

1. **Separation of Concerns**: Each task focuses on a single responsibility
2. **Maintainability**: Easy to modify individual stages without affecting others
3. **Testing**: Tasks can be tested independently
4. **Reusability**: Tasks can be composed into different workflows
5. **Configuration Management**: Centralized settings in `config.py`
6. **Documentation**: Clear task-specific documentation and type hints