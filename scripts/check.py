import pymupdf  # pip install pymupdf
from io import BytesIO


def repair_pdf_with_pymupdf(input_path, output_path):
    try:
        # Open the corrupted PDF
        doc = pymupdf.open(input_path)

        # Create a repaired version
        repaired_bytes = doc.tobytes(garbage=3, deflate=True)

        # Save the repaired PDF
        with open(output_path, 'wb') as f:
            f.write(repaired_bytes)

        doc.close()
        return True
    except Exception as e:
        print(f"Repair failed: {e}")
        return False


# Usage
success = repair_pdf_with_pymupdf(
    r"/data/documents/GSPP_5407_202507_Billing.pdf",
    r"/data/documents/raw/GSPP_5407_202507_Billing_repaired.pdf"
)
