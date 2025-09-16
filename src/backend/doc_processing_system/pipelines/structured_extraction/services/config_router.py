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

    Key Line Items (capture most important billing details):
    - penggunaan_puncak: Peak usage amount and unit
    - penggunaan_luar_puncak: Off-peak usage amount and unit
    - caj_tenaga_puncak: Peak energy charges with rate
    - caj_tenaga_luar_puncak: Off-peak energy charges with rate
    - caj_kapasiti: Capacity charges with rate
    - caj_rangkaian: Network charges with rate
    - kwtbb_percentage: KWTBB percentage and amount

    Rules:
    - Use exact text from document
    - Include meaningful attributes with currency amounts, dates, and descriptions
    - Skip if field is not clearly present
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="""## Bil Elektrik Anda

## ALAMAT POS

ACME MANUFACTURING SDN BHD

LOT 12345, JALAN INDUSTRI

SHAH ALAM 40000 SELANGOR

Jumlah Bil Anda (RM)

89,567.50

Sila bayar sebelum

15 Ogos 2024

## NO. AKAUN

123456789012

BAYARAN BAGI TEMPOH 01.07.2024 - 31.07.2024

RM2,450.00

Biller Code:

5454

Ref-1:
123456789012
""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="sumber_bil",
                    extraction_text="ACME MANUFACTURING SDN BHD",
                    attributes={"bill_source": "ACME MANUFACTURING SDN BHD", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class="alamat_pos",
                    extraction_text="LOT 12345, JALAN INDUSTRI\n\nSHAH ALAM 40000 SELANGOR",
                    attributes={"postal_address": "LOT 12345, JALAN INDUSTRI, SHAH ALAM 40000 SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="jumlah_bil",
                    extraction_text="89,567.50",
                    attributes={"total_bill": 89567.50, "currency": "MYR", "amount": 89567.50, "type": "main_total"}
                ),
                lx.data.Extraction(
                    extraction_class="bayar_sebelum",
                    extraction_text="15 Ogos 2024",
                    attributes={"pay_before": "15 Ogos 2024", "iso_date": "2024-08-15"}
                ),
                lx.data.Extraction(
                    extraction_class="no_akaun",
                    extraction_text="123456789012",
                    attributes={"account_number": "123456789012"}
                ),
                lx.data.Extraction(
                    extraction_class="bayaran_bagi_tempoh",
                    extraction_text="01.07.2024 - 31.07.2024",
                    attributes={"payment_for_period": "01.07.2024 - 31.07.2024", "start_date": "2024-07-01", "end_date": "2024-07-31"}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_bayaran_bagi_tempoh",
                    extraction_text="RM2,450.00",
                    attributes={"payment_amount_for_period": 2450.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
                lx.data.Extraction(
                    extraction_class="ref_1",
                    extraction_text="123456789012",
                    attributes={"reference_1": "123456789012", "type": "account_reference"}
                ),
                lx.data.Extraction(
                    extraction_class="baki_terdahulu",
                    extraction_text="RM0.00",
                    attributes={"previous_balance": 0.00, "currency": "MYR", "amount": 0.00, "type": "previous_outstanding"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="RM89,567.50",
                    attributes={"current_charges": 89567.50, "currency": "MYR", "amount": 89567.50, "type": "main_summary_charges"}
                ),
                lx.data.Extraction(
                    extraction_class="pelarasan_penggenapan",
                    extraction_text="-RM0.00",
                    attributes={"rounding_adjustment": 0.00, "currency": "MYR", "amount": 0.00, "type": "billing_adjustment"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_bil",
                    extraction_text="15.08.2024",
                    attributes={"bill_date": "15.08.2024", "iso_date": "2024-08-15"}
                ),
                lx.data.Extraction(
                    extraction_class="tempoh_bil",
                    extraction_text="01.07.2024 - 31.07.2024 (31 Hari)",
                    attributes={"bill_period": "01.07.2024 - 31.07.2024", "start_date": "2024-07-01", "end_date": "2024-07-31"}
                ),
                lx.data.Extraction(
                    extraction_class="no_invois",
                    extraction_text="000123456789",
                    attributes={"invoice_number": "000123456789"}
                ),
                lx.data.Extraction(
                    extraction_class="deposit_sekuriti",
                    extraction_text="RM150,000.00",
                    attributes={"security_deposit": 150000.00, "currency": "MYR"}
                ),
            ]
        ),
        lx.data.ExampleData(
            text="""

Anda Guna
Penerangan	Penggunaan	Kadar (RM)	Amaun (RM)
Puncak (kWh)	141,779.00	0.35500	50,331.55
Luar Puncak (kWh)	135,632.00	0.21900	29,703.41
Kehendak Maksima (kW)	716.00	37.00000	26,492.00
Jumlah	277,411.00		106,526.96"""
            ,
            extractions=[
                lx.data.Extraction(
                    extraction_class="penggunaan_puncak",
                    extraction_text="Puncak (kWh): 141,779.00",
                    attributes={"penggunaan": 141779.00, "unit": "kWh", "penerangan": "Puncak"}
                ),
                lx.data.Extraction(
                    extraction_class="penggunaan_luar_puncak",
                    extraction_text="Luar Puncak (kWh): 135,632.00",
                    attributes={"penggunaan": 135632.00, "unit": "kWh", "penerangan": "Luar Puncak"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_tenaga_puncak",
                    extraction_text="Puncak (kWh): 141,779.00 x 0.35500 = 50,331.55",
                    attributes={"penggunaan": 141779.00, "kadar": 0.35500, "amaun": 50331.55, "unit": "kWh", "penerangan": "Puncak"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_tenaga_luar_puncak",
                    extraction_text="Luar Puncak (kWh): 135,632.00 x 0.21900 = 29,703.41",
                    attributes={"penggunaan": 135632.00, "kadar": 0.21900, "amaun": 29703.41, "unit": "kWh", "penerangan": "Luar Puncak"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_kapasiti",
                    extraction_text="Kehendak Maksima (kW): 716.00 x 37.00000 = 26,492.00",
                    attributes={"penggunaan": 716.00, "kadar": 37.00000, "amaun": 26492.00, "unit": "kW", "penerangan": "Kehendak Maksima"}
                ),
            ]
        ),
        lx.data.ExampleData(
            text="""
Keterangan    Keterangan    Tanpa ST    Dengan ST    Jumlah
Jumlah Penggunaan Anda (277,411 kWh)    RM    80,034.96    0.00    80,034.96
Kehendak Maksima    RM    26,492.00    0.00    26,492.00
ICPT (RM0.16/kWh)    RM    44,385.76    0.00    44,385.76
Caj Penggunaan Bulan Semasa    RM    150,912.72    0.00    150,912.72
Kumpulan Wang Tenaga Boleh Baharu (1.6%)    RM            1,704.43
Lebihan Tenaga yang Dijana    RM    -319.03        -319.03
Nett Offset    RM            0.00
Caj Semasa    RM            152,298.12"""
            ,
            extractions=[
                lx.data.Extraction(
                    extraction_class="penggunaan_puncak",
                    extraction_text="Jumlah Penggunaan Anda (277,411 kWh): RM80,034.96",
                    attributes={"penggunaan": 277411, "unit": "kWh", "amaun": 80034.96, "keterangan": "Jumlah Penggunaan Anda"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_kapasiti",
                    extraction_text="Kehendak Maksima: RM26,492.00",
                    attributes={"amaun": 26492.00, "keterangan": "Kehendak Maksima", "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_tenaga_puncak",
                    extraction_text="ICPT (RM0.16/kWh): RM44,385.76",
                    attributes={"kadar": 0.16, "amaun": 44385.76, "unit": "kWh", "keterangan": "ICPT", "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_penggunaan_semasa",
                    extraction_text="Caj Penggunaan Bulan Semasa: RM150,912.72",
                    attributes={"amaun": 150912.72, "keterangan": "Caj Penggunaan Bulan Semasa", "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="kwtbb_percentage",
                    extraction_text="Kumpulan Wang Tenaga Boleh Baharu (1.6%): RM1,704.43",
                    attributes={"percentage": 1.6, "amaun": 1704.43, "keterangan": "Kumpulan Wang Tenaga Boleh Baharu", "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="kredit_nem_tenaga",
                    extraction_text="Lebihan Tenaga yang Dijana: -RM319.03",
                    attributes={"amaun": -319.03, "keterangan": "Lebihan Tenaga yang Dijana", "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="Caj Semasa: RM152,298.12",
                    attributes={"amaun": 152298.12, "keterangan": "Caj Semasa", "currency": "MYR", "type": "main_summary_charges"}
                ),
            ]
        )
    ]
    return extraction_prompt, examples



def process_document(text: str, doc_type: str):
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
    lx.io.save_annotated_documents(iter([result]), output_name="test.jsonl")
    return result

if __name__ == "__main__":
    # Example usage
    classification_2 = 'report'
    text = "Q3 2024 Financial Report prepared by Finance Department on October 1, 2024. Key Finding: Revenue increased by 15% compared to Q2 2024, reaching $2.5M. Recommendation: Increase marketing budget by 20% for Q4 to sustain growth momentum."
    doc = process_document(text, classification_2)
    print(doc)
    for extraction in doc.extractions:
        print(extraction)
