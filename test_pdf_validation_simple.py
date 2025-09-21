"""
Simple test script for PDF validation and repair functionality (without Prefect).
"""
from pathlib import Path
import subprocess
import fitz


def check_external_dependencies():
    """Check if required PDF processing tools are available."""
    dependencies = {
        "pdfinfo": False,
        "qpdf": False,
        "ghostscript": False,
        "pymupdf": False
    }

    # Check pdfinfo (poppler-utils)
    try:
        subprocess.run(["pdfinfo", "-v"], capture_output=True, check=True)
        dependencies["pdfinfo"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Check qpdf
    try:
        subprocess.run(["qpdf", "--version"], capture_output=True, check=True)
        dependencies["qpdf"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Check ghostscript (try both gs and gswin64c for Windows)
    for gs_cmd in ["gs", "gswin64c", "gswin32c"]:
        try:
            subprocess.run([gs_cmd, "--version"], capture_output=True, check=True)
            dependencies["ghostscript"] = True
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # Check PyMuPDF
    try:
        import fitz
        dependencies["pymupdf"] = True
    except ImportError:
        pass

    return dependencies


def simple_pdf_validation(pdf_path):
    """Simple PDF validation without Prefect tasks."""
    print(f"\nValidating PDF: {Path(pdf_path).name}")

    validation_errors = []
    needs_repair = False

    # Check with pdfinfo
    try:
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"✅ pdfinfo validation passed")
            print(f"   Output: {result.stdout[:200]}...")
        else:
            print(f"❌ pdfinfo validation failed: {result.stderr}")
            validation_errors.append(f"pdfinfo failed: {result.stderr}")
            needs_repair = True
    except Exception as e:
        print(f"⚠️ pdfinfo error: {str(e)}")
        validation_errors.append(f"pdfinfo error: {str(e)}")
        needs_repair = True

    # Check with PyMuPDF
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

    return {
        "needs_repair": needs_repair,
        "validation_errors": validation_errors
    }


def simple_pdf_cleaning(pdf_path):
    """Simple PDF cleaning with PyMuPDF."""
    print(f"\nCleaning PDF: {Path(pdf_path).name}")

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

            print(f"✅ PDF cleaning successful: {clean_path}")
            print(f"📊 Size change: {original_size} → {clean_size} bytes ({size_diff:+d})")

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


def main():
    """Test PDF validation functionality."""
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
            print(f"\n2. Testing PDF: {Path(pdf_path).name}")
            print("-" * 40)

            # Test validation
            validation_result = simple_pdf_validation(pdf_path)
            print(f"   Needs Repair: {validation_result['needs_repair']}")
            if validation_result['validation_errors']:
                print(f"   Errors: {validation_result['validation_errors']}")

            # Test cleaning
            clean_result = simple_pdf_cleaning(pdf_path)
            if clean_result['status'] == 'cleaned':
                print(f"   Clean Status: Success")
                print(f"   Clean Path: {clean_result['clean_path']}")

            print("\n" + "=" * 50)
            break  # Test only the first available PDF

    else:
        print("\n❌ No test PDF files found.")

if __name__ == "__main__":
    main()