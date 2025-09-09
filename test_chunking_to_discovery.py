"""
Test script to connect chunking output through discovery to consolidation nodes in isolation.
Uses existing nodes directly without any custom implementations.

Pipeline Flow Tested:
Chunking → Preference Injection → Context Loading → Discovery → Consolidation ✅
"""

import asyncio
import json
from pathlib import Path
import logging

# Import existing nodes directly
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.chunking import chunk_document
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.preference_injection import inject_user_preferences
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.context_loading import load_feedback_context
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.discovery import sequential_discovery
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.consolidation import consolidate_schema
from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import MultiAgentState
from src.backend.doc_processing_system.pipelines.structured_extraction.nodes.classification import  classify_document


async def test_chunking_to_discovery():
    """Test complete pipeline using existing nodes only."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Configuration classes
    class MockChunkingConfig:
        max_tokens = 5128
        overlap_tokens = 200
        use_tiktoken = True

    class MockModelConfig:
        discovery_model = "gemini-2.0-flash"
        consolidation_model = "gemini-2.0-flash"  
        extraction_model = "gemini-2.0-flash"
        openai_api_key = None

    class MockExtractionConfig:
        max_fields = 8
        document_type = "document"
        output_dir = "demo_results"

    class MockSettings:
        chunking = MockChunkingConfig()
        models = MockModelConfig()
        extraction = MockExtractionConfig()

    settings = MockSettings()
    # TODO MISSING DOC_ID when classifying
    # Initial state
    initial_state: MultiAgentState = {
        "document_text": "docs/phases/system_progress_summary.md",
        "document_id": "test_doc_1",
        "chunks": None,
        "progressive_results": None,
        "consolidated_schema": None,
        "final_schema": None,
        "config": None,
        "extractions": None,
        "status": None,
        "error": None,
        "classification": "contract",
        "classification_confidence": 0.9,
        "user_id": "test_user",
        "feedback_context": {},
        "user_preferences": {}
    }
    
    print("=" * 60)
    print("PIPELINE TEST: Using Existing Nodes Only")
    print("=" * 60)
    
    # STEP 1: Chunking
    print("\nSTEP 1: Chunking Node")
    print("-" * 30)
    
    current_state = chunk_document(initial_state, settings)
    print(f"Chunking Status: {current_state.get('status')}")
    if current_state.get('error'):
        print(f"Chunking Error: {current_state['error']}")
        return
    
    chunks = current_state.get('chunks', [])
    print(f"Number of chunks created: {len(chunks)}")
    print("doc id:", current_state.get('document_id'))
    current_state = await classify_document(current_state)
    # STEP 2: Preference Injection
    print("\nSTEP 2: Preference Injection Node")
    print("-" * 35)
    
    try:
        current_state = await inject_user_preferences(current_state)
        print(f"Preference Status: {current_state.get('status')}")
        if current_state.get('error'):
            print(f"Preference Error: {current_state['error']}")
        else:
            user_prefs = current_state.get('user_preferences', {})
            print(f"User preferences loaded: {bool(user_prefs)}")
    except Exception as e:
        print(f"Preference injection failed: {e}")
        current_state['error'] = str(e)
        current_state['status'] = 'preference_injection_failed'
    
    # STEP 3: Context Loading
    print("\nSTEP 3: Context Loading Node")
    print("-" * 30)
    
    try:
        current_state = await load_feedback_context(current_state)
        print(f"Context Status: {current_state.get('status')}")
        if current_state.get('error'):
            print(f"Context Error: {current_state['error']}")
        else:
            feedback_ctx = current_state.get('feedback_context', {})
            print(f"Feedback context loaded: {bool(feedback_ctx)}")
            if feedback_ctx:
                relevant_feedback = feedback_ctx.get('relevant_feedback', [])
                print(f"  Relevant feedback items: {len(relevant_feedback)}")
    except Exception as e:
        print(f"Context loading failed: {e}")
        current_state['error'] = str(e)
        current_state['status'] = 'context_loading_failed'
    
    # STEP 4: Discovery
    print("\nSTEP 4: Discovery Node")
    print("-" * 25)
    
    try:
        current_state = await sequential_discovery(current_state, settings)
        print(f"Discovery Status: {current_state.get('status')}")
        if current_state.get('error'):
            print(f"Discovery Error: {current_state['error']}")
        else:
            progressive_results = current_state.get('progressive_results', [])
            print(f"Progressive results: {len(progressive_results)}")
            
            # Count total discovered fields
            all_fields = []
            for result in progressive_results:
                all_fields.extend(result.discovered_fields)
            print(f"Total fields discovered: {len(all_fields)}")
            
            # Show first few fields
            for i, field in enumerate(all_fields[:3]):
                print(f"  Field {i+1}: {field.field_name} ({field.field_type})")
    except Exception as e:
        print(f"Discovery failed: {e}")
        current_state['error'] = str(e)
        current_state['status'] = 'discovery_failed'
    
    # STEP 5: Consolidation
    print("\nSTEP 5: Consolidation Node")
    print("-" * 30)
    
    try:
        current_state = await consolidate_schema(current_state, settings)
        print(f"Consolidation Status: {current_state.get('status')}")
        if current_state.get('error'):
            print(f"Consolidation Error: {current_state['error']}")
        else:
            consolidated_schema = current_state.get('consolidated_schema')
            if consolidated_schema:
                print(f"Final fields count: {len(consolidated_schema.final_fields)}")
                print(f"Document type: {consolidated_schema.document_type}")
                
                # Show first few consolidated fields
                for i, field in enumerate(consolidated_schema.final_fields[:3]):
                    print(f"  Final Field {i+1}: {field.field_name} ({field.field_type})")
    except Exception as e:
        print(f"Consolidation failed: {e}")
        current_state['error'] = str(e)
        current_state['status'] = 'consolidation_failed'
    
    # STEP 6: Save Results
    print("\nSTEP 6: Saving Results")
    print("-" * 25)
    
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    # Save final state as complete pipeline result
    pipeline_result = {
        "pipeline_status": "completed",
        "final_status": current_state.get('status', 'unknown'),
        "error": current_state.get('error'),
        "classification": current_state.get('classification', 'unknown'),
        "user_id": current_state.get('user_id', 'unknown'),
        "chunk_count": len(current_state.get('chunks', [])),
        "progressive_results_count": len(current_state.get('progressive_results', [])),
        "final_fields_count": len(current_state.get('consolidated_schema', {}).final_fields) if current_state.get('consolidated_schema') else 0,
        
        # Chunking results
        "chunking": {
            "status": "completed" if current_state.get('chunks') else "failed",
            "chunks": len(current_state.get('chunks', []))
        },
        
        # Preference injection results
        "preference_injection": {
            "status": "completed" if current_state.get('user_preferences') else "failed",
            "preferences_loaded": bool(current_state.get('user_preferences'))
        },
        
        # Context loading results
        "context_loading": {
            "status": "completed" if current_state.get('feedback_context') else "failed",
            "context_loaded": bool(current_state.get('feedback_context'))
        },
        
        # Discovery results
        "discovery": {
            "status": "completed" if current_state.get('progressive_results') else "failed",
            "progressive_results": len(current_state.get('progressive_results', [])),
            "total_fields_discovered": len([
                field 
                for result in current_state.get('progressive_results', [])
                for field in result.discovered_fields
            ])
        },
        
        # Consolidation results
        "consolidation": {
            "status": "completed" if current_state.get('consolidated_schema') else "failed",
            "final_fields": len(current_state.get('consolidated_schema', {}).final_fields) if current_state.get('consolidated_schema') else 0
        }
    }
    
    # Save complete pipeline results
    with open(results_dir / "complete_pipeline_results.json", "w") as f:
        json.dump(pipeline_result, f, indent=2)
    
    # Save detailed results for each component
    detailed_results = {
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "token_count": chunk.token_count,
                "text_preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char
            }
            for chunk in current_state.get('chunks', [])
        ],
        "user_preferences": current_state.get('user_preferences', {}),
        "feedback_context": current_state.get('feedback_context', {}),
        "progressive_results": [
            {
                "chunk_id": i,
                "document_type": result.document_type,
                "confidence_level": result.confidence_level,
                "chunk_coverage": result.chunk_coverage,
                "fields_count": len(result.discovered_fields),
                "discovered_fields": [
                    {
                        "field_name": field.field_name,
                        "field_type": field.field_type,
                        "description": field.description,
                        "category": field.category
                    }
                    for field in result.discovered_fields
                ]
            }
            for i, result in enumerate(current_state.get('progressive_results', []))
        ],
        "consolidated_schema": {
            "document_type": current_state.get('consolidated_schema', {}).document_type if current_state.get('consolidated_schema') else "unknown",
            "final_fields_count": len(current_state.get('consolidated_schema', {}).final_fields) if current_state.get('consolidated_schema') else 0,
            "optimization_notes": current_state.get('consolidated_schema', {}).optimization_notes if current_state.get('consolidated_schema') else "",
            "extraction_prompt": current_state.get('consolidated_schema', {}).extraction_prompt if current_state.get('consolidated_schema') else "",
            "final_fields": [
                {
                    "field_name": field.field_name,
                    "field_type": field.field_type,
                    "description": field.description,
                    "category": field.category
                }
                for field in (current_state.get('consolidated_schema', {}).final_fields or [])
            ]
        } if current_state.get('consolidated_schema') else None
    }
    
    with open(results_dir / "detailed_pipeline_results.json", "w") as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nResults saved to:")
    print(f"  - {results_dir / 'complete_pipeline_results.json'}")
    print(f"  - {results_dir / 'detailed_pipeline_results.json'}")
    
    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"Overall Status: {pipeline_result['final_status']}")
    print(f"Classification: {pipeline_result['classification']}")
    print(f"User ID: {pipeline_result['user_id']}")
    print(f"Chunks: {pipeline_result['chunk_count']}")
    print(f"Fields Discovered: {pipeline_result['discovery']['total_fields_discovered']}")
    print(f"Final Fields: {pipeline_result['consolidation']['final_fields']}")
    print(f"\nNode Status:")
    print(f"  ✓ Chunking: {pipeline_result['chunking']['status']}")
    print(f"  ✓ Preferences: {pipeline_result['preference_injection']['status']}")
    print(f"  ✓ Context: {pipeline_result['context_loading']['status']}")
    print(f"  ✓ Discovery: {pipeline_result['discovery']['status']}")
    print(f"  ✓ Consolidation: {pipeline_result['consolidation']['status']}")


if __name__ == "__main__":
    asyncio.run(test_chunking_to_discovery())