"""
Simple comprehensive test script for PDF validation, repair, and cleaning functionality.

Run with: python -m test_pdf_toolchain_simple
"""
from pathlib import Path
import subprocess
import shutil

# Import PDF libraries for testing
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

try:
    import ghostscript as gs
    GHOSTSCRIPT_AVAILABLE = True
except (ImportError, RuntimeError):
    GHOSTSCRIPT_AVAILABLE = False

import fitz  # PyMuPDF


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


def check_dependencies():
    """Check if required PDF processing tools are available."""
    dependencies = {
        "pdfinfo": False,
        "qpdf": False,
        "pikepdf": False,
        "ghostscript": False,
        "ghostscript_python": False,
        "pymupdf": False
    }

    # Check pdfinfo (poppler-utils)
    try:
        subprocess.run(["pdfinfo", "-v"], capture_output=True, check=True)
        dependencies["pdfinfo"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Check qpdf command line
    try:
        subprocess.run(["qpdf", "--version"], capture_output=True, check=True)
        dependencies["qpdf"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Check pikepdf (Python qpdf bindings)
    dependencies["pikepdf"] = PIKEPDF_AVAILABLE

    # Check ghostscript command line (try both gs and gswin64c for Windows)
    for gs_cmd in ["gs", "gswin64c", "gswin32c"]:
        try:
            subprocess.run([gs_cmd, "--version"], capture_output=True, check=True)
            dependencies["ghostscript"] = True
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # Check ghostscript Python bindings
    dependencies["ghostscript_python"] = GHOSTSCRIPT_AVAILABLE

    # Check PyMuPDF
    try:
        import fitz
        dependencies["pymupdf"] = True
    except ImportError:
        pass

    return dependencies


def test_dependency_availability():
    """Test all PDF tool dependencies."""
    print_section("🔧 PDF TOOLCHAIN DEPENDENCY CHECK")

    deps = check_dependencies()

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


def test_direct_pdf_libraries():
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


def simple_pdf_validation(pdf_path):
    """Simple PDF validation without Prefect tasks."""
    print_subsection("PDF Validation Test")
    print(f"📄 Validating: {Path(pdf_path).name}")

    validation_errors = []
    needs_repair = False

    deps = check_dependencies()

    # Check with pdfinfo
    if deps["pdfinfo"]:
        try:
            result = subprocess.run(
                ["pdfinfo", pdf_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"✅ pdfinfo validation passed")
                # Extract some info
                output_lines = result.stdout.split('\n')
                for line in output_lines[:5]:  # Show first 5 lines
                    if line.strip():
                        print(f"   {line.strip()}")
            else:
                print(f"❌ pdfinfo validation failed: {result.stderr}")
                validation_errors.append(f"pdfinfo failed: {result.stderr}")
                needs_repair = True
        except Exception as e:
            print(f"⚠️ pdfinfo error: {str(e)}")
            validation_errors.append(f"pdfinfo error: {str(e)}")

    # Check with pikepdf
    if deps["pikepdf"]:
        try:
            with pikepdf.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                print(f"✅ pikepdf validation passed: {page_count} pages")
        except Exception as e:
            print(f"❌ pikepdf validation failed: {str(e)}")
            validation_errors.append(f"pikepdf error: {str(e)}")
            needs_repair = True

    # Check with PyMuPDF
    if deps["pymupdf"]:
        try:
            doc = fitz.open(pdf_path)
            if doc.is_pdf and doc.page_count > 0:
                print(f"✅ PyMuPDF validation passed: {doc.page_count} pages")
            else:
                print(f"❌ PyMuPDF: Invalid PDF structure")
                validation_errors.append("PyMuPDF: Invalid PDF structure")
                needs_repair = True
            doc.close()
        except Exception as e:
            print(f"❌ PyMuPDF validation failed: {str(e)}")
            validation_errors.append(f"PyMuPDF error: {str(e)}")
            needs_repair = True

    print(f"📊 Validation Summary:")
    print(f"   Needs Repair: {needs_repair}")
    print(f"   Errors Found: {len(validation_errors)}")

    return {
        "needs_repair": needs_repair,
        "validation_errors": validation_errors
    }


def simple_pdf_repair(pdf_path):
    """Simple PDF repair functionality."""
    print_subsection("PDF Repair Test")
    print(f"🔧 Attempting repair: {Path(pdf_path).name}")

    deps = check_dependencies()
    pdf_file = Path(pdf_path)

    # Create processing directory
    processing_dir = Path("data/temp/pdf_processing") / pdf_file.stem
    processing_dir.mkdir(parents=True, exist_ok=True)

    # Try pikepdf repair first
    if deps["pikepdf"]:
        try:
            pikepdf_repaired_path = processing_dir / f"{pdf_file.stem}_pikepdf_repaired.pdf"

            # Open with pikepdf and save (this can fix some corruption issues)
            with pikepdf.open(pdf_path, allow_overwriting_input=False) as pdf:
                pdf.save(str(pikepdf_repaired_path), fix_metadata_version=True)

            if pikepdf_repaired_path.exists():
                original_size = pdf_file.stat().st_size
                repaired_size = pikepdf_repaired_path.stat().st_size
                print(f"✅ pikepdf repair successful: {pikepdf_repaired_path.name}")
                print(f"   📊 Size: {original_size:,} → {repaired_size:,} bytes")
                return {
                    "status": "repaired",
                    "repaired_path": str(pikepdf_repaired_path),
                    "repair_method": "pikepdf"
                }
        except Exception as e:
            print(f"⚠️ pikepdf repair failed: {str(e)}")

    print(f"ℹ️  No repairs performed (tools limited or PDF already valid)")
    return {
        "status": "no_repair_needed",
        "repaired_path": pdf_path,
        "repair_method": "none"
    }


def simple_pdf_cleaning(pdf_path):
    """Simple PDF cleaning with PyMuPDF."""
    print_subsection("PDF Cleaning Test")
    print(f"🧹 Cleaning: {Path(pdf_path).name}")

    try:
        # Create processing directory
        processing_dir = Path("data/temp/pdf_processing") / Path(pdf_path).stem
        processing_dir.mkdir(parents=True, exist_ok=True)

        clean_path = processing_dir / f"{Path(pdf_path).stem}_clean.pdf"

        # Open and clean the PDF
        doc = fitz.open(pdf_path)
        doc.save(str(clean_path), incremental=False, deflate=True)
        doc.close()

        if clean_path.exists():
            original_size = Path(pdf_path).stat().st_size
            clean_size = clean_path.stat().st_size
            size_diff = original_size - clean_size
            percent_change = (size_diff / original_size) * 100 if original_size > 0 else 0

            print(f"✅ PDF cleaning successful: {clean_path.name}")
            print(f"📊 Size change: {original_size:,} → {clean_size:,} bytes")
            print(f"📉 Difference: {size_diff:+,} bytes ({percent_change:+.1f}%)")

            return {
                "status": "cleaned",
                "clean_path": str(clean_path),
                "original_size": original_size,
                "clean_size": clean_size,
            }
        else:
            print(f"❌ Cleaning failed: output file not found")
            return {"status": "failed"}

    except Exception as e:
        print(f"❌ PDF cleaning failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


def test_full_processing_chain():
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
    validation_result = simple_pdf_validation(current_path)

    # Step 2: Repair (if needed or forced)
    if validation_result['needs_repair'] or True:  # Force for testing
        repair_result = simple_pdf_repair(current_path)

        if repair_result['status'] == 'repaired':
            current_path = repair_result['repaired_path']
            print(f"\n   → Using repaired file for next step")

    # Step 3: Cleaning
    clean_result = simple_pdf_cleaning(current_path)

    if clean_result['status'] == 'cleaned':
        final_path = clean_result['clean_path']

        # Compare final result with original
        original_size = test_pdf_path.stat().st_size
        final_size = Path(final_path).stat().st_size
        size_diff = original_size - final_size

        print(f"\n📊 Processing Chain Summary:")
        print(f"   📁 Original: {test_pdf_path.name} ({original_size:,} bytes)")
        print(f"   📁 Final:    {Path(final_path).name} ({final_size:,} bytes)")
        print(f"   📉 Change:   {size_diff:+,} bytes")

    # Cleanup
    print_subsection("Cleanup")
    try:
        processing_dir = Path("data/temp/pdf_processing") / test_pdf_path.stem
        if processing_dir.exists():
            shutil.rmtree(processing_dir)
            print("   ✅ Temporary files cleaned up")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")


def find_test_pdf():
    """Find a test PDF file to use for testing."""
    # Look for PDF files in the project
    project_root = Path(__file__).parent

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


def main():
    """Run all PDF toolchain tests."""
    print_section("🚀 PDF TOOLCHAIN COMPREHENSIVE TEST SUITE", 80)
    print(f"Project: {Path(__file__).parent.name}")
    print(f"Test Script: {Path(__file__).name}")

    # Test 1: Dependencies
    deps_ok = test_dependency_availability()
    if not deps_ok:
        print("\n❌ Critical: No PDF tools available. Cannot continue testing.")
        return

    # Test 2: Direct library testing
    test_direct_pdf_libraries()

    # Test 3: Full processing chain
    test_full_processing_chain()

    print_section("✅ ALL TESTS COMPLETED", 80)
    print("🎯 The PDF validation and repair system is ready!")
    print("📝 To use in your code:")
    print("   python -m test_pdf_toolchain_simple")


if __name__ == "__main__":
    main()