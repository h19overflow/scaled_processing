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
    Extract the following invoice information comprehensively. For each date, provide both the original text and ISO 8601 (YYYY-MM-DD). Normalize payment terms and due periods as integer days where possible. Always include "USD" currency for all monetary amounts.
    
    COMPANY & CONTACT INFORMATION:
    - Vendor details (name, address, phone, fax, email, website, tax IDs, DUNS number)
    - Customer/Bill-to details (name, address, contact info, department)
    - Ship-to details if different from bill-to
    
    PEOPLE & ROLES:
    - Contact persons with roles (account managers, project managers, supervisors)
    - Sales representatives and territory information
    
    INVOICE IDENTIFIERS:
    - Invoice number and date
    - Purchase order numbers and contract references
    - Project codes, quote references, customer account numbers
    
    FINANCIAL DETAILS:
    - Line items with descriptions, quantities, unit prices, and totals (all with USD currency)
    - Tax amounts, subtotals, and final totals (all with USD currency)
    - Discounts and their percentages/amounts
    - Shipping and handling costs
    
    PAYMENT & REMITTANCE:
    - Payment terms, due dates, and payment methods
    - Banking details (routing numbers, account numbers, wire transfer info)
    - Remittance addresses and instructions
    
    BUSINESS TERMS & COMPLIANCE:
    - Service periods and warranty terms
    - Contract references and legal clauses
    - Compliance notes and policy references
    
    DOCUMENT STRUCTURE:
    - Section headers (BILL TO, SHIP TO, REMIT TO, etc.)
    - Notes and special instructions
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
                    extraction_class="customer",
                    extraction_text="ABC Company",
                    attributes={"type": "bill_to", "company_name": "ABC Company"}
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
        ),
        lx.data.ExampleData(
            text="TechServices LLC, Tax ID: 12-3456789. Bill To: GlobalCorp Inc, IT Dept. Invoice #INV-2024-0156 dated June 10, 2024. Consulting: 40hrs x $85 = $3,400. Tax: $272. Total: $3,672. Net 30 days.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="vendor",
                    extraction_text="TechServices LLC",
                    attributes={"company_name": "TechServices LLC", "tax_id": "12-3456789"}
                ),
                lx.data.Extraction(
                    extraction_class="customer",
                    extraction_text="GlobalCorp Inc",
                    attributes={"company_name": "GlobalCorp Inc", "department": "IT Dept"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="INV-2024-0156",
                    attributes={"type": "invoice_id"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="June 10, 2024",
                    attributes={"type": "issue_date", "iso_date": "2024-06-10"}
                ),
                lx.data.Extraction(
                    extraction_class="line_item",
                    extraction_text="Consulting: 40hrs x $85 = $3,400",
                    attributes={
                        "description": "Consulting",
                        "quantity": 40.00,
                        "unit": "Hours",
                        "unit_price": 85.00,
                        "total": 3400.00,
                        "currency": "USD"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="tax",
                    extraction_text="$272",
                    attributes={"amount": 272.00, "currency": "USD", "type": "tax"}
                ),
                lx.data.Extraction(
                    extraction_class="total_amount",
                    extraction_text="$3,672",
                    attributes={"amount": 3672.00, "currency": "USD"}
                ),
                lx.data.Extraction(
                    extraction_class="payment_terms",
                    extraction_text="Net 30 days",
                    attributes={"due_period_text": "Net 30 days", "due_period_days": 30}
                ),
            ]
        ),
        lx.data.ExampleData(
            text="ACME LLC, DUNS: 987654321. BILL TO: MegaCorp, Attn: Robert Chen CFO. Invoice ACM-2024-001, Dec 5, 2024. Consulting 120hrs x $150 = $18,000. Tax: $1,575. Total: $19,575. REMIT TO: Chase Bank 021000021.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="vendor",
                    extraction_text="ACME LLC",
                    attributes={"company_name": "ACME LLC", "duns_number": "987654321"}
                ),
                lx.data.Extraction(
                    extraction_class="section_header",
                    extraction_text="BILL TO:",
                    attributes={"section_type": "billing_address"}
                ),
                lx.data.Extraction(
                    extraction_class="customer",
                    extraction_text="MegaCorp",
                    attributes={"company_name": "MegaCorp"}
                ),
                lx.data.Extraction(
                    extraction_class="contact_person",
                    extraction_text="Robert Chen",
                    attributes={"name": "Robert Chen", "role": "CFO", "type": "customer_contact"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="ACM-2024-001",
                    attributes={"type": "invoice_id"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="Dec 5, 2024",
                    attributes={"type": "issue_date", "iso_date": "2024-12-05"}
                ),
                lx.data.Extraction(
                    extraction_class="line_item",
                    extraction_text="Consulting 120hrs x $150 = $18,000",
                    attributes={
                        "description": "Consulting",
                        "quantity": 120.00,
                        "unit": "Hours",
                        "unit_price": 150.00,
                        "total": 18000.00,
                        "currency": "USD"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="tax",
                    extraction_text="$1,575",
                    attributes={"amount": 1575.00, "currency": "USD", "type": "tax"}
                ),
                lx.data.Extraction(
                    extraction_class="total_amount",
                    extraction_text="$19,575",
                    attributes={"amount": 19575.00, "currency": "USD"}
                ),
                lx.data.Extraction(
                    extraction_class="section_header",
                    extraction_text="REMIT TO:",
                    attributes={"section_type": "remittance_address"}
                ),
                lx.data.Extraction(
                    extraction_class="banking_details",
                    extraction_text="Chase Bank 021000021",
                    attributes={"bank_name": "Chase Bank", "routing_number": "021000021", "type": "wire_transfer"}
                )
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
