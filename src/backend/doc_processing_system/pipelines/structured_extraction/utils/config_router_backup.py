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
    - bill_source: Customer company name
    - postal_address: Customer postal address
    - invoice_number: Invoice number
    - bill_account_id: Account number
    - previous_balance: Previous balance amount
    - current_charges: Current charges (main summary value, NOT NEM-specific, may be empty if only NEM charges exist)
    - current_charges_nem: Current charges under NEM program (only extract if explicitly labeled as "NEM" charges, typically large amounts)
    - security_deposit: Security deposit
    - amount_due: The amount due at the end of the billing period
    - issue_date: Bill date
    - due_date: Payment due date
    - billing_period_start: Billing period start date
    - billing_period_end: Billing period end date
    - payment_period: Payment period
    - payment_amount: Payment amount
    - biller_code: Biller code
    - reference_1: Reference number
    - rounding_adjustment: Rounding adjustment (small amounts like -RM0.01, -RM0.02, typically less than RM1)
    - arrears_final_date: Final settlement date
    - arrears_amount: Arrears amount
    - nem_balance: NEM balance accumulated
    - nem_balance_expiry: NEM balance expiry date

    IMPORTANT:
    - current_charges_nem should only be extracted when explicitly mentioned as "NEM" charges
    - current_charges may be empty if the bill only contains NEM charges
    - rounding_adjustment is for small rounding adjustments (usually cents, like -RM0.01)
    - Do NOT confuse small rounding amounts with large NEM charges
    
    REFLECT AND DOUBLE CHECK THE REQUIRED and THE EXTRACTION FIELDS TO ENSURE ALL ARE COVERED.
    Ask yourself: "Is there any field that might be missing or overlooked?"
    
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
                    extraction_class="bill_source",
                    extraction_text="GS PAPERBOARD & PACKAGING SDN. BHD.",
                    attributes={"bill_source": "GS PAPERBOARD & PACKAGING SDN. BHD.", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class='amount_due',
                    extraction_text="""
                    BAYARAN BAGI TEMPOH 
                    01.06.2025 - 30.06.2025
                    RM1,809.50
                    """,
                    attributes={'amount_due': 1809.50, 'currency': 'MYR'}

                ),
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
                    extraction_class="bill_account_id",
                    extraction_text="210299319006",
                    attributes={"account_number": "210299319006"}
                ),
                lx.data.Extraction(
                    extraction_class="previous_balance",
                    extraction_text="BAKI TERDAHULU RM0.00",
                    attributes={"previous_balance": 0.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="current_charges",
                    extraction_text="",
                    attributes={"current_charges": "", "currency": "", "type": "regular_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="current_charges_nem",
                    extraction_text="CAJ SEMASA NEM RM169,582.76",
                    attributes={"current_charges_nem": 169582.76, "currency": "MYR", "type": "nem_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="rounding_adjustment",
                    extraction_text="PELARASAN PEMBUNDARAN -RM0.01",
                    attributes={"rounding_adjustment": -0.01, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="amount_due",
                    extraction_text="BAYARAN BAGI TEMPOH \n01.06.2025 - 30.06.2025\nRM1,809.50\nRingkasan Bil Anda:\nBAKI TERDAHULU RM125.50\nCAJ SEMASA RM450.00\nDEPOSIT SEKURITI RM200.00\nPELARASAN PEMBUNDARAN -RM0.02\nJUMLAH BIL ANDA RM1809.50",
                    attributes={"amount_due":1809.50, "currency": "MYR", "type": "final_payable"}
                ),
                lx.data.Extraction(
                    extraction_class="issue_date",
                    extraction_text="01.08.2025",
                    attributes={"issue_date": "01.08.2025", "iso_date": "2025-08-01"}
                ),
                lx.data.Extraction(
                    extraction_class="due_date",
                    extraction_text="31 Ogos 2025",
                    attributes={"due_date": "31 Ogos 2025", "iso_date": "2025-08-31"}
                ),
                lx.data.Extraction(
                    extraction_class="billing_period_start",
                    extraction_text="01.07.2025 - 31.07.2025 (31 Hari)",
                    attributes={"billing_period_start": "2025-07-01"}
                ),
                lx.data.Extraction(
                    extraction_class="billing_period_end",
                    extraction_text="01.07.2025 - 31.07.2025 (31 Hari)",
                    attributes={"billing_period_end": "2025-07-31"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
                lx.data.Extraction(
                    extraction_class="reference_1",
                    extraction_text="210299319006",
                    attributes={"reference_1": "210299319006"}
                )
            ]
        ),

                lx.data.Extraction(
                    extraction_class="bill_source",
                    extraction_text="TENAGA NASIONAL BERHAD",
                    attributes={"bill_source": "TENAGA NASIONAL BERHAD", "type": "utility_company"}
                ),
                lx.data.Extraction(
                    extraction_class="postal_address",
                    extraction_text="NO. 15, JALAN SULTAN ISMAIL\n50250 KUALA LUMPUR",
                    attributes={"postal_address": "NO. 15, JALAN SULTAN ISMAIL, 50250 KUALA LUMPUR"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="000445566778",
                    attributes={"invoice_number": "000445566778"}
                ),
                lx.data.Extraction(
                    extraction_class="bill_account_id",
                    extraction_text="401234567890",
                    attributes={"account_number": "401234567890"}
                ),
                lx.data.Extraction(
                    extraction_class="previous_balance",
                    extraction_text="BAKI TERDAHULU RM125.50",
                    attributes={"previous_balance": 125.50, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="current_charges",
                    extraction_text="CAJ SEMASA RM450.00",
                    attributes={"current_charges": 450.00, "currency": "MYR", "type": "regular_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="current_charges_nem",
                    extraction_text="",
                    attributes={"current_charges_nem": "", "currency": "", "type": "nem_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="security_deposit",
                    extraction_text="DEPOSIT SEKURITI RM200.00",
                    attributes={"security_deposit": 200.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="rounding_adjustment",
                    extraction_text="PELARASAN PEMBUNDARAN -RM0.02",
                    attributes={"rounding_adjustment": -0.02, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="amount_due",
                    extraction_text="BAYARAN BAGI TEMPOH \n01.06.2025 - 30.06.2025\nRM1,809.50\nRingkasan Bil Anda:\nBAKI TERDAHULU RM125.50\nCAJ SEMASA RM450.00\nDEPOSIT SEKURITI RM200.00\nPELARASAN PEMBUNDARAN -RM0.02\nJUMLAH BIL ANDA RM1809.50",
                    attributes={"amount_due": 1809.50, "currency": "MYR", "type": "final_payable"}
                ),
                lx.data.Extraction(
                    extraction_class="issue_date",
                    extraction_text="15.09.2025",
                    attributes={"issue_date": "15.09.2025", "iso_date": "2025-09-15"}
                ),
                lx.data.Extraction(
                    extraction_class="due_date",
                    extraction_text="30 September 2025",
                    attributes={"due_date": "30 September 2025", "iso_date": "2025-09-30"}
                ),
                lx.data.Extraction(
                    extraction_class="billing_period_start",
                    extraction_text="15.08.2025 - 14.09.2025 (30 Hari)",
                    attributes={"billing_period_start": "2025-08-15"}
                ),
                lx.data.Extraction(
                    extraction_class="billing_period_end",
                    extraction_text="15.08.2025 - 14.09.2025 (30 Hari)",
                    attributes={"billing_period_end": "2025-09-14"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="1234",
                    attributes={"biller_code": "1234"}
                ),
                lx.data.Extraction(
                    extraction_class="reference_1",
                    extraction_text="401234567890",
                    attributes={"reference_1": "401234567890"}
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
        model_id="gemini-2.0-flash",
        max_workers=5,
        max_char_buffer=15000,  # Smaller buffer for better JSON stability
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