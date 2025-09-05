"""
Main demo orchestrator for langextract structured extraction.
Simple demo that processes Hamza's CV and extracts structured data.
"""

import asyncio
import os
from pathlib import Path

from .extraction_workflow import ExtractionWorkflow
from .results_handler import ResultsHandler

class LangExtractDemo:
    """Main demo class for structured extraction."""
    
    def __init__(self):
        """Initialize demo components."""
        self.workflow = ExtractionWorkflow()
        self.results_handler = ResultsHandler()
    
    def load_document(self, document_path: str) -> str:
        """Load document content from file."""
        with open(document_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def run_demo(self, document_path: str, document_id: str = None) -> dict:
        """Run the complete extraction demo."""
        print(f"🚀 Starting langextract demo for: {document_path}")
        
        # Load document
        document_text = self.load_document(document_path)
        if document_id is None:
            document_id = Path(document_path).stem
        
        print(f"📄 Loaded document: {len(document_text)} characters")
        
        # Run extraction workflow
        print("🔍 Running extraction workflow...")
        results = await self.workflow.run_extraction(
            document_text=document_text,
            document_id=document_id
        )
        
        # Save results
        print("💾 Saving results...")
        json_path = self.results_handler.save_results(results)
        summary_path = self.results_handler.save_summary(results)
        
        print(f"✅ Demo complete!")
        print(f"📊 Results saved: {json_path}")
        print(f"📝 Summary saved: {summary_path}")
        
        # Print quick summary
        extractions = results.get("extractions", [])
        print(f"\n📈 Extracted {len(extractions)} items:")
        for extraction in extractions[:3]:  # Show first 3
            print(f"  - {extraction['extraction_class']}: {extraction['extraction_text'][:50]}...")
        
        return results

async def main():
    """Run demo with Hamza's CV."""
    # Path to Hamza's processed CV
    cv_path = "data/documents/processed/Hamza_CV_Updated/Hamza_CV_Updated_processed.md"
    
    if not os.path.exists(cv_path):
        print(f"❌ Document not found: {cv_path}")
        return
    
    # Run demo
    demo = LangExtractDemo()
    await demo.run_demo(cv_path, "Hamza_CV_Updated")

if __name__ == "__main__":
    asyncio.run(main())