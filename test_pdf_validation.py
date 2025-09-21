"""
Test script for PDF validation and repair functionality.
"""
import asyncio
from pathlib import Path
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core.pdf_validation_tasks import (
    check_external_dependencies,
    validate_pdf_task,
    repair_pdf_task,
    clean_with_pymupdf_task,
)

async def test_pdf_validation():
    """Test PDF validation tasks."""
    print("🔧 Testing PDF Validation and Repair System")
    print("=" * 50)

    # Check dependencies
    print("\n1. Checking External Dependencies:")
    deps = check_external_dependencies()
    for tool, available in deps.items():
        status = "✅ Available" if available else "❌ Not Available"
        print(f"   {tool}: {status}")

    # Test with existing PDF files in the project
    test_pdfs = [
        "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\GSPP_5407_202507_Billing.pdf",
        "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\GSPP_5407_202508_Billing.pdf",
    ]

    for pdf_path in test_pdfs:
        if Path(pdf_path).exists():
            print(f"\n2. Testing PDF Validation for: {Path(pdf_path).name}")
            print("-" * 30)

            # Test validation
            validation_result = validate_pdf_task(pdf_path)
            print(f"   Validation Status: {validation_result['status']}")
            print(f"   Needs Repair: {validation_result['needs_repair']}")
            if validation_result['validation_errors']:
                print(f"   Errors: {validation_result['validation_errors']}")

            # Test repair if needed or forced
            if validation_result['needs_repair'] or True:  # Force repair for testing
                print(f"\n   Testing PDF Repair...")
                repair_result = repair_pdf_task(pdf_path)
                print(f"   Repair Status: {repair_result['status']}")
                print(f"   Repair Method: {repair_result['repair_method']}")
                print(f"   Repaired Path: {repair_result['repaired_path']}")

                # Test cleaning if repair was successful
                if repair_result['status'] == 'repaired':
                    print(f"\n   Testing PDF Cleaning...")
                    clean_result = clean_with_pymupdf_task(repair_result['repaired_path'])
                    print(f"   Clean Status: {clean_result['status']}")
                    if clean_result['status'] == 'cleaned':
                        print(f"   Clean Path: {clean_result['clean_path']}")
                        if 'original_size' in clean_result:
                            print(f"   Size Change: {clean_result['original_size']} → {clean_result['clean_size']} bytes")

            print("\n" + "=" * 50)
            break  # Test only the first available PDF

    else:
        print("\n❌ No test PDF files found. Place a PDF in data/pdfs/ to test.")

if __name__ == "__main__":
    asyncio.run(test_pdf_validation())