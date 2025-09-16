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
    - caj_semasa: Current charges (main summary value)
    - deposit_sekuriti: Security deposit
    - jumlah_bil: Total bill amount
    - tarikh_bil: Bill date
    - bayar_sebelum: Payment due date
    - tempoh_bil: Billing period
    - bayaran_bagi_tempoh: Payment period
    - amaun_bayaran_bagi_tempoh: Payment amount
    - biller_code: Biller code
    - ref_1: Reference number
    - pelarasan_penggenapan: Rounding adjustment
    - tarikh_akhir_jelaskan_tunggakan: Final settlement date
    - amaun_rm_tunggakan: Arrears amount
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="""## Bil Elektrik Anda

## Bil Elektrik Anda

## ALAMAT POS

GS  PAPERBOARD  &amp;  PACKAGING (SELANGOR) SDN BHD.

LOT 36967, JALAN HAJI ABDUL MANAN

MERU 41050 KLANG SELANGOR

Sila imbas bagi pembayaran di Kios @Kedai Tenaga

210111780602000943984273000000015229810

Jumlah Bil Anda (RM)

152,298.10

KLIK DI SINI UNTUK PEMBAYARAN

Sila bayar sebelum

14 Ogos 2025

NO. AKAUN

210111780602

JENIS BACAAN

Bacaan Sebenar

TARIF

E2:Perindustrian

BAYARAN BAGI TEMPOH 01.06.2025 - 30.06.2025

RM1,809.50

Biller Code:

5454

Ref-1:

210111780602

JomPAY online di Perbankan Internet dan Telefon Mudah Alih dengan akaun semasa, simpanan atau kad kredit

| Ringkasan Bil Anda:   |              |
|-----------------------|--------------|
| Baki Terdahulu        | RM0.00       |
| Caj Semasa NEM        | RM152,298.12 |
| Pelarasan Penggenapan | -RM0.02      |
| Baki NEM              | RM0.00       |

TARIKH BIL

15.07.2025

TEMPOH BIL

01.06.2025 - 30.06.2025 (30 Hari)

NO. INVOIS

000943984273

DEPOSIT SEKURITI

RM313,418.73

## Maklumat Tambahan untuk Anda

| MaximumAllowable Quantity(MAQ)      | 57,413.00   |
|-------------------------------------|-------------|
| Average System Marginal Price (SMP) | 0.2103      |
| Beban Diisytiharkan                 | 950.00kW    |
| Kehendak Maksima Tertinggi          | 819.00kW    |
| Faktor Beban                        | 0.54        |
| Angkadar Kuasa                      | 0.94        |

Untuk maklumat terperinci, sila rujuk di muka surat sebelah

## Caj Elektrik Anda Bagi Tempoh 6 Bulan

| Caj Bulanan (RM)   | Caj Bulanan (RM)   |
|--------------------|--------------------|
| Jan-25             | RM154,854.85       |
| Feb-25             | RM136,265.70       |
| Mac-25             |                    |
| Apr-25             | RM156,809.50       |
| Mei-25             | RM152,298.10       |
| Jun-25             |                    |

## TIP MENINCKATKAN KECEKAPAN TENAGA

Telapkan penghawa anda dingin pada bagi

Penghawa dingin menggunakan banyak elektrik. Menetapkan suhu di antara mampu untuk mengekalkan kedinginan, di samping mengurangkan penggunaan elektrik anda.

""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="sumber_bil",
                    extraction_text="GS PAPERBOARD & PACKAGING (SELANGOR) SDN BHD.",
                    attributes={"bill_source": "GS PAPERBOARD & PACKAGING (SELANGOR) SDN BHD.", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class="alamat_pos",
                    extraction_text="LOT 36967, JALAN HAJI ABDUL MANAN\n\nMERU 41050 KLANG SELANGOR",
                    attributes={"postal_address": "LOT 36967, JALAN HAJI ABDUL MANAN, MERU 41050 KLANG SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="jumlah_bil",
                    extraction_text="152,298.10",
                    attributes={"total_bill": 152298.10, "currency": "MYR", "amount": 152298.10, "type": "main_total"}
                ),
                lx.data.Extraction(
                    extraction_class="bayar_sebelum",
                    extraction_text="14 Ogos 2025",
                    attributes={"pay_before": "14 Ogos 2025", "iso_date": "2025-08-14"}
                ),
                lx.data.Extraction(
                    extraction_class="no_akaun",
                    extraction_text="210111780602",
                    attributes={"account_number": "210111780602"}
                ),
                lx.data.Extraction(
                    extraction_class="bayaran_bagi_tempoh",
                    extraction_text="01.06.2025 - 30.06.2025",
                    attributes={"payment_for_period": "01.06.2025 - 30.06.2025", "start_date": "2025-06-01", "end_date": "2025-06-30"}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_bayaran_bagi_tempoh",
                    extraction_text="RM1,809.50",
                    attributes={"payment_amount_for_period": 1809.50, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
                lx.data.Extraction(
                    extraction_class="ref_1",
                    extraction_text="210111780602",
                    attributes={"reference_1": "210111780602", "type": "account_reference"}
                ),
                lx.data.Extraction(
                    extraction_class="baki_terdahulu",
                    extraction_text="RM0.00",
                    attributes={"previous_balance": 0.00, "currency": "MYR", "amount": 0.00, "type": "previous_outstanding"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="RM152,298.12",
                    attributes={"current_charges": 152298.12, "currency": "MYR", "amount": 152298.12, "type": "main_summary_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="pelarasan_penggenapan",
                    extraction_text="-RM0.02",
                    attributes={"rounding_adjustment": -0.02, "currency": "MYR", "amount": -0.02, "type": "billing_adjustment"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_bil",
                    extraction_text="15.07.2025",
                    attributes={"bill_date": "15.07.2025", "iso_date": "2025-07-15"}
                ),
                lx.data.Extraction(
                    extraction_class="tempoh_bil",
                    extraction_text="01.06.2025 - 30.06.2025 (30 Hari)",
                    attributes={"bill_period": "01.06.2025 - 30.06.2025", "start_date": "2025-06-01", "end_date": "2025-06-30", "days": 30}
                ),
                lx.data.Extraction(
                    extraction_class="no_invois",
                    extraction_text="000943984273",
                    attributes={"invoice_number": "000943984273"}
                ),
                lx.data.Extraction(
                    extraction_class="deposit_sekuriti",
                    extraction_text="RM313,418.73",
                    attributes={"security_deposit": 313418.73, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_akhir_jelaskan_tunggakan",
                    extraction_text="",
                    attributes={"final_arrears_settlement_date": "", "iso_date": ""}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_rm_tunggakan",
                    extraction_text="RM0.00",
                    attributes={"arrears_amount": 0.00, "currency": "MYR"}
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
