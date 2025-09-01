"""
Test script for 2-stage chunker system

Processes the specified document and measures performance.
Outputs comprehensive JSON report with timing and quality metrics.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from components.two_stage_chunker import TwoStageChunker


async def test_two_stage_chunker():
    """Test the 2-stage chunker with the specified document."""
    
    # Document path
    doc_path = Path(r"C:\Users\User\Projects\scaled_processing\data\documents\processed\doc_20250901_082440_0ec59f16\doc_20250901_082440_0ec59f16_processed.md")
    
    print("🔄 Testing 2-Stage Chunker System")
    print(f"📄 Document: {doc_path.name}")
    
    # Check if document exists
    if not doc_path.exists():
        print(f"❌ Document not found: {doc_path}")
        return
    
    # Read document content
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📊 Document size: {len(content):,} characters")
        
    except Exception as e:
        print(f"❌ Error reading document: {e}")
        return

    # Initialize 2-stage chunker with 15 concurrent agents
    chunker = TwoStageChunker(
        chunk_size=700,
        semantic_threshold=0.75,
        boundary_context=200,
        concurrent_agents=15,
        output_directory=str(Path(__file__).parent)
    )
    
    # Estimate processing time
    estimated_time = chunker.estimate_processing_time(len(content))
    print(f"⏱️ Estimated processing time: {estimated_time:.1f} seconds")
    
    # Process document
    try:
        result = await chunker.process_document(
            text=content,
            document_id="doc_20250901_082440_0ec59f16"
        )
        
        # Print results
        print("\n✅ Processing Complete!")
        print(f"📊 Final chunks: {result['chunk_count']}")
        print(f"⏱️ Total time: {result['total_processing_time']:.3f} seconds")
        print(f"📁 Report saved: {result['report_saved_path']}")
        print(f"📄 Chunks saved: {result['chunks_saved_path']}")
        
        # Print key metrics from report
        report = result['processing_report']
        print(f"\n📈 Key Metrics:")
        print(f"  • Initial chunks: {report['final_results']['initial_chunk_count']}")
        print(f"  • Final chunks: {report['final_results']['final_chunk_count']}")
        print(f"  • Chunks merged: {report['final_results']['chunks_merged']}")
        print(f"  • Merge rate: {report['final_results']['merge_rate']:.1f}%")
        print(f"  • Avg chunk size: {report['final_results']['final_chunk_statistics']['avg_length']:.0f} chars")
        print(f"  • Processing speed: {report['performance_metrics']['chars_per_second']:.0f} chars/sec")
        print(f"  • Boundary confidence: {report['quality_metrics']['avg_boundary_confidence']:.2f}")
        
        # Print first few chunks for inspection
        print(f"\n🔍 Sample Chunks (first 3):")
        for i, chunk in enumerate(result['final_chunks'][:3]):
            print(f"\n--- Chunk {i+1} ({len(chunk)} chars) ---")
            print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        
        return result
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run the test."""
    print("🚀 Starting 2-Stage Chunker Test")
    return asyncio.run(test_two_stage_chunker())


if __name__ == "__main__":
    main()