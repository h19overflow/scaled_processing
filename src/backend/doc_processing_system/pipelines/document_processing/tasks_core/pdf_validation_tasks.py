from pathlib import Path
from typing import Dict, Any
import subprocess
import shutil
import os
import fitz
from prefect import task, get_run_logger

# Import PDF processing libraries
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


def check_external_dependencies() -> Dict[str, bool]:
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


@task(name="validate-pdf", retries=1)
def validate_pdf_task(raw_file_path: str) -> Dict[str, Any]:
    """
    Validate PDF structure using pdfinfo and qpdf.

    Args:
        raw_file_path: Path to the PDF file to validate

    Returns:
        Dict containing validation results and repair recommendation
    """
    logger = get_run_logger()
    logger.info(f"🔍 Validating PDF: {Path(raw_file_path).name}")

    # Check if file is actually a PDF
    if not raw_file_path.lower().endswith('.pdf'):
        return {
            "status": "skipped",
            "needs_repair": False,
            "validation_errors": [],
            "message": "File is not a PDF, skipping validation"
        }

    if not Path(raw_file_path).exists():
        return {
            "status": "error",
            "needs_repair": True,
            "validation_errors": ["File does not exist"],
            "message": f"PDF file not found: {raw_file_path}"
        }

    validation_errors = []
    needs_repair = False

    # Check dependencies
    deps = check_external_dependencies()

    # Validate with pdfinfo if available
    if deps["pdfinfo"]:
        try:
            result = subprocess.run(
                ["pdfinfo", raw_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                validation_errors.append(f"pdfinfo failed: {result.stderr}")
                needs_repair = True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            validation_errors.append(f"pdfinfo error: {str(e)}")
            needs_repair = True

    # Validate with qpdf if available
    if deps["qpdf"]:
        try:
            result = subprocess.run(
                ["qpdf", "--check", raw_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                validation_errors.append(f"qpdf check failed: {result.stderr}")
                needs_repair = True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            validation_errors.append(f"qpdf error: {str(e)}")
            needs_repair = True

    # Try pikepdf validation if available
    if deps["pikepdf"]:
        try:
            with pikepdf.open(raw_file_path) as pdf:
                page_count = len(pdf.pages)
                logger.info(f"✅ pikepdf validation passed: {page_count} pages")
        except Exception as e:
            validation_errors.append(f"pikepdf error: {str(e)}")
            needs_repair = True

    # Try PyMuPDF validation if available
    if deps["pymupdf"]:
        try:
            doc = fitz.open(raw_file_path)
            if doc.is_pdf and doc.page_count > 0:
                logger.info(f"✅ PyMuPDF validation passed: {doc.page_count} pages")
            else:
                validation_errors.append("PyMuPDF: Invalid PDF structure")
                needs_repair = True
            doc.close()
        except Exception as e:
            validation_errors.append(f"PyMuPDF error: {str(e)}")
            needs_repair = True

    # If no tools available, assume PDF is valid
    if not any(deps.values()):
        logger.warning("⚠️ No PDF validation tools available, assuming PDF is valid")
        return {
            "status": "no_tools",
            "needs_repair": False,
            "validation_errors": ["No validation tools available"],
            "message": "PDF validation skipped - no tools available"
        }

    status = "needs_repair" if needs_repair else "valid"
    logger.info(f"📋 PDF validation complete: {status}")

    return {
        "status": status,
        "needs_repair": needs_repair,
        "validation_errors": validation_errors,
        "message": f"PDF validation completed with {len(validation_errors)} errors"
    }


@task(name="repair-pdf", retries=2)
def repair_pdf_task(raw_file_path: str) -> Dict[str, Any]:
    """
    Repair corrupted PDF using Ghostscript with QPDF fallback.

    Args:
        raw_file_path: Path to the corrupted PDF file

    Returns:
        Dict containing repair results and repaired file path
    """
    logger = get_run_logger()
    logger.info(f"🔧 Repairing PDF: {Path(raw_file_path).name}")

    raw_path = Path(raw_file_path)
    if not raw_path.exists():
        return {
            "status": "error",
            "repaired_path": raw_file_path,
            "repair_method": "none",
            "message": f"Source file not found: {raw_file_path}"
        }

    # Create processing directory
    processing_dir = Path("data/temp/pdf_processing") / raw_path.stem
    processing_dir.mkdir(parents=True, exist_ok=True)

    repaired_path = processing_dir / f"{raw_path.stem}_repaired.pdf"

    deps = check_external_dependencies()

    # Try Ghostscript repair first
    if deps["ghostscript"]:
        try:
            # Try different Ghostscript commands for Windows/Linux
            gs_commands = ["gs", "gswin64c", "gswin32c"]
            gs_cmd = None

            for cmd in gs_commands:
                try:
                    subprocess.run([cmd, "--version"], capture_output=True, check=True)
                    gs_cmd = cmd
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue

            if gs_cmd:
                result = subprocess.run([
                    gs_cmd, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
                    "-dPDFSETTINGS=/prepress", "-dCompatibilityLevel=1.4",
                    f"-sOutputFile={repaired_path}", str(raw_path)
                ], capture_output=True, text=True, timeout=120)

                if result.returncode == 0 and repaired_path.exists():
                    logger.info(f"✅ Ghostscript repair successful: {repaired_path}")
                    return {
                        "status": "repaired",
                        "repaired_path": str(repaired_path),
                        "repair_method": "ghostscript",
                        "message": "PDF repaired successfully with Ghostscript"
                    }
                else:
                    logger.warning(f"⚠️ Ghostscript repair failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ Ghostscript repair error: {str(e)}")

    # Fallback to QPDF repair (command line)
    if deps["qpdf"]:
        try:
            qpdf_repaired_path = processing_dir / f"{raw_path.stem}_qpdf_repaired.pdf"

            result = subprocess.run([
                "qpdf", "--repair", str(raw_path), str(qpdf_repaired_path)
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and qpdf_repaired_path.exists():
                logger.info(f"✅ QPDF repair successful: {qpdf_repaired_path}")
                return {
                    "status": "repaired",
                    "repaired_path": str(qpdf_repaired_path),
                    "repair_method": "qpdf",
                    "message": "PDF repaired successfully with QPDF"
                }
            else:
                logger.warning(f"⚠️ QPDF repair failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ QPDF repair error: {str(e)}")

    # Fallback to pikepdf repair
    if deps["pikepdf"]:
        try:
            pikepdf_repaired_path = processing_dir / f"{raw_path.stem}_pikepdf_repaired.pdf"

            # Open with pikepdf and save (this can fix some corruption issues)
            with pikepdf.open(raw_path, allow_overwriting_input=False) as pdf:
                pdf.save(str(pikepdf_repaired_path), fix_metadata_version=True)

            if pikepdf_repaired_path.exists():
                logger.info(f"✅ pikepdf repair successful: {pikepdf_repaired_path}")
                return {
                    "status": "repaired",
                    "repaired_path": str(pikepdf_repaired_path),
                    "repair_method": "pikepdf",
                    "message": "PDF repaired successfully with pikepdf"
                }
        except Exception as e:
            logger.warning(f"⚠️ pikepdf repair error: {str(e)}")

    # If all repair methods failed, return original file
    logger.error(f"❌ All PDF repair methods failed for: {raw_path.name}")
    return {
        "status": "failed",
        "repaired_path": raw_file_path,
        "repair_method": "none",
        "message": "All PDF repair methods failed, using original file"
    }


@task(name="clean-pdf-pymupdf", retries=1)
def clean_with_pymupdf_task(pdf_path: str) -> Dict[str, Any]:
    """
    Clean PDF using PyMuPDF to remove incremental updates and optimize structure.

    Args:
        pdf_path: Path to the PDF file to clean

    Returns:
        Dict containing cleaning results and cleaned file path
    """
    logger = get_run_logger()
    logger.info(f"🧹 Cleaning PDF with PyMuPDF: {Path(pdf_path).name}")

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {
            "status": "error",
            "clean_path": pdf_path,
            "message": f"Source file not found: {pdf_path}"
        }

    deps = check_external_dependencies()
    if not deps["pymupdf"]:
        return {
            "status": "skipped",
            "clean_path": pdf_path,
            "message": "PyMuPDF not available, skipping cleaning"
        }

    try:
        # Create processing directory
        processing_dir = Path("data/temp/pdf_processing") / pdf_file.stem
        processing_dir.mkdir(parents=True, exist_ok=True)

        clean_path = processing_dir / f"{pdf_file.stem}_clean.pdf"

        # Open and clean the PDF
        doc = fitz.open(pdf_path)

        # Save with incremental=False to remove incremental updates
        doc.save(str(clean_path), incremental=False, deflate=True)
        doc.close()

        if clean_path.exists():
            original_size = pdf_file.stat().st_size
            clean_size = clean_path.stat().st_size
            size_diff = original_size - clean_size

            logger.info(f"✅ PyMuPDF cleaning successful: {clean_path}")
            logger.info(f"📊 Size change: {original_size} → {clean_size} bytes ({size_diff:+d})")

            return {
                "status": "cleaned",
                "clean_path": str(clean_path),
                "original_size": original_size,
                "clean_size": clean_size,
                "message": f"PDF cleaned successfully, size change: {size_diff:+d} bytes"
            }
        else:
            return {
                "status": "failed",
                "clean_path": pdf_path,
                "message": "Cleaning completed but output file not found"
            }

    except Exception as e:
        logger.error(f"❌ PyMuPDF cleaning failed: {str(e)}")
        return {
            "status": "failed",
            "clean_path": pdf_path,
            "message": f"PyMuPDF cleaning failed: {str(e)}"
        }


def cleanup_pdf_processing_temp(document_id: str) -> None:
    """Clean up temporary PDF processing files."""
    processing_dir = Path("data/temp/pdf_processing") / document_id
    if processing_dir.exists():
        try:
            shutil.rmtree(processing_dir)
        except Exception:
            pass