import textwrap
import langextract as lx
from typing import Tuple, List
from dotenv import load_dotenv
load_dotenv()


# TODO Current charges not extracted in teh 5407202508
def invoice_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
Extract Malaysian utility bill information. Extract each field type only ONCE - choose the primary/main value if multiple exist.  
Fields might appear in malay.  
  
Extract these fields:  
- postal_address: Customer postal address  
- invoice_number: Invoice number    
- amount_due: The amount due at the end of the billing period  
- due_date: Payment due date  
- biller_code: Biller code  


    """).strip()

    examples = [
        # Comprehensive example: Utility bill with both regular charges and NEM charges
        lx.data.ExampleData(
            text="""
ALAMAT POS
GS PAPERBOARD & PACKAGING SDN. BHD.
NO. 24, JALAN ALOI 3
KAWASAN PERUSAHAAN BUKIT CHANGGANG UTAMA
42700 BANTING SELANGOR

TARIKH BIL: 01.08.2025
TEMPOH BIL: 01.07.2025 - 31.07.2025 (31 Hari)
NO. INVOIS: 000271377327
NO. AKAUN: 210299319006

BAYARAN BAGI TEMPOH
15.06.2025 - 14.07.2025
RM1,255.75

Ringkasan Bil Anda:
BAKI TERDAHULU RM125.50
CAJ SEMASA RM450.00
CAJ SEMASA NEM RM169,582.76
DEPOSIT SEKURITI RM200.00
PELARASAN PEMBUNDARAN -RM0.01
JUMLAH BIL ANDA RM170,358.25

BAKI NEM RM15,250.50
TARIKH LUPUT BAKI NEM: 31.12.2025

TUNGGAKAN: RM250.75
TARIKH PENYELESAIAN AKHIR: 15.09.2025

Sila bayar sebelum: 31 Ogos 2025
Biller Code: 5454
Ref-1: 210299319006
""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="postal_address",
                    extraction_text="NO. 24, JALAN ALOI 3\nKAWASAN PERUSAHAAN BUKIT CHANGGANG UTAMA\n42700 BANTING SELANGOR",
                    attributes={"postal_address": "NO. 24, JALAN ALOI 3, KAWASAN PERUSAHAAN BUKIT CHANGGANG UTAMA, 42700 BANTING SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="000271377327",
                    attributes={"invoice_number": "000271377327"}
                ),
                lx.data.Extraction(
                    extraction_class="amount_due",
                    extraction_text="BAYARAN BAGI TEMPOH\n15.06.2025 - 14.07.2025\nRM1,255.75",
                    attributes={"amount_due": 1255.75, "currency": "MYR", "type": "final_payable"}
                ),
                lx.data.Extraction(
                    extraction_class="due_date",
                    extraction_text="31 Ogos 2025",
                    attributes={"due_date": "31 Ogos 2025", "iso_date": "2025-08-31"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
            ]
        )
    ]
    return extraction_prompt, examples


def process_document(text: str):
    """Process document using langextract with appropriate routing and temporal normalization"""
    prompt, examples = invoice_extraction()
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-2.-flash",
        max_workers=1,
        max_char_buffer=5000,  # Smaller buffer for better JSON stability
        temperature=0.0,       # Small temperature for controlled randomness
        extraction_passes=1    # Single pass to avoid JSON conflicts
    )
    return result

if __name__ == "__main__":
    # Example usage with utility bill content
    text = """
ALAMAT POS
TENAGA NASIONAL BERHAD
NO. 15, JALAN SULTAN ISMAIL
50250 KUALA LUMPUR

TARIKH BIL: 15.09.2025
TEMPOH BIL: 15.08.2025 - 14.09.2025 (30 Hari)
NO. INVOIS: 000445566778
NO. AKAUN: 401234567890

Ringkasan Bil Anda:
BAKI TERDAHULU RM125.50
CAJ SEMASA RM450.00
JUMLAH BIL ANDA RM575.50

Sila bayar sebelum: 30 September 2025
Biller Code: 1234
Ref-1: 401234567890
    """
    doc = process_document(text)
    print(doc)
    for extraction in doc.extractions:
        print(extraction)