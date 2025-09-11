#!/usr/bin/env python3
"""
Demo script to showcase the refactored Prefect pipeline with saved results.

Usage:
    python -m src.backend.doc_processing_system.pipelines.structured_extraction.core.demo_pipeline

Results will be saved to: demo_results/
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from .prefect_tasks import structured_extraction_flow
from ..config.settings import Settings


def create_demo_results_dir():
    """Create demo results directory."""
    results_dir = Path("demo_results")
    results_dir.mkdir(exist_ok=True)
    return results_dir


def save_intermediate_results(state, step_name, results_dir):
    """Save intermediate results for each pipeline step."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{step_name}_{timestamp}.json"
    filepath = results_dir / filename
    
    # Prepare serializable data
    step_data = {
        "step": step_name,
        "timestamp": datetime.now().isoformat(),
        "status": state.status,
        "error": state.error,
        "document_id": state.document_id,
        "user_id": state.user_id,
        "classification": state.classification,
        "classification_confidence": state.classification_confidence,
        "chunks_count": len(state.chunks or []),
        "progressive_results_count": len(state.progressive_results or []),
        "config_available": bool(state.config),
        "extractions_count": len(state.extractions or []),
        "task_execution_log": state.task_execution_log
    }
    
    # Add detailed data for specific steps
    if step_name == "final_results" and state.extractions:
        step_data["extractions"] = state.extractions
        
    if state.progressive_results and step_name in ["discovery", "final_results"]:
        step_data["progressive_results_sample"] = [
            {
                "document_type": pr.document_type,
                "confidence_level": pr.confidence_level,
                "chunk_coverage": pr.chunk_coverage,
                "fields_count": len(pr.discovered_fields),
                "sample_fields": [
                    {
                        "field_name": field.field_name,
                        "field_type": field.field_type,
                        "category": field.category
                    } for field in pr.discovered_fields[:3]  # First 3 fields as sample
                ]
            } for pr in state.progressive_results[:2]  # First 2 results as sample
        ]
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(step_data, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Saved {step_name} results to: {filepath}")


async def run_demo_pipeline():
    """Run the demo pipeline with result saving."""
    print("🚀 Starting Prefect Pipeline Demo")
    print("=" * 50)
    
    # Create results directory
    results_dir = create_demo_results_dir()
    print(f"📁 Results will be saved to: {results_dir.absolute()}")
    
    # Read the actual document from docling processing
    document_path = "data/temp/docling/Covering_Letter_-_AHMED_HAMZA_KHALED_MAHMOUD/Covering_Letter_-_AHMED_HAMZA_KHALED_MAHMOUD_vision_enhanced.md"
    
    try:
        with open(document_path, 'r', encoding='utf-8') as f:
            document_content = f.read()
        print(f"📄 Loaded document from: {document_path}")
        print(f"📊 Document length: {len(document_content)} characters")
    except FileNotFoundError:
        print(f"❌ Could not find document at: {document_path}")
        print("📋 Using fallback document instead")
        document_content = """
        MEDICAL INSURANCE CONFIRMATION LETTER
        
        Student Name: AHMED HAMZA KHALED MAHMOUD
        Student ID: 1211309695
        Passport Number: A31074358
        Country: EGYPT
        Institution: MULTIMEDIA UNIVERSITY (MMU) CYBER
        Plan Type: BM200
        Start Date: 14.02.2025
        Expiry Date: 13.02.2026
        
        This confirms medical & health insurance coverage for the international student.
        """
    
    # Test document
    demo_documents = {
        "insurance_confirmation": document_content
    }
    
    # Test each document type
    for doc_type, document_text in demo_documents.items():
        print(f"\n🔄 Processing {doc_type.replace('_', ' ').title()}")
        print("-" * 30)
        
        try:
            # Create settings
            settings = Settings()
            
            # Run pipeline
            result = await structured_extraction_flow(
                document_text=document_text,
                document_id=f"demo_{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                settings=settings,
                user_id="test_user"
            )
            
            # Save results
            save_intermediate_results(result, f"{doc_type}_final_results", results_dir)
            
            # Print summary
            print(f"✅ Status: {result.status}")
            print(f"🏷️  Classification: {result.classification} ({result.classification_confidence:.2f})")
            print(f"📊 Chunks: {len(result.chunks or [])}")
            print(f"🔍 Discovery Results: {len(result.progressive_results or [])}")
            print(f"📋 Extractions: {len(result.extractions or [])}")
            
            if result.extractions:
                print("📈 Sample Extractions:")
                for i, extraction in enumerate(result.extractions[:3]):
                    print(f"   {i+1}. {extraction}")
            
        except Exception as e:
            print(f"❌ Error processing {doc_type}: {e}")
    
    # Create summary report
    summary_file = results_dir / "demo_summary.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# Prefect Pipeline Demo Results\n\n")
        f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Features Demonstrated\n\n")
        f.write("✅ **Generic Task Wrapper**: All tasks use standardized error handling and logging\n\n")
        f.write("✅ **Centralized State Management**: State conversion handled in PipelineState methods\n\n")
        f.write("✅ **Prefect Native Logging**: Enhanced logging with get_run_logger()\n\n")
        f.write("✅ **Async Standardization**: All tasks now use async pattern consistently\n\n")
        f.write("✅ **Critical vs Non-Critical Tasks**: Smart error handling based on task importance\n\n")
        f.write("✅ **Task Execution Monitoring**: Detailed logging of each pipeline step\n\n")
        f.write("## Document Types Processed\n\n")
        f.write("- Insurance Confirmation Letter (AHMED HAMZA KHALED MAHMOUD)\n\n")
        f.write("## Results Location\n\n")
        f.write(f"All intermediate results saved to: `{results_dir.absolute()}`\n\n")
        f.write("## Pipeline Architecture\n\n")
        f.write("1. **Document Classification** (non-critical)\n")
        f.write("2. **Context Loading** (non-critical)\n")
        f.write("3. **Preference Injection** (non-critical)\n")
        f.write("4. **Document Chunking** (critical)\n")
        f.write("5. **Sequential Discovery** (critical)\n")
        f.write("6. **Config Generation** (critical)\n")
        f.write("7. **Data Extraction** (critical)\n\n")
        f.write("*Critical tasks will stop the pipeline on failure, non-critical tasks continue with warnings.*\n")
    
    print(f"\n📝 Demo summary saved to: {summary_file.absolute()}")
    print("\n🎉 Demo completed successfully!")


def main():
    """Main entry point for the demo."""
    try:
        asyncio.run(run_demo_pipeline())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    main()