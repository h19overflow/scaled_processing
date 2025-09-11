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


def save_comprehensive_observability(state, doc_type, results_dir):
    """Save comprehensive observability files for full pipeline tracking."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_id = state.document_id
    
    # Create document-specific subdirectory
    doc_dir = results_dir / f"{doc_type}_{timestamp}"
    doc_dir.mkdir(exist_ok=True)
    
    # 1. DISCOVERED FIELDS FILE
    save_discovered_fields(state, doc_dir, doc_id, timestamp)
    
    # 2. EXTRACTIONS FILE  
    save_extractions_file(state, doc_dir, doc_id, timestamp)
    
    # 3. TIMING METRICS FILE
    save_timing_metrics(state, doc_dir, doc_id, timestamp)
    
    # 4. INTERMEDIATE RESULTS FILE
    save_intermediate_results_file(state, doc_dir, doc_id, timestamp)
    
    # 5. EXECUTION SUMMARY FILE
    save_execution_summary(state, doc_dir, doc_id, timestamp, doc_type)
    
    print(f"📊 Full observability saved to: {doc_dir}")
    return doc_dir


def save_discovered_fields(state, doc_dir, doc_id, timestamp):
    """Save all discovered fields to dedicated file."""
    all_fields = []
    field_stats = {
        "total_chunks_processed": len(state.chunks or []),
        "total_discovery_results": len(state.progressive_results or []),
        "unique_fields_discovered": 0,
        "field_categories": {},
        "field_types": {}
    }
    
    if state.progressive_results:
        for i, pr in enumerate(state.progressive_results):
            chunk_fields = []
            for field in pr.discovered_fields:
                field_data = {
                    "field_name": field.field_name,
                    "field_type": field.field_type,
                    "description": field.description,
                    "example_text": field.example_text,
                    "category": field.category,
                    "subcategory": field.subcategory,
                    "discovered_in_chunk": i + 1,
                    "chunk_coverage": pr.chunk_coverage
                }
                chunk_fields.append(field_data)
                all_fields.append(field_data)
                
                # Update stats
                field_stats["field_categories"][field.category] = field_stats["field_categories"].get(field.category, 0) + 1
                field_stats["field_types"][field.field_type] = field_stats["field_types"].get(field.field_type, 0) + 1
    
    # Calculate unique fields
    unique_field_names = set(f["field_name"] for f in all_fields)
    field_stats["unique_fields_discovered"] = len(unique_field_names)
    field_stats["unique_field_list"] = list(unique_field_names)
    
    discovered_fields_data = {
        "document_id": doc_id,
        "timestamp": timestamp,
        "statistics": field_stats,
        "all_discovered_fields": all_fields
    }
    
    filepath = doc_dir / f"discovered_fields_{timestamp}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(discovered_fields_data, f, indent=2, ensure_ascii=False)
    print(f"  📋 Discovered fields: {filepath.name}")


def save_extractions_file(state, doc_dir, doc_id, timestamp):
    """Save all extractions to dedicated file."""
    extractions_data = {
        "document_id": doc_id,
        "timestamp": timestamp,
        "extraction_summary": {
            "total_extractions": len(state.extractions or []),
            "extraction_methods": [],
            "fallback_used": False,
            "extraction_quality": "unknown"
        },
        "all_extractions": state.extractions or []
    }
    
    # Add intermediate results analysis if available
    if hasattr(state, 'intermediate_results') and state.intermediate_results:
        ir = state.intermediate_results
        extractions_data["extraction_summary"].update({
            "extraction_methods": ir.get("extraction_summary", {}).get("successful_methods", []),
            "fallback_used": ir.get("fallback_analysis", {}).get("fallback_used", False),
            "extraction_quality": "high" if not ir.get("fallback_analysis", {}).get("fallback_used") else "medium",
            "config_quality_score": ir.get("config_analysis", {}).get("quality_score", 0),
            "entity_categories": ir.get("extracted_entities", {}).get("categories", {}),
            "quality_metrics": ir.get("extracted_entities", {}).get("quality_metrics", {})
        })
        
        # Add detailed analysis
        extractions_data["detailed_analysis"] = {
            "entity_analysis": ir.get("extracted_entities", {}),
            "fallback_analysis": ir.get("fallback_analysis", {}),
            "recommendations": ir.get("fallback_analysis", {}).get("recommendations", [])
        }
    
    filepath = doc_dir / f"extractions_{timestamp}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(extractions_data, f, indent=2, ensure_ascii=False)
    print(f"  🎯 Extractions: {filepath.name}")


def save_timing_metrics(state, doc_dir, doc_id, timestamp):
    """Save detailed timing metrics to dedicated file."""
    timing_data = {
        "document_id": doc_id,
        "timestamp": timestamp,
        "execution_timeline": [],
        "performance_summary": {
            "total_pipeline_time": 0,
            "slowest_task": "",
            "fastest_task": "",
            "average_task_time": 0
        }
    }
    
    if state.task_execution_log:
        # Process execution log to calculate timings
        task_timings = {}
        current_task = None
        
        for log_entry in state.task_execution_log:
            task_name = log_entry["task_name"]
            status = log_entry["status"]
            ts = log_entry["timestamp"]
            
            if status == "started":
                current_task = task_name
                task_timings[task_name] = {"start": ts, "end": None, "duration": 0}
            elif status == "completed" and current_task == task_name:
                if task_name in task_timings:
                    task_timings[task_name]["end"] = ts
                    task_timings[task_name]["duration"] = ts - task_timings[task_name]["start"]
            
            timing_data["execution_timeline"].append({
                "task": task_name,
                "status": status,
                "timestamp": ts,
                "datetime": datetime.fromtimestamp(ts).isoformat()
            })
        
        # Calculate performance summary
        durations = [t["duration"] for t in task_timings.values() if t["duration"] > 0]
        if durations:
            timing_data["performance_summary"] = {
                "total_pipeline_time": sum(durations),
                "slowest_task": max(task_timings.items(), key=lambda x: x[1]["duration"])[0],
                "fastest_task": min(task_timings.items(), key=lambda x: x[1]["duration"])[0],
                "average_task_time": sum(durations) / len(durations),
                "task_durations": {name: data["duration"] for name, data in task_timings.items()}
            }
    
    filepath = doc_dir / f"timing_metrics_{timestamp}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(timing_data, f, indent=2, ensure_ascii=False)
    print(f"  ⏱️  Timing metrics: {filepath.name}")


def save_intermediate_results_file(state, doc_dir, doc_id, timestamp):
    """Save intermediate results to dedicated file."""
    if hasattr(state, 'intermediate_results') and state.intermediate_results:
        ir_data = {
            "document_id": doc_id,
            "timestamp": timestamp,
            "intermediate_results": state.intermediate_results
        }
        
        filepath = doc_dir / f"intermediate_results_{timestamp}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(ir_data, f, indent=2, ensure_ascii=False)
        print(f"  🔍 Intermediate results: {filepath.name}")


def save_execution_summary(state, doc_dir, doc_id, timestamp, doc_type):
    """Save executive summary with key metrics."""
    summary_data = {
        "document_info": {
            "document_id": doc_id,
            "document_type": doc_type,
            "classification": state.classification,
            "classification_confidence": state.classification_confidence,
            "user_id": state.user_id
        },
        "processing_results": {
            "status": state.status,
            "error": state.error,
            "chunks_processed": len(state.chunks or []),
            "fields_discovered": len(state.progressive_results or []),
            "extractions_count": len(state.extractions or [])
        },
        "key_metrics": {},
        "recommendations": []
    }
    
    # Add intermediate results summary
    if hasattr(state, 'intermediate_results') and state.intermediate_results:
        ir = state.intermediate_results
        summary_data["key_metrics"] = {
            "fallback_used": ir.get("fallback_analysis", {}).get("fallback_used", False),
            "config_quality_score": ir.get("config_analysis", {}).get("quality_score", 0),
            "extraction_completeness": ir.get("extracted_entities", {}).get("quality_metrics", {}).get("completeness_rate", 0),
            "entity_categories": list(ir.get("extracted_entities", {}).get("categories", {}).keys())
        }
        summary_data["recommendations"] = ir.get("fallback_analysis", {}).get("recommendations", [])
    
    filepath = doc_dir / f"execution_summary_{timestamp}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"  📈 Executive summary: {filepath.name}")


def save_intermediate_results(state, step_name, results_dir):
    """Legacy function for backward compatibility."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{step_name}_{timestamp}.json"
    filepath = results_dir / filename
    
    # Basic data for legacy compatibility
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
            
            # Save comprehensive observability files
            doc_dir = save_comprehensive_observability(result, doc_type, results_dir)
            
            # Print summary
            print(f"✅ Status: {result.status}")
            print(f"🏷️  Classification: {result.classification} ({result.classification_confidence:.2f})")
            print(f"📊 Chunks: {len(result.chunks or [])}")
            print(f"🔍 Discovery Results: {len(result.progressive_results or [])}")
            print(f"📋 Extractions: {len(result.extractions or [])}")
            
            # Show intermediate results summary if available
            if hasattr(result, 'intermediate_results') and result.intermediate_results:
                ir = result.intermediate_results
                print(f"🔧 Intermediate Results:")
                print(f"   • Fallback Used: {ir.get('fallback_analysis', {}).get('fallback_used', 'Unknown')}")
                print(f"   • Config Quality: {ir.get('config_analysis', {}).get('quality_score', 'Unknown')}/100")
                print(f"   • Entity Categories: {list(ir.get('extracted_entities', {}).get('categories', {}).keys())}")
                
                if ir.get('fallback_analysis', {}).get('recommendations'):
                    print(f"   • Recommendations: {len(ir['fallback_analysis']['recommendations'])} items")
            
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