"""
Multi-agent demo orchestrator for comprehensive structured extraction.
Tests the full chunking + sequential discovery + consolidation pipeline.
"""

import asyncio
import os
from pathlib import Path

from .multi_agent_workflow import MultiAgentWorkflow
from .results_handler import ResultsHandler

class MultiAgentDemo:
    """Main demo class for multi-agent structured extraction."""
    
    def __init__(self, max_tokens: int = 1500, max_fields: int = 8):
        """Initialize multi-agent demo components."""
        self.workflow = MultiAgentWorkflow(
            max_tokens=max_tokens, 
            max_fields=max_fields
        )
        self.results_handler = ResultsHandler()
    
    def load_document(self, document_path: str) -> str:
        """Load document content from file."""
        with open(document_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def run_demo(self, document_path: str, document_id: str = None) -> dict:
        """Run the complete multi-agent extraction demo."""
        print("=" * 60)
        print(f"🚀 Multi-Agent Structured Extraction Demo")
        print(f"📄 Document: {document_path}")
        print("=" * 60)
        
        # Load document
        document_text = self.load_document(document_path)
        if document_id is None:
            document_id = Path(document_path).stem
        
        print(f"📊 Document loaded: {len(document_text):,} characters")
        
        # Run multi-agent extraction workflow
        results = await self.workflow.run_extraction(
            document_text=document_text,
            document_id=document_id
        )
        
        # Save results
        print("\n💾 Saving results...")
        json_path = self.results_handler.save_results(results)
        summary_path = self.results_handler.save_summary(results)
        
        # Display results summary
        print("\n" + "=" * 60)
        print("📈 EXTRACTION RESULTS SUMMARY")
        print("=" * 60)
        
        if results.get("error"):
            print(f"❌ Error: {results['error']}")
        else:
            # Chunking summary
            chunks = results.get("chunks", [])
            print(f"📄 Document chunks: {len(chunks)}")
            
            # Schema discovery summary
            if results.get("final_schema"):
                schema = results["final_schema"]
                print(f"📋 Document type: {schema.document_type}")
                print(f"🔍 Final extraction classes: {len(schema.extraction_classes)}")
                
                for i, field in enumerate(schema.extraction_classes, 1):
                    print(f"   {i}. {field.field_name}: {field.description}")
            
            # Extraction results
            extractions = results.get("extractions", [])
            print(f"✅ Total extractions: {len(extractions)}")
            
            # Show sample extractions
            if extractions:
                print(f"\n📊 Sample extractions:")
                for extraction in extractions[:5]:
                    text_preview = extraction['extraction_text'][:50]
                    if len(extraction['extraction_text']) > 50:
                        text_preview += "..."
                    print(f"   • {extraction['extraction_class']}: {text_preview}")
                
                if len(extractions) > 5:
                    print(f"   ... and {len(extractions) - 5} more")
        
        # File outputs
        print(f"\n📁 Files saved:")
        print(f"   📊 JSON: {json_path}")
        print(f"   📝 Summary: {summary_path}")
        
        return results

async def main():
    """Run multi-agent demo with Hamza's CV."""
    # Path to Hamza's processed CV
    cv_path = "data/documents/processed/Hamza_CV_Updated/Hamza_CV_Updated_processed.md"
    
    if not os.path.exists(cv_path):
        print(f"❌ Document not found: {cv_path}")
        return
    
    # Run multi-agent demo
    demo = MultiAgentDemo(
        max_tokens=1500,  # Chunk size
        max_fields=8      # Final schema fields
    )
    
    await demo.run_demo(cv_path, "Hamza_CV_MultiAgent")

if __name__ == "__main__":
    asyncio.run(main())