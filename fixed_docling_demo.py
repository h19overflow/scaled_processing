"""
Simple Docling Demo - Convert document to markdown with AI image descriptions
"""

import sys
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src" / "backend"
sys.path.insert(0, str(src_path))

from doc_processing_system.pipelines.document_processing.docling_processor import DoclingProcessor


def run_simple_demo():
    """Convert document to markdown and save it."""
    
    print("=" * 50)
    print("🔧 Simple Docling to Markdown Demo")
    print("=" * 50)
    
    # Path to the PDF
    pdf_path = "src/backend/doc_processing_system/pipelines/document_processing/gemini-for-google-workspace-prompting-guide-101.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    try:
        # Convert document to markdown using DoclingProcessor
        print("🚀 Converting document to markdown...")
        processor = DoclingProcessor()
        markdown_content = processor.extract_markdown(pdf_path)
        
        print(f"✅ Converted: {len(markdown_content):,} characters")
        
        # Save markdown file
        output_file = "output_markdown.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"💾 Markdown saved to: {output_file}")
        
        # Show first few lines
        print("\n📝 First 500 characters:")
        print("-" * 50)
        print(markdown_content[:500])
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_simple_demo()