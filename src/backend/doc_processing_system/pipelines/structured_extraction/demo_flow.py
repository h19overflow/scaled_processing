"""
Demo script to test the structured extraction flow with dummy data.
"""

from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import PipelineState
from src.backend.doc_processing_system.pipelines.structured_extraction.flows.prefect_flow import structured_extraction_flow

DUMMY_INVOICE_TEXT = """
ALAMAT POS
TENAGA NASIONAL BERHAD
NO. 15, JALAN SULTAN ISMAIL
50250 KUALA LUMPUR

TARIKH BIL: 15.01.2025
TEMPOH BIL: 15.12.2024 - 14.01.2025 (30 Hari)
NO. INVOIS: 000445566778
NO. AKAUN: 401234567890

Ringkasan Bil Anda:
BAKI TERDAHULU RM125.50
CAJ SEMASA RM450.00
JUMLAH BIL ANDA RM575.50

Sila bayar sebelum: 31 January 2025
Biller Code: 1234
Ref-1: 401234567890
"""

DUMMY_RESUME_TEXT = """
JOHN SMITH
Software Developer

Contact Information:
Email: john.smith@email.com
Phone: (555) 123-4567
Address: 789 Tech Drive, Silicon Valley, CA 94000

EXPERIENCE

Senior Software Developer | TechCorp Inc. | 2020-2024
- Led development of microservices architecture serving 1M+ users
- Implemented CI/CD pipelines reducing deployment time by 60%
- Mentored 5 junior developers on best practices

Software Developer | StartupXYZ | 2018-2020
- Built REST APIs using Python/Django and PostgreSQL
- Developed responsive web applications with React
- Collaborated with cross-functional teams in Agile environment

EDUCATION

Bachelor of Science in Computer Science
University of Technology | 2014-2018
GPA: 3.8/4.0

SKILLS
- Programming: Python, JavaScript, Java, SQL
- Frameworks: Django, React, Node.js
- Tools: Docker, Kubernetes, AWS, Git
- Databases: PostgreSQL, MongoDB, Redis
"""

def test_flow_with_invoice():
    """Test the flow with invoice dummy data."""
    print("\n🧾 Testing with Invoice Document")
    print("=" * 50)
    
    # Create initial state for invoice
    initial_state = PipelineState(
        document_text=DUMMY_INVOICE_TEXT,
        document_id="test_invoice_001"
    )
    
    print(f"📄 Input Document ID: {initial_state.document_id}")
    print(f"📝 Document Preview: {initial_state.document_text[:100]}...")
    
    # Run the flow
    try:
        result = structured_extraction_flow(initial_state)
        
        print(f"\n✅ Flow completed with status: {result.status}")
        print(f"🏷️  Classification: {result.classification}")
        print(f"🎯 Confidence: {result.classification_confidence}")
        print(f"📦 Chunks created: {len(result.chunks) if result.chunks else 0}")
        
        if hasattr(result, 'results') and result.results:
            print(f"🔍 Extraction Results: {result.results}")
        
        return result
        
    except Exception as e:
        print(f"❌ Flow failed with error: {e}")
        return None

def test_flow_with_resume():
    """Test the flow with resume dummy data.""" 
    print("\n👤 Testing with Resume Document")
    print("=" * 50)
    
    # Create initial state for resume
    initial_state = PipelineState(
        document_text=DUMMY_RESUME_TEXT,
        document_id="test_resume_001"
    )
    
    print(f"📄 Input Document ID: {initial_state.document_id}")
    print(f"📝 Document Preview: {initial_state.document_text[:100]}...")
    
    # Run the flow
    try:
        result = structured_extraction_flow(initial_state)
        
        print(f"\n✅ Flow completed with status: {result.status}")
        print(f"🏷️  Classification: {result.classification}")
        print(f"🎯 Confidence: {result.classification_confidence}")
        print(f"📦 Chunks created: {len(result.chunks) if result.chunks else 0}")
        
        if hasattr(result, 'results') and result.results:
            print(f"🔍 Extraction Results: {result.results}")
        
        return result
        
    except Exception as e:
        print(f"❌ Flow failed with error: {e}")
        return None

def main():
    """Run demo tests."""
    print("🚀 Structured Extraction Flow Demo")
    print("=" * 60)
    
    # Test with different document types
    invoice_result = test_flow_with_invoice()

    print("\n📊 Demo Summary")
    print("=" * 30)
    print(f"Invoice processing: {'✅ Success' if invoice_result and invoice_result.status == 'completed' else '❌ Failed'}")

if __name__ == "__main__":
    main()