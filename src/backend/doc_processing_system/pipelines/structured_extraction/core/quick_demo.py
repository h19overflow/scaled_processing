#!/usr/bin/env python3
"""
Quick demo script to showcase the refactored Prefect pipeline.

Usage:
    python -m src.backend.doc_processing_system.pipelines.structured_extraction.core.quick_demo

Results saved to: demo_results/
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from .prefect_tasks import structured_extraction_flow
from ..config.settings import Settings


async def run_quick_demo():
    """Run a single document through the pipeline to showcase features."""
    print("🚀 Quick Prefect Pipeline Demo")
    print("=" * 40)
    
    # Create results directory
    results_dir = Path("demo_results")
    results_dir.mkdir(exist_ok=True)
    
    # Simple test document
    test_document = """
    EMPLOYMENT CONTRACT
    
    Employee: Alice Johnson  
    Position: Software Engineer
    Department: Engineering
    Start Date: January 15, 2024
    Salary: $75,000 per year
    
    This contract outlines the employment terms between
    TechCorp Inc. and Alice Johnson for the Software Engineer
    position starting January 15, 2024.
    
    Responsibilities:
    - Develop software applications
    - Code reviews and testing
    - Team collaboration
    
    Benefits:
    - Health insurance
    - 401k matching
    - Paid time off
    """
    
    print("📄 Processing employment contract...")
    
    try:
        # Create settings and run pipeline
        settings = Settings()
        
        result = await structured_extraction_flow(
            document_text=test_document,
            document_id=f"quick_demo_{datetime.now().strftime('%H%M%S')}",
            settings=settings,
            user_id="demo_user"
        )
        
        # Display results
        print(f"\n✅ Pipeline Status: {result.status}")
        print(f"🏷️  Classification: {result.classification} (confidence: {result.classification_confidence:.2f})")
        print(f"📊 Processing Stats:")
        print(f"   • Chunks created: {len(result.chunks or [])}")
        print(f"   • Discovery results: {len(result.progressive_results or [])}")
        print(f"   • Extractions: {len(result.extractions or [])}")
        
        # Show task execution timeline
        print(f"\n⏱️  Task Execution Timeline:")
        for i in range(0, len(result.task_execution_log), 2):
            if i + 1 < len(result.task_execution_log):
                start_log = result.task_execution_log[i]
                end_log = result.task_execution_log[i + 1]
                duration = end_log["timestamp"] - start_log["timestamp"]
                print(f"   ✅ {start_log['task_name']}: {duration:.2f}s")
        
        # Save results
        timestamp = datetime.now().strftime("%H%M%S")
        results_file = results_dir / f"quick_demo_results_{timestamp}.json"
        
        demo_results = {
            "demo_type": "quick_demo",
            "timestamp": datetime.now().isoformat(),
            "pipeline_status": result.status,
            "classification": result.classification,
            "classification_confidence": result.classification_confidence,
            "processing_stats": {
                "chunks_count": len(result.chunks or []),
                "discovery_results_count": len(result.progressive_results or []),
                "extractions_count": len(result.extractions or [])
            },
            "task_execution_log": result.task_execution_log,
            "sample_extractions": result.extractions[:3] if result.extractions else [],
            "refactoring_features_demonstrated": [
                "Generic task wrapper reducing boilerplate",
                "Centralized state management",
                "Prefect native logging",
                "Async standardization",
                "Enhanced error handling",
                "Task execution monitoring"
            ]
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(demo_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Results saved to: {results_file}")
        
        # Show sample extractions
        if result.extractions:
            print(f"\n📋 Sample Extractions:")
            for i, extraction in enumerate(result.extractions[:3]):
                print(f"   {i+1}. {extraction}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"💡 View detailed logs at: http://localhost:4200 (if Prefect server running)")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False


def main():
    """Main entry point for quick demo."""
    try:
        success = asyncio.run(run_quick_demo())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())