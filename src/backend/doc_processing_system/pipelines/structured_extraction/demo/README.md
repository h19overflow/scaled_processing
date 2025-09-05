# Multi-Agent LangExtract Structured Extraction System

Advanced multi-agent system for extracting structured data from full documents using Google's LangExtract framework with progressive schema discovery.

## Architecture

```
Document → Chunking → Sequential Discovery → Schema Consolidation → LangExtract → Results
```

**Key Innovation**: Processes entire documents through sequential multi-agent schema discovery that builds context progressively across chunks.

## Components

### 1. `document_chunker.py`
**Purpose**: Splits documents into token-based overlapping chunks for processing  
**Key Decision**: Uses **TikToken** with fallback to character-based chunking  
**Output**: List of `DocumentChunk` objects with metadata

### 2. `sequential_schema_discovery.py` 
**Purpose**: Progressive schema discovery across document chunks  
**Key Decision**: Each chunk builds on previous discoveries using **Gemini 2.0 Flash**  
**Output**: `ProgressiveSchema` results with cumulative field discovery

### 3. `schema_consolidation.py`
**Purpose**: Consolidates discovered fields into optimized final schema  
**Key Decision**: AI-powered deduplication and prioritization to best fields  
**Output**: `ConsolidatedSchema` with refined extraction classes

### 4. `multi_agent_workflow.py`
**Purpose**: LangGraph orchestration of the complete multi-agent pipeline  
**Key Decision**: 5-step workflow with state management and error handling  
**Output**: `MultiAgentState` with complete extraction results

### 5. `multi_agent_demo.py`
**Purpose**: Main orchestrator for the multi-agent extraction system  
**Key Decision**: Configurable chunk size and field limits for optimization  
**Output**: Console progress + comprehensive results

### 6. `config_generator.py` + `results_handler.py`
**Purpose**: LangExtract configuration and results management  
**Key Decision**: Dual output format for systems and human readability  
**Output**: JSON data + Markdown summaries

## Multi-Agent Pipeline Results

**Test Results** (Hamza CV - 10,477 characters):
- **Chunking**: 2 overlapping chunks (1500 tokens each)
- **Progressive Discovery**: 15-20 total fields discovered across chunks
- **Consolidation**: Optimized to 6-8 high-value extraction classes
- **Final Extraction**: 3-11 structured items (varies due to AI model non-determinism)

**Discovered Schema Categories**:
1. **Contact Information**: Name, email, phone, location, profile URLs
2. **Summary/Objective**: Professional summary and career goals
3. **Education**: Degree details, university, graduation, GPA, coursework
4. **Projects**: Project descriptions with technologies and outcomes
5. **Technical Skills**: Programming languages, frameworks, tools
6. **Languages**: Language proficiency levels
7. **Achievements**: Notable awards and accomplishments
8. **Core Strengths**: Professional competencies and abilities

**Key System Improvements**:
- ✅ **Real Document Examples**: Uses actual text from document (not fake placeholders)
- ✅ **Comprehensive Logging**: Debug logs track every step for troubleshooting  
- ✅ **Robust Error Handling**: Fallback schemas prevent total failure
- ✅ **Flexible Chunking**: Token-based with character fallback

## Usage

```bash
python -m src.backend.doc_processing_system.pipelines.structured_extraction.demo.multi_agent_demo
```

## Key Advantages Over Single-Agent

- ✅ **Full Document Coverage** (no 2000-character limit)
- ✅ **Progressive Context Building** (each chunk aware of previous findings)
- ✅ **Intelligent Optimization** (consolidates duplicates, prioritizes value)
- ✅ **Production Ready** (robust logging, error handling, real examples)
- ✅ **Consistent Schema Discovery** (15-20 fields → 6-8 optimized classes)

## Troubleshooting

**Extraction Inconsistency**: LangExtract results can vary (3-11 items) due to AI model non-determinism. This is normal behavior - the schema discovery remains consistent.

**Debug Logging**: Check `demo_results/extraction_debug_*.log` for detailed execution logs including agent calls, field discovery, and consolidation steps.