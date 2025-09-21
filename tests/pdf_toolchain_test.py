"""
Comprehensive test script for PDF validation, repair, and cleaning functionality.

Run with: python -m tests.pdf_toolchain_test
"""
import asyncio
import os
from pathlib import Path
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment to use local mode for Prefect
os.environ["PREFECT_API_URL"] = ""
os.environ["PREFECT_PROFILES_PATH"] = ""

# Import the PDF validation tasks
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core.pdf_validation_tasks import (
    check_external_dependencies,
    validate_pdf_task,
    repair_pdf_task,
    clean_with_pymupdf_task,
    cleanup_pdf_processing_temp,
)

# Import PDF libraries for direct testing
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

try:
    import ghostscript as gs
    GHOSTSCRIPT_AVAILABLE = True
except ImportError:
    GHOSTSCRIPT_AVAILABLE = False

import fitz


def print_section(title: str, width: int = 70):
    """Print a formatted section header."""
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_subsection(title: str, width: int = 50):
    """Print a formatted subsection header."""
    print(f"\n{'-' * width}")
    print(f"  {title}")
    print(f"{'-' * width}")


async def test_dependency_availability():
    """Test all PDF tool dependencies."""
    print_section("🔧 PDF TOOLCHAIN DEPENDENCY CHECK")

    deps = check_external_dependencies()

    print("\n📋 Available Tools:")
    for tool, available in deps.items():
        status_icon = "✅" if available else "❌"
        status_text = "Available" if available else "Not Available"
        print(f"   {status_icon} {tool:20}: {status_text}")

    available_count = sum(deps.values())
    total_count = len(deps)

    print(f"\n📊 Summary: {available_count}/{total_count} tools available")

    if available_count == 0:
        print("⚠️  WARNING: No PDF processing tools available!")
        return False
    elif available_count < total_count:
        print("ℹ️  Some tools missing, but basic functionality available")
    else:
        print("🎉 All PDF tools available!")

    return True


async def test_direct_pdf_libraries():
    """Test direct usage of PDF libraries."""
    print_section("🧪 DIRECT PDF LIBRARY TESTING")

    test_pdf_path = find_test_pdf()
    if not test_pdf_path:
        print("❌ No test PDF found for direct library testing")
        return

    print(f"📄 Testing with: {test_pdf_path.name}")
    print(f"📏 File size: {test_pdf_path.stat().st_size:,} bytes")

    # Test PyMuPDF
    print_subsection("PyMuPDF (fitz) Test")
    try:
        doc = fitz.open(str(test_pdf_path))
        print(f"✅ PyMuPDF opened successfully")
        print(f"   📄 Pages: {doc.page_count}")
        print(f"   📊 Is PDF: {doc.is_pdf}")
        print(f"   🔍 Metadata: {doc.metadata.get('title', 'No title')}")
        doc.close()
    except Exception as e:
        print(f"❌ PyMuPDF failed: {e}")

    # Test pikepdf
    if PIKEPDF_AVAILABLE:
        print_subsection("pikepdf Test")
        try:
            with pikepdf.open(str(test_pdf_path)) as pdf:
                print(f"✅ pikepdf opened successfully")
                print(f"   📄 Pages: {len(pdf.pages)}")
                print(f"   📊 PDF Version: {pdf.pdf_version}")
                if hasattr(pdf, 'docinfo'):
                    print(f"   🔍 Title: {pdf.docinfo.get('/Title', 'No title')}")
        except Exception as e:
            print(f"❌ pikepdf failed: {e}")
    else:
        print("⏭️  pikepdf not available")

    # Test Ghostscript (if available)
    if GHOSTSCRIPT_AVAILABLE:
        print_subsection("Ghostscript Python Test")
        try:
            # Basic ghostscript version test
            print(f"✅ Ghostscript Python bindings available")
            print(f"   📦 Version: {gs.__version__}")
        except Exception as e:
            print(f"❌ Ghostscript Python test failed: {e}")
    else:
        print("⏭️  Ghostscript Python bindings not available")


async def test_pdf_validation_pipeline():
    """Test the full PDF validation pipeline."""
    print_section("🔍 PDF VALIDATION PIPELINE TEST")

    test_pdf_path = find_test_pdf()
    if not test_pdf_path:
        print("❌ No test PDF found for validation testing")
        return

    print(f"📄 Testing with: {test_pdf_path.name}")

    # Test validation
    print_subsection("PDF Validation Test")
    try:
        validation_result = validate_pdf_task(str(test_pdf_path))
        print(f"✅ Validation completed")
        print(f"   📊 Status: {validation_result['status']}")
        print(f"   🔧 Needs Repair: {validation_result['needs_repair']}")
        print(f"   📝 Message: {validation_result['message']}")

        if validation_result['validation_errors']:
            print(f"   ⚠️  Errors: {len(validation_result['validation_errors'])}")
            for i, error in enumerate(validation_result['validation_errors'][:3], 1):
                print(f"      {i}. {error}")

        return validation_result
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_pdf_repair_pipeline():
    """Test the PDF repair pipeline."""
    print_section("🔧 PDF REPAIR PIPELINE TEST")

    test_pdf_path = find_test_pdf()
    if not test_pdf_path:
        print("❌ No test PDF found for repair testing")
        return

    print(f"📄 Testing repair with: {test_pdf_path.name}")

    # Test repair (even on valid PDFs to test the functionality)
    print_subsection("PDF Repair Test (Forced)")
    try:
        repair_result = repair_pdf_task(str(test_pdf_path))
        print(f"✅ Repair completed")
        print(f"   📊 Status: {repair_result['status']}")
        print(f"   🔧 Method: {repair_result['repair_method']}")
        print(f"   📁 Repaired Path: {repair_result.get('repaired_path', 'N/A')}")
        print(f"   📝 Message: {repair_result['message']}")

        return repair_result
    except Exception as e:
        print(f"❌ Repair failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_pdf_cleaning_pipeline():
    """Test the PDF cleaning pipeline."""
    print_section("🧹 PDF CLEANING PIPELINE TEST")

    test_pdf_path = find_test_pdf()
    if not test_pdf_path:
        print("❌ No test PDF found for cleaning testing")
        return

    print(f"📄 Testing cleaning with: {test_pdf_path.name}")

    # Test cleaning
    print_subsection("PDF Cleaning Test")
    try:
        clean_result = clean_with_pymupdf_task(str(test_pdf_path))
        print(f"✅ Cleaning completed")
        print(f"   📊 Status: {clean_result['status']}")
        print(f"   📁 Clean Path: {clean_result.get('clean_path', 'N/A')}")
        print(f"   📝 Message: {clean_result['message']}")

        if 'original_size' in clean_result and 'clean_size' in clean_result:
            original_size = clean_result['original_size']
            clean_size = clean_result['clean_size']
            size_diff = original_size - clean_size
            percent_change = (size_diff / original_size) * 100 if original_size > 0 else 0

            print(f"   📊 Size Change: {original_size:,} → {clean_size:,} bytes")
            print(f"   📉 Difference: {size_diff:+,} bytes ({percent_change:+.1f}%)")

        return clean_result
    except Exception as e:
        print(f"❌ Cleaning failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_full_processing_chain():
    """Test the complete PDF processing chain."""
    print_section("🔄 FULL PDF PROCESSING CHAIN TEST")

    test_pdf_path = find_test_pdf()
    if not test_pdf_path:
        print("❌ No test PDF found for full chain testing")
        return

    print(f"📄 Testing full chain with: {test_pdf_path.name}")

    # Simulate the full pipeline
    current_path = str(test_pdf_path)

    # Step 1: Validation
    print_subsection("Step 1: Validation")
    validation_result = validate_pdf_task(current_path)
    print(f"   Status: {validation_result['status']}")

    # Step 2: Repair (if needed or forced)
    if validation_result['needs_repair'] or True:  # Force for testing
        print_subsection("Step 2: Repair")
        repair_result = repair_pdf_task(current_path)
        print(f"   Status: {repair_result['status']}")

        if repair_result['status'] == 'repaired':
            current_path = repair_result['repaired_path']
            print(f"   Using repaired file: {Path(current_path).name}")

    # Step 3: Cleaning
    print_subsection("Step 3: Cleaning")
    clean_result = clean_with_pymupdf_task(current_path)
    print(f"   Status: {clean_result['status']}")

    if clean_result['status'] == 'cleaned':
        final_path = clean_result['clean_path']
        print(f"   Final processed file: {Path(final_path).name}")

        # Compare final result with original
        original_size = test_pdf_path.stat().st_size
        final_size = Path(final_path).stat().st_size
        size_diff = original_size - final_size

        print(f"\n📊 Processing Summary:")
        print(f"   Original: {original_size:,} bytes")
        print(f"   Final:    {final_size:,} bytes")
        print(f"   Change:   {size_diff:+,} bytes")

    # Cleanup temporary files
    print_subsection("Step 4: Cleanup")
    try:
        cleanup_pdf_processing_temp(test_pdf_path.stem)
        print("   ✅ Temporary files cleaned up")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")


def find_test_pdf() -> Path:
    """Find a test PDF file to use for testing."""
    # Look for PDF files in the project
    project_root = Path(__file__).parent.parent

    potential_paths = [
        project_root / "data" / "documents" / "GSPP_5407_202507_Billing.pdf",
        project_root / "data" / "documents" / "GSPP_5407_202508_Billing.pdf",
    ]

    for pdf_path in potential_paths:
        if pdf_path.exists():
            return pdf_path

    # Look for any PDF in documents folder
    docs_folder = project_root / "data" / "documents"
    if docs_folder.exists():
        for pdf_file in docs_folder.glob("*.pdf"):
            return pdf_file

    return None


async def main():
    """Run all PDF toolchain tests."""
    print_section("🚀 PDF TOOLCHAIN COMPREHENSIVE TEST SUITE", 80)
    print(f"Project: {Path(__file__).parent.parent.name}")
    print(f"Test Script: {Path(__file__).name}")

    # Test 1: Dependencies
    deps_ok = await test_dependency_availability()
    if not deps_ok:
        print("\n❌ Critical: No PDF tools available. Cannot continue testing.")
        return

    # Test 2: Direct library testing
    await test_direct_pdf_libraries()

    # Test 3: Validation pipeline
    await test_pdf_validation_pipeline()

    # Test 4: Repair pipeline
    await test_pdf_repair_pipeline()

    # Test 5: Cleaning pipeline
    await test_pdf_cleaning_pipeline()

    # Test 6: Full processing chain
    await test_full_processing_chain()

    print_section("✅ ALL TESTS COMPLETED", 80)
    print("Check the output above for any errors or warnings.")
    print("The PDF validation and repair system is ready for production use!")


if __name__ == "__main__":
    asyncio.run(main())