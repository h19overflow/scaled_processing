import textwrap
import langextract as lx
from typing import Tuple, List
from dotenv import load_dotenv
load_dotenv()

def route_classification(classification: str) -> Tuple[str, List[lx.data.ExampleData]]:
    """Routes classification to appropriate extraction function"""
    if classification == "contract":
        return contract_extraction()
    elif classification == "invoice":
        return invoice_extraction()
    elif classification == "legal":
        return legal_extraction()
    elif classification == 'report':
        return report_extraction()
    else:
        return "Unknown classification", []

def contract_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract the following contract information.
    For all date fields, output both the original string and the normalized ISO 8601 format (YYYY-MM-DD) if possible.
    For durations (payment terms, periods), output the value in both text and as an integer number of days.
    - Party names and roles
    - Contract dates (start, end, signing)
    - Key terms and conditions
    - Payment terms and amounts
    - Termination clauses (with date fields normalized)
    """).strip()

    examples = [
        lx.data.ExampleData(
            text=(
                "This Service Agreement is entered into on January 15, 2024, between TechCorp Inc. (Client) "
                "and DataSolutions LLC (Provider). The agreement period is from February 1, 2024 to December 31, 2024. "
                "Payment of $50,000 due within 30 days of invoice date. Can be terminated after 90 days."
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="party",
                    extraction_text="TechCorp Inc.",
                    attributes={"role": "Client"}
                ),
                lx.data.Extraction(
                    extraction_class="party",
                    extraction_text="DataSolutions LLC",
                    attributes={"role": "Provider"}
                ),
                lx.data.Extraction(
                    extraction_class="date",
                    extraction_text="January 15, 2024",
                    attributes={"type": "agreement_signed", "iso_date": "2024-01-15"}
                ),
                lx.data.Extraction(
                    extraction_class="date",
                    extraction_text="February 1, 2024",
                    attributes={"type": "start_date", "iso_date": "2024-02-01"}
                ),
                lx.data.Extraction(
                    extraction_class="date",
                    extraction_text="December 31, 2024",
                    attributes={"type": "end_date", "iso_date": "2024-12-31"}
                ),
                lx.data.Extraction(
                    extraction_class="payment_terms",
                    extraction_text="30 days",
                    attributes={"due_period_text": "30 days", "due_period_days": 30}
                ),
                lx.data.Extraction(
                    extraction_class="termination_clause",
                    extraction_text="Can be terminated after 90 days",
                    attributes={"termination_period_text": "90 days", "termination_period_days": 90}
                ),
            ]
        )
    ]
    return extraction_prompt, examples

def invoice_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract the following invoice information. For each date, provide both the original text and ISO 8601 (YYYY-MM-DD). Normalize payment terms and due periods as integer days where possible.
    - Invoice number and date
    - Vendor and customer details
    - Line items (quantities and prices)
    - Tax amounts and totals
    - Payment terms and due date
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="Invoice #INV-2024-001 dated March 15, 2024. Bill To: ABC Company. Due: April 14, 2024. Terms: Net 30.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="INV-2024-001",
                    attributes={"type": "invoice_id"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="March 15, 2024",
                    attributes={"type": "issue_date", "iso_date": "2024-03-15"}
                ),
                lx.data.Extraction(
                    extraction_class="due_date",
                    extraction_text="April 14, 2024",
                    attributes={"iso_date": "2024-04-14"}
                ),
                lx.data.Extraction(
                    extraction_class="payment_terms",
                    extraction_text="Net 30",
                    attributes={"due_period_text": "Net 30", "due_period_days": 30}
                ),
            ]
        )
    ]
    return extraction_prompt, examples

def legal_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract the following legal information. For all dates (e.g., hearings, filings), output the original and the normalized ISO 8601 (YYYY-MM-DD) format.
    For deadlines/durations, provide both the string and number of days.
    - Case numbers and court details
    - Legal entities and parties involved
    - Key dates and deadlines (filed, hearing, judgment)
    - Legal citations and references
    - Judgments and decisions
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="Case No. 2024-CV-12345. Hearing on May 15, 2024. Summary Judgment filed April 10, 2024; response due in 21 days.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="case_number",
                    extraction_text="2024-CV-12345",
                    attributes={"type": "civil_case"}
                ),
                lx.data.Extraction(
                    extraction_class="hearing_date",
                    extraction_text="May 15, 2024",
                    attributes={"iso_date": "2024-05-15"}
                ),
                lx.data.Extraction(
                    extraction_class="filed_date",
                    extraction_text="April 10, 2024",
                    attributes={"iso_date": "2024-04-10"}
                ),
                lx.data.Extraction(
                    extraction_class="response_deadline",
                    extraction_text="21 days",
                    attributes={"deadline_text": "21 days", "deadline_days": 21}
                ),
            ]
        )
    ]
    return extraction_prompt, examples

def report_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    extraction_prompt = textwrap.dedent("""
    Extract the following report information. For all report dates and periods, output both the original text and the normalized ISO 8601 (YYYY-MM-DD) or precise period info suitable for database ingestion.
    - Report title and date (with normalized date)
    - Author and organization
    - Key findings and conclusions
    - Data points and statistics
    - Recommendations and next steps
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="Q3 2024 Financial Report prepared by Finance Department on October 1, 2024.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="report_title",
                    extraction_text="Q3 2024 Financial Report",
                    attributes={"period": "Q3 2024", "period_start": "2024-07-01", "period_end": "2024-09-30"}
                ),
                lx.data.Extraction(
                    extraction_class="report_date",
                    extraction_text="October 1, 2024",
                    attributes={"type": "preparation_date", "iso_date": "2024-10-01"}
                ),
                lx.data.Extraction(
                    extraction_class="author",
                    extraction_text="Finance Department",
                    attributes={"organization": "Finance Department"}
                ),
                lx.data.Extraction(
                    extraction_class="key_findings",
                    extraction_text="Revenue increased by 15% compared to Q2 2024, reaching $2.5M.",
                    attributes={"period": "Q2 2024", "period_start": "2023-10-01", "period_end": "2023-12-31"}
                )
            ]
        )
    ]
    return extraction_prompt, examples

def process_document(text: str, doc_type: str):
    """Process document using langextract with appropriate routing and temporal normalization"""
    prompt, examples = route_classification(doc_type)
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-2.0-flash",
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
