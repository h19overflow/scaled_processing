"""
Test the integrated document processing flow with PDF validation.
"""
import asyncio
import os
from pathlib import Path

# Set environment to use local mode for Prefect
os.environ["PREFECT_API_URL"] = ""
os.environ["PREFECT_PROFILES_PATH"] = ""

async def test_document_processing_flow():
    """Test the complete document processing flow with PDF validation."""
    try:
        from src.backend.doc_processing_system.pipelines.document_processing.flows.document_processing_flow import (
            process_document_with_flow
        )

        print("🚀 Testing Integrated Document Processing Flow with PDF Validation")
        print("=" * 70)

        # Test with a real PDF file
        test_pdf = "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\GSPP_5407_202507_Billing.pdf"

        if not Path(test_pdf).exists():
            print(f"❌ Test PDF not found: {test_pdf}")
            return

        print(f"📄 Testing with PDF: {Path(test_pdf).name}")
        print(f"📏 File size: {Path(test_pdf).stat().st_size:,} bytes")

        # Test with PDF validation enabled
        print("\n🔍 Testing with PDF validation ENABLED:")
        print("-" * 40)

        result = await process_document_with_flow(
            raw_file_path=test_pdf,
            user_id="test_user",
            enable_chunking=False,  # Disable chunking for faster testing
            enable_pdf_validation=True,
            force_pdf_repair=False
        )

        print(f"Status: {result.get('status')}")
        print(f"Document ID: {result.get('document_id')}")

        if 'processing_steps' in result:
            print("\nProcessing Steps:")
            for step, status in result['processing_steps'].items():
                print(f"  {step}: {status}")

        # Test with forced PDF repair
        print("\n🔧 Testing with FORCED PDF repair:")
        print("-" * 40)

        result_forced = await process_document_with_flow(
            raw_file_path=test_pdf,
            user_id="test_user_forced",
            enable_chunking=False,
            enable_pdf_validation=True,
            force_pdf_repair=True  # Force repair even if validation passes
        )

        print(f"Status: {result_forced.get('status')}")
        print(f"Document ID: {result_forced.get('document_id')}")

        if 'processing_steps' in result_forced:
            print("\nProcessing Steps:")
            for step, status in result_forced['processing_steps'].items():
                print(f"  {step}: {status}")

        # Test with PDF validation disabled
        print("\n⏭️ Testing with PDF validation DISABLED:")
        print("-" * 40)

        result_disabled = await process_document_with_flow(
            raw_file_path=test_pdf,
            user_id="test_user_disabled",
            enable_chunking=False,
            enable_pdf_validation=False
        )

        print(f"Status: {result_disabled.get('status')}")
        print(f"Document ID: {result_disabled.get('document_id')}")

        if 'processing_steps' in result_disabled:
            print("\nProcessing Steps:")
            for step, status in result_disabled['processing_steps'].items():
                print(f"  {step}: {status}")

        print("\n✅ All tests completed successfully!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_document_processing_flow())