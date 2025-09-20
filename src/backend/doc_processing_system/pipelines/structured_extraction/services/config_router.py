import textwrap
import langextract as lx
from typing import Tuple, List
from dotenv import load_dotenv
load_dotenv()




def invoice_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract Malaysian utility bill information. Extract each field type only ONCE - choose the primary/main value if multiple exist.

    Extract these fields:
    - sumber_bil: Customer company name
    - alamat_pos: Customer postal address
    - no_invois: Invoice number
    - no_akaun: Account number
    - baki_terdahulu: Previous balance amount
    - caj_semasa: Current charges (main summary value, NOT NEM-specific, may be empty if only NEM charges exist)
    - caj_semasa_nem: Current charges under NEM program (only extract if explicitly labeled as "NEM" charges, typically large amounts)
    - deposit_sekuriti: Security deposit
    - jumlah_bil: Total bill amount
    - tarikh_bil: Bill date
    - bayar_sebelum: Payment due date
    - tempoh_bil: Billing period
    - bayaran_bagi_tempoh: Payment period
    - amaun_bayaran_bagi_tempoh: Payment amount
    - biller_code: Biller code
    - ref_1: Reference number
    - pelarasan_penggenapan: Rounding adjustment (small amounts like -RM0.01, -RM0.02, typically less than RM1)
    - tarikh_akhir_jelaskan_tunggakan: Final settlement date
    - amaun_rm_tunggakan: Arrears amount
    - Baki NEM: NEM balance accumulated
    - Tarikh Luput Baki NEM: NEM balance expiry date

    IMPORTANT:
    - caj_semasa_nem should only be extracted when explicitly mentioned as "NEM" charges
    - caj_semasa may be empty if the bill only contains NEM charges
    - pelarasan_penggenapan is for small rounding adjustments (usually cents, like -RM0.01)
    - Do NOT confuse small rounding amounts with large NEM charges
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="""## Bil Elektrik Anda

## ALAMAT POS

## GS PAPERBOARD &amp; PACKAGING SDN. BHD.

NO. 24, JALAN ALOI 3

KAWASAN  PERUSAHAAN  BUKIT  CHANGGANG

UTAMA

42700 BANTING

SELANGOR

Sila imbas bagi pembayaran di Kios @Kedai Tenaga

210299319006000271377327000000016958275

Jumlah Bil Anda (RM)

169,582.75

## KLIK DI SINI UNTUK PEMBAYARAN

Sila bayar sebelum

31 Ogos 2025

## Ringkasan Bil Anda:

| Baki Terdahulu                                     | RM0.00       |
|----------------------------------------------------|--------------|
| Caj Semasa NEM                                     | RM169,582.76 |
| Pelarasan Penggenapan                              | -RM0.01      |
| Baki NEM Terkumpul                                 | RM0.00       |
| Baki NEM Dibawa Ke Hadapan - Luput pada 31.12.2025 | RM0.00       |

TARIKH BIL

01.08.2025

TEMPOH BIL

01.07.2025 - 31.07.2025 (31 Hari)

## NO. INVOIS

000271377327

## DEPOSIT SEKURITI

RM994,898.92

NO. AKAUN

210299319006

BAYARAN BAGI TEMPOH 01.07.2025 - 31.07.2025

RM5,000.00

Biller Code:

5454

Ref-1:

210299319006""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="sumber_bil",
                    extraction_text="GS PAPERBOARD & PACKAGING SDN. BHD.",
                    attributes={"bill_source": "GS PAPERBOARD & PACKAGING SDN. BHD.", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class="alamat_pos",
                    extraction_text="NO. 24, JALAN ALOI 3\n\nKAWASAN  PERUSAHAAN  BUKIT  CHANGGANG\n\nUTAMA\n\n42700 BANTING\n\nSELANGOR",
                    attributes={"postal_address": "NO. 24, JALAN ALOI 3, KAWASAN PERUSAHAAN BUKIT CHANGGANG UTAMA, 42700 BANTING SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="jumlah_bil",
                    extraction_text="169,582.75",
                    attributes={"total_bill": 169582.75, "currency": "MYR", "amount": 169582.75, "type": "main_total"}
                ),
                lx.data.Extraction(
                    extraction_class="bayar_sebelum",
                    extraction_text="31 Ogos 2025",
                    attributes={"pay_before": "31 Ogos 2025", "iso_date": "2025-08-31"}
                ),
                lx.data.Extraction(
                    extraction_class="no_akaun",
                    extraction_text="210299319006",
                    attributes={"account_number": "210299319006"}
                ),
                lx.data.Extraction(
                    extraction_class="bayaran_bagi_tempoh",
                    extraction_text="01.07.2025 - 31.07.2025",
                    attributes={"payment_for_period": "01.07.2025 - 31.07.2025", "start_date": "2025-07-01", "end_date": "2025-07-31"}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_bayaran_bagi_tempoh",
                    extraction_text="RM5,000.00",
                    attributes={"payment_amount_for_period": 5000.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
                lx.data.Extraction(
                    extraction_class="ref_1",
                    extraction_text="210299319006",
                    attributes={"reference_1": "210299319006", "type": "account_reference"}
                ),
                lx.data.Extraction(
                    extraction_class="baki_terdahulu",
                    extraction_text="RM0.00",
                    attributes={"previous_balance": 0.00, "currency": "MYR", "amount": 0.00, "type": "previous_outstanding"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="",
                    attributes={"current_charges": "", "currency": "", "amount": "", "type": "regular_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa_nem",
                    extraction_text="RM169,582.76",
                    attributes={"current_charges_nem": 169582.76, "currency": "MYR", "amount": 169582.76, "type": "nem_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="pelarasan_penggenapan",
                    extraction_text="-RM0.01",
                    attributes={"rounding_adjustment": -0.01, "currency": "MYR", "amount": -0.01, "type": "billing_adjustment"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_bil",
                    extraction_text="01.08.2025",
                    attributes={"bill_date": "01.08.2025", "iso_date": "2025-08-01"}
                ),
                lx.data.Extraction(
                    extraction_class="tempoh_bil",
                    extraction_text="01.07.2025 - 31.07.2025 (31 Hari)",
                    attributes={"bill_period": "01.07.2025 - 31.07.2025", "start_date": "2025-07-01", "end_date": "2025-07-31", "days": 31}
                ),
                lx.data.Extraction(
                    extraction_class="no_invois",
                    extraction_text="000271377327",
                    attributes={"invoice_number": "000271377327"}
                ),
                lx.data.Extraction(
                    extraction_class="deposit_sekuriti",
                    extraction_text="RM994,898.92",
                    attributes={"security_deposit": 994898.92, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_akhir_jelaskan_tunggakan",
                    extraction_text="",
                    attributes={"final_arrears_settlement_date": "", "iso_date": ""}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_rm_tunggakan",
                    extraction_text="",
                    attributes={"arrears_amount": "", "currency": ""}
                ),
                lx.data.Extraction(
                    extraction_class="Baki NEM",
                    extraction_text="RM0.00",
                    attributes={"nem_balance": 0.00, "currency": "MYR", "type": "nem_accumulated_balance"}
                ),
                lx.data.Extraction(
                    extraction_class="Tarikh Luput Baki NEM",
                    extraction_text="31.12.2025",
                    attributes={"nem_balance_expiry_date": "31.12.2025", "iso_date": "2025-12-31"}
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