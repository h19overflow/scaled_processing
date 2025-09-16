import textwrap
import langextract as lx
from typing import Tuple, List
from dotenv import load_dotenv
load_dotenv()





def invoice_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract Malaysian bill/invoice information from MARKDOWN-FORMATTED utility bills. Pay special attention to:

    MARKDOWN DOCUMENT STRUCTURE:
    - Headers starting with ## (e.g., ## ALAMAT POS, ## NO. AKAUN)
    - Table structures with | separators
    - Text that appears after section headers
    - Values in table cells and standalone text blocks

    CRITICAL MALAYSIAN BILL FIELDS TO EXTRACT:
    - sumber_bil (Bill source): Company name providing the utility service
    - alamat_pos (Postal address): Customer's complete mailing address
    - no_invois (Invoice number): Unique invoice/bill identifier
    - no_akaun (Account number): Customer's account number
    - baki_terdahulu (Previous balance): Outstanding amount from previous bill
    - caj_semasa (Current charges): Current period charges or "Caj Semasa"
    - deposit_sekuriti (Security deposit): Security deposit amount
    - jumlah_bil (Total bill): Total amount due - look for "Jumlah Bil Anda"
    - tarikh_bil (Bill date): Date the bill was issued - "TARIKH BIL"
    - bayar_sebelum (Pay before): Payment due date - "Sila bayar sebelum"
    - tempoh_bil (Bill period): Time frame covered - "TEMPOH BIL"
    - bayaran_bagi_tempoh (Payment for the period): Payment amount for specific period
    - amaun_bayaran_bagi_tempoh (Payment amount for the period): Specific payment amount
    - biller_code (Biller code): Billing company code - "Biller Code"
    - ref_1 (Reference 1): Reference number - "Ref-1"
    - pelarasan_penggenapan (Rounding adjustment): Rounding adjustments - "Pelarasan Penggenapan"
    - tarikh_akhir_jelaskan_tunggakan (Final date to settle arrears): Final settlement date
    - amaun_rm_tunggakan (Arrears amount in RM): Outstanding arrears amount

    EXTRACTION GUIDELINES:
    - Look for values that appear immediately after field labels
    - Extract data from table cells, especially in "Ringkasan Bil" tables
    - Handle both standalone text and tabular data
    - Recognize Malaysian date formats (15.07.2025, 14 Ogos 2025)
    - Extract RM currency amounts with proper formatting
    - Pay attention to section headers that indicate field locations
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

| Ringkasan Bil Anda:   |              |
|-----------------------|--------------|
| Baki Terdahulu        | RM0.00       |
| Caj Semasa NEM        | RM89,567.50  |
| Pelarasan Penggenapan | -RM0.00      |

TARIKH BIL

15.08.2024

TEMPOH BIL

01.07.2024 - 31.07.2024 (31 Hari)

NO. INVOIS

000123456789

DEPOSIT SEKURITI

RM150,000.00""",
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
                    attributes={"total_bill": 89567.50, "currency": "MYR"}
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
                    attributes={"previous_balance": 0.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="RM89,567.50",
                    attributes={"current_charges": 89567.50, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="pelarasan_penggenapan",
                    extraction_text="-RM0.00",
                    attributes={"rounding_adjustment": 0.00, "currency": "MYR"}
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
            text="""## NO. AKAUN

210987654321

## ALAMAT PREMIS

TECH SOLUTIONS SDN BHD

LOT 9876, JALAN TEKNOLOGI MAJU 40150 KLANG SELANGOR

## MAKLUMAT BAYARAN AKHIR

Amaun : RM3,456.75

Tarikh  : 25.09.2024

| Ringkasan Bil Anda:   |              |
|-----------------------|--------------|
| Baki Terdahulu        | RM150.25     |
| Caj Semasa            | RM3,306.50   |
| Pelarasan Penggenapan | RM0.00       |
| Jumlah Bil Anda       | RM3,456.75   |

TARIKH BIL

20.09.2024

TEMPOH BIL

20.08.2024 - 19.09.2024 (30 Hari)

NO. INVOIS

000987654321

Ref-1:

TECH123

Biller Code:

5454""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="no_akaun",
                    extraction_text="210987654321",
                    attributes={"account_number": "210987654321"}
                ),
                lx.data.Extraction(
                    extraction_class="sumber_bil",
                    extraction_text="TECH SOLUTIONS SDN BHD",
                    attributes={"bill_source": "TECH SOLUTIONS SDN BHD", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class="alamat_pos",
                    extraction_text="LOT 9876, JALAN TEKNOLOGI MAJU 40150 KLANG SELANGOR",
                    attributes={"postal_address": "LOT 9876, JALAN TEKNOLOGI MAJU 40150 KLANG SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_bayaran_bagi_tempoh",
                    extraction_text="RM3,456.75",
                    attributes={"payment_amount_for_period": 3456.75, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_akhir_jelaskan_tunggakan",
                    extraction_text="25.09.2024",
                    attributes={"final_arrears_settlement_date": "25.09.2024", "iso_date": "2024-09-25"}
                ),
                lx.data.Extraction(
                    extraction_class="baki_terdahulu",
                    extraction_text="RM150.25",
                    attributes={"previous_balance": 150.25, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="RM3,306.50",
                    attributes={"current_charges": 3306.50, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="pelarasan_penggenapan",
                    extraction_text="RM0.00",
                    attributes={"rounding_adjustment": 0.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="jumlah_bil",
                    extraction_text="RM3,456.75",
                    attributes={"total_bill": 3456.75, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_bil",
                    extraction_text="20.09.2024",
                    attributes={"bill_date": "20.09.2024", "iso_date": "2024-09-20"}
                ),
                lx.data.Extraction(
                    extraction_class="tempoh_bil",
                    extraction_text="20.08.2024 - 19.09.2024 (30 Hari)",
                    attributes={"bill_period": "20.08.2024 - 19.09.2024", "start_date": "2024-08-20", "end_date": "2024-09-19"}
                ),
                lx.data.Extraction(
                    extraction_class="no_invois",
                    extraction_text="000987654321",
                    attributes={"invoice_number": "000987654321"}
                ),
                lx.data.Extraction(
                    extraction_class="ref_1",
                    extraction_text="TECH123",
                    attributes={"reference_1": "TECH123", "type": "customer_reference"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
            ]
        ),
        lx.data.ExampleData(
            text="""## Bil Elektrik Anda

## ALAMAT POS

GLOBAL INDUSTRIES SDN BHD

LOT 55555, JALAN PERINDUSTRIAN UTAMA

SUBANG JAYA 47500 SELANGOR

Jumlah Bil Anda (RM)

45,678.90

Sila bayar sebelum

30 September 2024

## NO. AKAUN

555444333222

BAYARAN BAGI TEMPOH 01.09.2024 - 30.09.2024

RM1,234.56

Biller Code:

5454

Ref-1:

555444333222

| Ringkasan Bil Anda:     |              |
|-------------------------|--------------|
| Baki Terdahulu          | RM500.00     |
| Caj Semasa NEM          | RM45,178.90  |
| Pelarasan Penggenapan   | RM0.00       |
| Amaun RM Tunggakan      | RM0.00       |

TARIKH BIL

25.09.2024

TEMPOH BIL

01.09.2024 - 30.09.2024 (30 Hari)

NO. INVOIS

000555444333

DEPOSIT SEKURITI

RM200,000.00

MAKLUMAT BAYARAN AKHIR

Tarikh : 10.10.2024""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="sumber_bil",
                    extraction_text="GLOBAL INDUSTRIES SDN BHD",
                    attributes={"bill_source": "GLOBAL INDUSTRIES SDN BHD", "type": "customer_company"}
                ),
                lx.data.Extraction(
                    extraction_class="alamat_pos",
                    extraction_text="LOT 55555, JALAN PERINDUSTRIAN UTAMA\n\nSUBANG JAYA 47500 SELANGOR",
                    attributes={"postal_address": "LOT 55555, JALAN PERINDUSTRIAN UTAMA, SUBANG JAYA 47500 SELANGOR"}
                ),
                lx.data.Extraction(
                    extraction_class="jumlah_bil",
                    extraction_text="45,678.90",
                    attributes={"total_bill": 45678.90, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="bayar_sebelum",
                    extraction_text="30 September 2024",
                    attributes={"pay_before": "30 September 2024", "iso_date": "2024-09-30"}
                ),
                lx.data.Extraction(
                    extraction_class="no_akaun",
                    extraction_text="555444333222",
                    attributes={"account_number": "555444333222"}
                ),
                lx.data.Extraction(
                    extraction_class="bayaran_bagi_tempoh",
                    extraction_text="01.09.2024 - 30.09.2024",
                    attributes={"payment_for_period": "01.09.2024 - 30.09.2024", "start_date": "2024-09-01", "end_date": "2024-09-30"}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_bayaran_bagi_tempoh",
                    extraction_text="RM1,234.56",
                    attributes={"payment_amount_for_period": 1234.56, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="biller_code",
                    extraction_text="5454",
                    attributes={"biller_code": "5454"}
                ),
                lx.data.Extraction(
                    extraction_class="ref_1",
                    extraction_text="555444333222",
                    attributes={"reference_1": "555444333222", "type": "account_reference"}
                ),
                lx.data.Extraction(
                    extraction_class="baki_terdahulu",
                    extraction_text="RM500.00",
                    attributes={"previous_balance": 500.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="caj_semasa",
                    extraction_text="RM45,178.90",
                    attributes={"current_charges": 45178.90, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="pelarasan_penggenapan",
                    extraction_text="RM0.00",
                    attributes={"rounding_adjustment": 0.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="amaun_rm_tunggakan",
                    extraction_text="RM0.00",
                    attributes={"arrears_amount": 0.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_bil",
                    extraction_text="25.09.2024",
                    attributes={"bill_date": "25.09.2024", "iso_date": "2024-09-25"}
                ),
                lx.data.Extraction(
                    extraction_class="tempoh_bil",
                    extraction_text="01.09.2024 - 30.09.2024 (30 Hari)",
                    attributes={"bill_period": "01.09.2024 - 30.09.2024", "start_date": "2024-09-01", "end_date": "2024-09-30"}
                ),
                lx.data.Extraction(
                    extraction_class="no_invois",
                    extraction_text="000555444333",
                    attributes={"invoice_number": "000555444333"}
                ),
                lx.data.Extraction(
                    extraction_class="deposit_sekuriti",
                    extraction_text="RM200,000.00",
                    attributes={"security_deposit": 200000.00, "currency": "MYR"}
                ),
                lx.data.Extraction(
                    extraction_class="tarikh_akhir_jelaskan_tunggakan",
                    extraction_text="10.10.2024",
                    attributes={"final_arrears_settlement_date": "10.10.2024", "iso_date": "2024-10-10"}
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
        max_workers=20,

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
