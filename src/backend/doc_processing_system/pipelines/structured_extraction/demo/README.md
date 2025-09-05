# LangExtract Structured Extraction Demo

Simple proof-of-concept for extracting structured data from documents using Google's LangExtract framework with LangGraph orchestration.

## Architecture

```
Document → Schema Discovery → Config Generation → LangExtract → Results
```

## Components

### 1. `schema_discovery.py`
**Purpose**: Analyzes documents to identify extractable fields  
**Key Decision**: Uses **Gemini 2.0 Flash** to discover document type and extraction classes  
**Output**: `DocumentSchema` with field specifications and extraction prompt

### 2. `config_generator.py` 
**Purpose**: Converts discovered schemas into langextract configuration  
**Key Decision**: Creates example data for langextract training  
**Output**: Langextract-compatible config with prompt and examples

### 3. `extraction_workflow.py`
**Purpose**: LangGraph orchestration of the extraction pipeline  
**Key Decision**: Sequential workflow: discover → generate → extract  
**Output**: Complete extraction state with results

### 4. `results_handler.py`
**Purpose**: Saves extraction results and generates reports  
**Key Decision**: Dual output - JSON for systems, Markdown for humans  
**Output**: Structured files in `demo_results/`

### 5. `langextract_demo.py`
**Purpose**: Main orchestrator that runs the complete demo  
**Key Decision**: Simple async interface for testing  
**Output**: Console summary + saved results

## Key Design Decisions

- **Schema Discovery**: Gemini 2.0 Flash analyzes documents to suggest extraction fields
- **Simple Workflow**: Linear LangGraph pipeline (no complex branching)
- **Fallback Strategy**: Mock extractions when langextract unavailable
- **Dual Serialization**: Handle both langextract objects and JSON storage

## Usage

```bash
python -m src.backend.doc_processing_system.pipelines.structured_extraction.demo.langextract_demo
```

Processes `Hamza_CV_Updated_processed.md` and saves results to `demo_results/`.

## Example Output

- **Discovered Schema**: Resume with personal_info + skills extraction classes
- **Extractions**: 104 items (4 personal details + 100 technical skills)
- **Categories**: Automatic attribute assignment for context