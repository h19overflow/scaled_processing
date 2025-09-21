import textwrap
import langextract as lx
from typing import Tuple, List
from dotenv import load_dotenv
load_dotenv()




def invoice_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract Malaysian utility bill information. Extract each field type only ONCE - choose the primary/main value if multiple exist.

    Extract these fields:
    - bill_source: Customer company name
    - postal_address: Customer postal address
    - invoice_number: Invoice number
    - bill_account_id: Account number
    - previous_balance: Previous balance amount
    - current_charges: Current charges (main summary value, NOT NEM-specific, may be empty if only NEM charges exist)
    - current_charges_nem: Current charges under NEM program (only extract if explicitly labeled as "NEM" charges, typically large amounts)
    - security_deposit: Security deposit
    - amount_due: Total bill amount
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
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="""
ALAMAT POS

GS PAPERBOARD & PACKAGING SDN. BHD.

NO. 24, JALAN ALOI 3

KAWASAN PERUSAHAAN BUKIT CHANGGANG

UTAMA

42700 BANTING

SELANGOR

# TARIKH BIL

01.08.2025

TEMPOH BIL

01.07.2025 - 31.07.2025 (31 Hari)

NO. INVOIS 000271377327

DEPOSIT SEKURITI RM994,898.92

NO. AKAUN

210299319006

JENIS BACAAN Bacaan Sebenar

# TARIF

E1:Perindustrian ETOU

BAYARAN BAGI TEMPOH 01.07.2025 - 31.07.2025 RM5,000.00

Biller Code: 5454
Ref-1: 210299319006

JomPAY online di Perbankan Internet dan Telefon Mudah Alih dengan akaun semasa, simpanan atau kad kredit

# Jumlah Bil Anda (RM)

169,582.75

# KLIK DI SINI UNTUK PEMBAYARAN

Sila bayar sebelum

31 Ogos 2025

# Ringkasan Bil Anda:

Untuk maklumat terperinci, sila rujuk di muka surat sebelah

BAKI TERDAHULU RM0.00

CAJ SEMASA NEM RM169,582.76

PELARASAN PEMBUNDARAN -RM0.01

JUMLAH TEMPOH INI RM169,582.75

BAKI NEM TERKUMPUL RM0.00

TARIKH LUPUT BAKI NEM 31.12.2025

# Page 0 Tables

## Table 1

<table>
<tr><td>Penerangan</td><td>Penggunaan</td><td>Kadar (RM)</td><td>Amaun (RM)</td></tr>
<tr><td>Luar Puncak (kWh)</td><td>1,294,040.00</td><td>0.3190</td><td>412,798.76</td></tr>
<tr><td>Puncak (kWh)</td><td>3,983,440.00</td><td>0.3550</td><td>1,414,121.20</td></tr>
<tr><td>Caj Permintaan Maksimum (kW)</td><td>1,328.00</td><td>37.00</td><td>49,136.00</td></tr>
<tr><td>Jumlah</td><td></td><td></td><td>1,876,055.96</td></tr>
</table>
<table><tr><td rowspan=1 colspan=1>Baki Terdahulu</td><td rowspan=1 colspan=1>RM0.00</td></tr><tr><td rowspan=1 colspan=1>Caj Semasa NEM</td><td rowspan=1 colspan=1>RM152,298.12</td></tr><tr><td rowspan=1 colspan=1> Pelarasan Penggenapan</td><td rowspan=1 colspan=1>-RM0.02</td></tr><tr><td rowspan=1 colspan=1>Baki NEM</td><td rowspan=1 colspan=1>RM0.00</td></tr></table>

""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="bill_source",
                    extraction_text="GS PAPERBOARD & PACKAGING SDN. BHD.",
                    attributes={"bill_source": "GS PAPERBOARD & PACKAGING SDN. BHD.", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class="postal_address",
                    extraction_text="NO. 24, JALAN ALOI 3\n\nKAWASAN  PERUSAHAAN  BUKIT  CHANGGANG\n\nUTAMA\n\n42700 BANTING\n\nSELANGOR",
                    attributes={"postal_address": "NO. 24, JALAN ALOI 3, KAWASAN PERUSAHAAN BUKIT CHANGGANG UTAMA, 42700 BANTING SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="amount_due",
                    extraction_text="169,582.75",
                    attributes={"total_bill": 169582.75, "currency": "MYR", "amount": 169582.75, "type": "main_total"}
                ),
                lx.data.Extraction(
                    extraction_class="due_date",
                    extraction_text="31 Ogos 2025",
                    attributes={"pay_before": "31 Ogos 2025", "iso_date": "2025-08-31"}
                ),
                lx.data.Extraction(
                    extraction_class="bill_account_id",
                    extraction_text="210299319006",
                    attributes={"account_number": "210299319006"}
                ),
                lx.data.Extraction(
                    extraction_class="payment_period",
                    extraction_text="01.07.2025 - 31.07.2025",
                    attributes={"payment_for_period": "01.07.2025 - 31.07.2025", "start_date": "2025-07-01", "end_date": "2025-07-31"}
                ),
                lx.data.Extraction(
                    extraction_class="payment_amount",
                    extraction_text="RM5,000.00",
                    attributes={"payment_amount_for_period": 5000.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
                lx.data.Extraction(
                    extraction_class="reference_1",
                    extraction_text="210299319006",
                    attributes={"reference_1": "210299319006", "type": "account_reference"}
                ),
                lx.data.Extraction(
                    extraction_class="previous_balance",
                    extraction_text="BAKI TERDAHULU RM0.00",
                    attributes={"previous_balance": 0.00, "currency": "MYR", "amount": 0.00, "type": "previous_outstanding"}
                ),
                lx.data.Extraction(
                    extraction_class="current_charges",
                    extraction_text="",
                    attributes={"current_charges": "", "currency": "", "amount": "", "type": "regular_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="amount_due",
                    extraction_text="CAJ SEMASA NEM RM169,582.76",
                    attributes={"total_bill": 152298.12, "currency": "MYR", "amount": 169582.76, "type": "nem_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="rounding_adjustment",
                    extraction_text="PELARASAN PEMBUNDARAN -RM0.01",
                    attributes={"rounding_adjustment": -0.01, "currency": "MYR", "amount": -0.01, "type": "billing_adjustment"}
                ),
                lx.data.Extraction(
                    extraction_class="issue_date",
                    extraction_text="01.08.2025",
                    attributes={"bill_date": "01.08.2025", "iso_date": "2025-08-01"}
                ),
                lx.data.Extraction(
                    extraction_class="billing_period_start",
                    extraction_text="01.07.2025 - 31.07.2025 (31 Hari)",
                    attributes={"bill_period": "01.07.2025 - 31.07.2025", "start_date": "2025-07-01", "end_date": "2025-07-31", "days": 31}
                ),
                lx.data.Extraction(
                    extraction_class="billing_period_end",
                    extraction_text="01.07.2025 - 31.07.2025 (31 Hari)",
                    attributes={"bill_period": "01.07.2025 - 31.07.2025", "start_date": "2025-07-01", "end_date": "2025-07-31", "days": 31}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="000271377327",
                    attributes={"invoice_number": "000271377327"}
                ),
                lx.data.Extraction(
                    extraction_class="security_deposit",
                    extraction_text="RM994,898.92",
                    attributes={"security_deposit": 994898.92, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="arrears_final_date",
                    extraction_text="",
                    attributes={"final_arrears_settlement_date": "", "iso_date": ""}
                ),
                lx.data.Extraction(
                    extraction_class="arrears_amount",
                    extraction_text="",
                    attributes={"arrears_amount": "", "currency": ""}
                ),
                lx.data.Extraction(
                    extraction_class="nem_balance",
                    extraction_text="BAKI NEM TERKUMPUL RM0.00",
                    attributes={"nem_balance": 0.00, "currency": "MYR", "type": "nem_accumulated_balance"}
                ),
                lx.data.Extraction(
                    extraction_class="nem_balance_expiry",
                    extraction_text="31.12.2025",
                    attributes={"nem_balance_expiry_date": "31.12.2025", "iso_date": "2025-12-31"}
                ),
                # Table-specific extractions to show HTML table data
                lx.data.Extraction(
                    extraction_class="peak_usage",
                    extraction_text="<td>Puncak (kWh)</td><td>3,983,440.00</td>",
                    attributes={"usage_type": "Puncak (kWh)", "consumption": 3983440.00, "rate": 0.3550, "amount": 1414121.20}
                ),
                lx.data.Extraction(
                    extraction_class="off_peak_usage",
                    extraction_text="<td>Luar Puncak (kWh)</td><td>1,294,040.00</td>",
                    attributes={"usage_type": "Luar Puncak (kWh)", "consumption": 1294040.00, "rate": 0.3190, "amount": 412798.76}
                ),
                lx.data.Extraction(
                    extraction_class="demand_charge",
                    extraction_text="<td>Caj Permintaan Maksimum (kW)</td><td>1,328.00</td>",
                    attributes={"charge_type": "Caj Permintaan Maksimum (kW)", "demand": 1328.00, "rate": 37.00, "amount": 49136.00}
                ),
                lx.data.Extraction(
                    extraction_class="total_charges",
                    extraction_text="<td>Jumlah</td><td></td><td></td><td>1,876,055.96</td>",
                    attributes={"total_amount": 1876055.96, "currency": "MYR", "type": "subtotal"}
                ),
            ]
        ),

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
        max_workers=10,
        max_char_buffer=5000,  # Smaller buffer for better accuracy
    )
    return result

if __name__ == "__main__":
    # Example usage
    classification_2 = 'report'
    text = "Q3 2024 Financial Report prepared by Finance Department on October 1, 2024. Key Finding: Revenue increased by 15% compared to Q2 2024, reaching $2.5M. Recommendation: Increase marketing budget by 20% for Q4 to sustain growth momentum."
    doc = process_document(text)
    print(doc)
    for extraction in doc.extractions:
        print(extraction)