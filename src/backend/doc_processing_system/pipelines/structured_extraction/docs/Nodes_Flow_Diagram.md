# Structured Extraction Nodes - High-Level Flow Overview

This document provides a high-level overview of all structured extraction pipeline nodes and their data flow relationships.

## Complete Pipeline Flow

```
┌─────────────────┐
│   Document      │
│   Input         │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Classification │ ◄─── Determines document type (contract, invoice, etc.)
│     Node        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│    Chunking     │ ◄─── Splits document into processable chunks
│     Node        │      (5128 tokens max, 200 overlap)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Preference     │ ◄─── Loads user preferences for classification
│  Injection      │      (field priorities, extraction style)
│     Node        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Context       │ ◄─── Loads feedback context from previous runs
│   Loading       │      (common issues, field corrections)
│     Node        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Discovery     │ ◄─── AI agent discovers extractable fields
│     Node        │      (progressive schema building)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Consolidation   │ ◄─── Merges discoveries into final schema
│     Node        │      (deduplication, validation)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Config Gen     │ ◄─── Generates extraction configuration
│     Node        │      (agent scaling, task distribution)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Extraction     │ ◄─── Executes field extraction using agents
│     Node        │      (structured data output)
└─────────────────┘
```

## Node Descriptions

### 🏷️ Classification Node
**File**: `classification.py`
**Purpose**: Determines document type for context-aware processing
**Input**: Raw document content
**Output**: Classification (e.g., "contract", "invoice", "resume") + confidence score
**Dependencies**: Classification AI model

### 📄 Chunking Node  
**File**: `chunking.py`
**Purpose**: Splits documents into manageable chunks for processing
**Input**: Document text/markdown content
**Output**: List of DocumentChunk objects with token counts and positions
**Configuration**: Max tokens (5128), overlap tokens (200), tiktoken encoding

### 👤 Preference Injection Node
**File**: `preference_injection.py`  
**Purpose**: Loads user-specific extraction preferences
**Input**: User ID + Document classification
**Output**: User preferences (field priorities, extraction style, custom instructions)
**Dependencies**: PreferenceManager, PostgreSQL database

### 🔄 Context Loading Node
**File**: `context_loading.py`
**Purpose**: Loads relevant feedback context from previous extractions
**Input**: User ID + Document classification  
**Output**: Feedback context (common issues, field corrections, context prompts)
**Dependencies**: FeedbackContextManager, PostgreSQL database

### 🔍 Discovery Node
**File**: `discovery.py`
**Purpose**: AI-powered field discovery using enhanced context
**Input**: Chunks + User preferences + Feedback context
**Output**: Progressive schema with discovered fields per chunk
**Dependencies**: Discovery AI agent (Gemini), enhanced prompts

### 🔗 Consolidation Node
**File**: `consolidation.py`
**Purpose**: Merges progressive discoveries into unified schema
**Input**: List of progressive schemas from discovery
**Output**: Consolidated schema with deduplicated and validated fields
**Dependencies**: Consolidation AI agent

### ⚙️ Config Generation Node
**File**: `config_gen.py`
**Purpose**: Generates extraction configuration and agent scaling
**Input**: Consolidated schema + Document complexity metrics
**Output**: Extraction configuration (agent count, task distribution)
**Dependencies**: Configuration generation logic

### 🎯 Extraction Node
**File**: `extraction.py`
**Purpose**: Executes actual field extraction using configured agents
**Input**: Document content + Extraction configuration + Schema
**Output**: Structured extraction results with field values
**Dependencies**: Extraction AI agents, parallel processing

## Data Flow States

### MultiAgentState Structure
The pipeline uses a shared state dictionary that flows through all nodes:

```python
{
    "document_id": str,           # Unique document identifier
    "document_text": str,         # Document content/path
    "classification": str,        # Document type classification
    "classification_confidence": float,
    "user_id": str,              # User identifier
    "chunks": List[DocumentChunk], # Document chunks
    "user_preferences": Dict,     # User extraction preferences  
    "feedback_context": Dict,     # Previous feedback context
    "progressive_results": List,  # Discovery results per chunk
    "consolidated_schema": Dict,  # Merged field schema
    "final_schema": Dict,        # Validated final schema
    "config": Dict,              # Extraction configuration
    "extractions": Dict,         # Final extracted data
    "status": str,               # Current processing status
    "error": str                 # Error information if any
}
```

## Processing Modes

### 🔄 Sequential Processing (Default)
Each node processes the complete state and passes enhanced state to next node:
```
State₀ → Node₁ → State₁ → Node₂ → State₂ → ... → Final State
```

### 🌟 Enhanced Context Mode
Preference injection and context loading enhance discovery with:
- **User Preferences**: Field priorities, extraction styles, custom instructions
- **Feedback Context**: Common issues, field corrections from previous runs
- **Progressive Discovery**: Each chunk builds on previous chunk discoveries

### ⚡ Parallel Processing (Future)
Some nodes support parallel processing for performance:
```
Chunks → [Discovery₁, Discovery₂, Discovery₃] → Consolidation
```

## Node Dependencies

### Database Dependencies
```
┌─────────────────┐    ┌──────────────┐
│  Preference     │───→│ PostgreSQL   │
│  Injection      │    │   Database   │
└─────────────────┘    │              │
┌─────────────────┐    │  - user_prefs│
│   Context       │───→│  - feedback  │
│   Loading       │    │  - schemas   │
└─────────────────┘    └──────────────┘
```

### AI Model Dependencies
```
┌─────────────────┐    ┌──────────────┐
│ Classification  │───→│ Gemini 2.0   │
└─────────────────┘    │   Flash      │
┌─────────────────┐    │              │
│   Discovery     │───→│ - classify   │
└─────────────────┘    │ - discover   │
┌─────────────────┐    │ - extract    │
│ Consolidation   │───→│              │
└─────────────────┘    └──────────────┘
┌─────────────────┐
│  Extraction     │
└─────────────────┘
```

## Error Handling Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Node     │───→│   Error?    │───→│   Fallback  │
│ Processing  │    │             │    │   Logic     │
└─────────────┘    └─────┬───────┘    └─────────────┘
                         │                    │
                         ▼                    │
                   ┌─────────────┐            │
                   │  Continue   │◄───────────┘
                   │ Processing  │
                   └─────────────┘
```

### Fallback Strategies
- **Classification**: Default to "document" type
- **Chunking**: Use basic text splitting if tiktoken fails
- **Preferences**: Use default extraction preferences
- **Context**: Continue without feedback context
- **Discovery**: Use fallback schema with basic fields
- **Extraction**: Return partial results with errors

## Performance Characteristics

### Node Processing Times (Estimated)
```
Classification  : ~1-2 seconds  (AI inference)
Chunking       : ~0.1 seconds  (Text processing)
Preference     : ~0.05 seconds (Database query)
Context        : ~0.1 seconds  (Database query)
Discovery      : ~3-5 seconds  (AI inference per chunk)
Consolidation  : ~1-2 seconds  (AI inference)
Config Gen     : ~0.1 seconds  (Logic processing)
Extraction     : ~5-10 seconds (AI inference, depends on schema)
```

### Bottlenecks
1. **AI Model Calls**: Discovery and Extraction nodes (parallel processing helps)
2. **Database Queries**: Preference and Context loading (caching helps)
3. **Token Limits**: Large documents require more chunks (affects Discovery time)

## Integration Points

### Input Sources
- **File Upload API**: Direct document upload
- **File Watcher**: Automated processing of dropped files
- **Kafka Messages**: Event-driven document processing

### Output Destinations  
- **Database Storage**: Extraction results and schemas
- **JSON Files**: Structured output for downstream systems
- **Kafka Events**: Processing completion notifications

## Testing Flow

The test script (`test_chunking_to_discovery.py`) validates the core flow:

```
Test Document → Chunking → Preferences → Context → Discovery → Results
     ↓              ↓           ↓          ↓         ↓         ↓
   ✅ MD File    ✅ 3 Chunks  ✅ Loaded  ✅ Loaded ✅ Fields ✅ Saved
```

## Future Enhancements

### Planned Node Additions
1. **Validation Node**: Schema and result validation
2. **Optimization Node**: Performance optimization suggestions
3. **Export Node**: Multiple output format generation
4. **Monitoring Node**: Performance and quality metrics collection

### Processing Improvements
1. **Streaming**: Real-time processing of large documents
2. **Caching**: Intelligent caching of preferences and context
3. **Batching**: Multi-document processing optimization
4. **Retry Logic**: Enhanced error recovery mechanisms

This flow diagram provides the foundation for understanding how structured extraction processes documents through multiple specialized nodes to produce high-quality, context-aware field extractions.