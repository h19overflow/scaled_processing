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
- **Chunking**: 4 overlapping chunks (800 tokens each)
- **Progressive Discovery**: 21 total fields discovered across chunks
- **Consolidation**: Optimized to 4 high-value extraction classes
- **Final Extraction**: 43 targeted structured items

**Discovered Schema**:
1. **Skills**: Technical skills, tools, and technologies
2. **Projects**: Project descriptions with technologies used  
3. **Core Strengths**: Candidate abilities with proficiency levels
4. **Education**: Academic details including graduation and GPA

## Usage

```bash
python -m src.backend.doc_processing_system.pipelines.structured_extraction.demo.multi_agent_demo
```

## Key Advantages Over Single-Agent

- ✅ **Full Document Coverage** (no 2000-character limit)
- ✅ **Progressive Context Building** (each chunk aware of previous findings)
- ✅ **Intelligent Optimization** (consolidates duplicates, prioritizes value)
- ✅ **Better Quality Results** (43 targeted vs 104 redundant extractions)