"""
Demo script to test the structured extraction flow with dummy data.
"""

from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import PipelineState
from src.backend.doc_processing_system.pipelines.structured_extraction.core.prefect_tasks import structured_extraction_flow

DUMMY_INVOICE_TEXT = """
INVOICE

Invoice Number: INV-2024-001
Date: March 15, 2024

Bill To:
John Doe Company
123 Main Street
Anytown, ST 12345

From:
ABC Services Inc.
456 Business Ave
Corporate City, CC 67890

Description                    Quantity    Unit Price    Total
Web Development Services            40        $125.00    $5,000.00
Design Consulting                   10        $150.00    $1,500.00
Project Management                   8        $100.00      $800.00

Subtotal: $7,300.00
Tax (8.5%): $620.50
Total Amount Due: $7,920.50

Payment Terms: Net 30 days
Due Date: April 14, 2024
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