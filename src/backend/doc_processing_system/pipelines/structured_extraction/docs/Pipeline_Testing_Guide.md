# Structured Extraction Pipeline Testing Guide

This document provides comprehensive guidance for testing the structured extraction pipeline in isolation, including individual nodes and complete end-to-end workflows.

## Overview

The structured extraction pipeline consists of four main nodes that work together to process documents and extract structured data:

1. **Chunking Node** (`nodes/chunking.py`) - Processes documents into chunks for analysis
2. **Preference Injection Node** (`nodes/preference_injection.py`) - Loads user preferences for extraction customization
3. **Context Loading Node** (`nodes/context_loading.py`) - Loads relevant feedback context from previous extractions
4. **Discovery Node** (`nodes/discovery.py`) - Discovers extractable fields using AI agents with enhanced context

## Complete Pipeline Test

### Test Script Location
```
test_chunking_to_discovery.py
```

### Test Architecture
The test script demonstrates the complete data flow through all four nodes:
```
Document → Chunking → Preference Injection → Context Loading → Discovery → Results
```

### Running the Complete Test

```bash
python test_chunking_to_discovery.py
```

## Test Configuration

### Document Classification
- **Classification**: `contract` (configurable)
- **User ID**: `test_user` (configurable)
- **Document**: `docs/phases/system_progress_summary.md`

### Chunking Configuration
```python
class MockChunkingConfig:
    max_tokens = 5128
    overlap_tokens = 200
    use_tiktoken = True
```

### Model Configuration
```python
class MockModelConfig:
    discovery_model = "gemini-2.0-flash"
    consolidation_model = "gemini-2.0-flash"
    extraction_model = "gemini-2.0-flash"
```

## Test Results Structure

The test creates comprehensive results in the `test_results/` directory:

### Generated Files

1. **`chunking_results.json`** - Chunking node output with token counts and chunk previews
2. **`preference_results.json`** - User preferences loaded for the classification
3. **`context_results.json`** - Feedback context loaded from previous extractions
4. **`discovery_results.json`** - Complete discovery results with enhanced context
5. **`prompts_summary.json`** - Summary of all captured prompts
6. **`chunk_0_prompt.txt`** - Full prompt for chunk 0 (no previous discoveries)
7. **`chunk_1_prompt.txt`** - Full prompt for chunk 1 (with previous discoveries)
8. **`chunk_2_prompt.txt`** - Full prompt for chunk 2 (with accumulated context)

### Sample Results

#### Preference Loading Success
```json
{
  "status": "preferences_loaded",
  "user_preferences": {
    "field_preferences": {
      "field_priorities": {
        "employee_name": {"weight": 0.9, "required": true},
        "company_name": {"weight": 0.9, "required": true},
        "salary": {"weight": 0.9, "required": true}
      }
    },
    "extraction_style": {
      "verbosity": "detailed",
      "confidence_threshold": 0.8
    },
    "prompt_instructions": "Focus on employment terms and legal obligations"
  }
}
```

#### Context Loading Success
```json
{
  "status": "context_loaded",
  "feedback_context": {
    "relevant_feedback": [
      {
        "rating": 3,
        "comment": "Salary format needs improvement. Extract salary as structured amount with currency",
        "type": "field_format"
      }
    ],
    "common_issues": [
      "Salary format needs improvement. Extract salary as structured amount with currency",
      "Missing termination clause information. Please extract termination conditions when available"
    ]
  }
}
```

#### Discovery Results
```json
{
  "status": "discovery_complete",
  "classification": "contract",
  "user_id": "test_user",
  "preference_injection_status": "preferences_loaded",
  "context_loading_status": "context_loaded",
  "user_preferences_loaded": true,
  "feedback_context_loaded": true,
  "total_fields_discovered": 3,
  "discovered_fields": [
    {
      "field_name": "workflow_types",
      "field_type": "List[str]",
      "description": "List of workflow types the document is prepared for",
      "category": "Document Processing"
    }
  ]
}
```

## Pipeline Node Testing

### Individual Node Testing

Each node can be tested individually by importing and calling the node function:

#### Chunking Node Test
```python
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.chunking import chunk_document

# Test chunking with markdown file
result = chunk_document(state, settings)
print(f"Chunks created: {len(result['chunks'])}")
```

#### Preference Injection Test  
```python
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.preference_injection import inject_user_preferences

# Test preference loading
result = await inject_user_preferences(state)
print(f"Status: {result['status']}")
```

#### Context Loading Test
```python
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.context_loading import load_feedback_context

# Test context loading
result = await load_feedback_context(state)
print(f"Context items: {len(result['feedback_context'].get('relevant_feedback', []))}")
```

#### Discovery Node Test
```python
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.discovery import sequential_discovery

# Test discovery with enhanced context
result = await sequential_discovery(state, settings)
print(f"Fields discovered: {len(result['progressive_results'])}")
```

## Enhanced Context Integration

### Prompt Enhancement

The pipeline demonstrates how user preferences and feedback context enhance the discovery prompts:

```
You are analyzing chunk #0 of a contract document for user test_user.

USER PREFERENCES:
Special instructions: Focus on employment terms and legal obligations
High priority fields: employee_name, company_name, position, salary, start_date
Extraction style: verbosity: detailed, minimum confidence: 0.8

FEEDBACK CONTEXT:
Based on previous user feedback, please pay special attention to:
Common issues to avoid:
- Salary format needs improvement. Extract salary as structured amount with currency
- Missing termination clause information. Please extract termination conditions when available
```

### Progressive Discovery

Each chunk builds on previous discoveries:
- **Chunk 0**: No previous discoveries, starts fresh
- **Chunk 1**: Includes fields discovered in Chunk 0
- **Chunk 2**: Includes fields discovered in Chunks 0 and 1

## Database Dependencies

### Requirements
The preference injection and context loading nodes require:
- PostgreSQL database connection
- Populated user preferences for the test classification
- Feedback data for context enhancement

### Database Configuration
```python
# Connection configured via ConnectionManager
connection_manager = ConnectionManager()
# Uses environment variables for database connection
```

### Test Data Requirements

For complete testing, ensure test data exists:

#### User Preferences Table
```sql
INSERT INTO user_preferences (user_id, classification, field_preferences, extraction_style, prompt_instructions)
VALUES ('test_user', 'contract', {...}, {...}, 'Focus on employment terms and legal obligations');
```

#### Feedback Data Table
```sql
INSERT INTO document_feedback (classification, feedback_type, comment, fields)
VALUES ('contract', 'field_format', 'Salary format needs improvement', {...});
```

## Error Handling and Fallbacks

### Node Failure Handling
Each node includes comprehensive error handling:

```python
try:
    # Node processing logic
    result = process_node(state)
    return {"status": "success", "data": result}
except Exception as e:
    logger.error(f"Node failed: {e}")
    return {"status": "failed", "error": str(e)}
```

### Discovery Fallback
The discovery node includes fallback schema generation when AI processing fails:

```python
def _create_fallback_schema(chunks) -> List[ProgressiveSchema]:
    """Create fallback schema when AI fails."""
    basic_fields = [
        FieldSchema(
            field_name="personal_info",
            field_type="contact",
            description="Name, email, phone, location"
        )
    ]
    # Return basic schema for all chunks
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```
Error: ConnectionManager failed to connect
Solution: Ensure PostgreSQL is running and credentials are correct
```

#### Async/Await Errors
```
Error: object dict can't be used in 'await' expression
Solution: Check if methods being awaited are actually async functions
```

#### Model Loading Errors
```
Error: Model 'gemini-2.0-flash' not available
Solution: Verify API keys and model availability
```

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

## Performance Considerations

### Chunking Performance
- Larger `max_tokens` = fewer chunks but larger context windows
- Smaller `max_tokens` = more chunks but better granularity
- `overlap_tokens` provides context continuity between chunks

### Discovery Performance  
- Sequential processing ensures context building between chunks
- Parallel processing possible but loses progressive context
- Agent model selection impacts processing speed and quality

## Future Enhancements

### Planned Improvements
1. **Parallel Processing**: Option for parallel chunk processing when context isn't critical
2. **Caching**: Cache user preferences and feedback context to reduce database queries
3. **Batch Processing**: Process multiple documents in a single test run
4. **Metrics Collection**: Capture performance metrics during testing
5. **Visual Results**: Generate visualizations of discovered fields and relationships

## Integration Testing

### Full Workflow Test
The test script demonstrates integration with:
- Document processing (via chunking)
- Database operations (via preferences and context)
- AI model inference (via discovery)
- Result serialization and storage

### Production Readiness
The tested pipeline is production-ready with:
- ✅ Error handling and fallbacks
- ✅ Comprehensive logging
- ✅ Database integration
- ✅ AI model integration
- ✅ Result capture and analysis
- ✅ Progressive context building
- ✅ User preference customization
- ✅ Feedback-driven improvements

## Usage Examples

### Basic Test Run
```bash
# Run complete pipeline test
python test_chunking_to_discovery.py

# Expected output:
# STEP 1: Running Chunking Node
# STEP 2: Preference Injection Node  
# STEP 3: Context Loading Node
# STEP 4: Discovery Node with Enhanced Context
# STEP 5: Saving Results
```

### Custom Configuration Test
```python
# Modify test for different classification
chunking_state["classification"] = "invoice"
chunking_state["user_id"] = "custom_user"

# Run with different chunk size
MockChunkingConfig.max_tokens = 2048
```

### Results Analysis
```python
# Load and analyze results
import json
with open("test_results/discovery_results.json", "r") as f:
    results = json.load(f)
    
print(f"Fields discovered: {results['total_fields_discovered']}")
print(f"Context loaded: {results['feedback_context_loaded']}")
```

This comprehensive testing framework ensures the structured extraction pipeline works correctly end-to-end with all enhancements and integrations properly validated.