import textwrap
import langextract as lx
from typing import Tuple, List


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
        # Default fallback
        return "Unknown classification", []


def contract_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    """Extract contract-specific information"""
    extraction_prompt = textwrap.dedent("""
    Extract the following contract information:
    - Party names and roles
    - Contract dates (start, end, signing)
    - Key terms and conditions
    - Payment terms and amounts
    - Termination clauses
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="This Service Agreement is entered into on January 15, 2024, between TechCorp Inc. (Client) and DataSolutions LLC (Provider). Payment of $50,000 due within 30 days of invoice date.",
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
                    attributes={"type": "agreement_date"}
                ),
                lx.data.Extraction(
                    extraction_class="payment_terms",
                    extraction_text="Payment of $50,000 due within 30 days",
                    attributes={"amount": "$50,000", "due_period": "30 days"}
                )
            ]
        )
    ]

    return extraction_prompt, examples


def invoice_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    """Extract invoice-specific information"""
    extraction_prompt = textwrap.dedent("""
    Extract the following invoice information:
    - Invoice number and date
    - Vendor and customer details
    - Line items with quantities and prices
    - Tax amounts and total due
    - Payment terms and due date
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="Invoice #INV-2024-001 dated March 15, 2024. Bill To: ABC Company. Item: Software License, Quantity: 5, Unit Price: $100.00, Total: $500.00. Tax: $50.00. Grand Total: $550.00",
            extractions=[
                lx.data.Extraction(
                    extraction_class="invoice_number",
                    extraction_text="INV-2024-001",
                    attributes={"type": "invoice_id"}
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="March 15, 2024",
                    attributes={"type": "issue_date"}
                ),
                lx.data.Extraction(
                    extraction_class="customer",
                    extraction_text="ABC Company",
                    attributes={"role": "bill_to"}
                ),
                lx.data.Extraction(
                    extraction_class="line_item",
                    extraction_text="Software License, Quantity: 5, Unit Price: $100.00",
                    attributes={"quantity": "5", "unit_price": "$100.00", "item": "Software License"}
                ),
                lx.data.Extraction(
                    extraction_class="total",
                    extraction_text="Grand Total: $550.00",
                    attributes={"amount": "$550.00", "type": "grand_total"}
                )
            ]
        )
    ]

    return extraction_prompt, examples


def legal_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    """Extract legal document information"""
    extraction_prompt = textwrap.dedent("""
    Extract the following legal information:
    - Case numbers and court details
    - Legal entities and parties involved
    - Key dates and deadlines
    - Legal citations and references
    - Judgments and decisions
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="Case No. 2024-CV-12345 filed in the Superior Court of California. Plaintiff John Doe vs. Defendant Jane Smith. Motion for Summary Judgment filed on April 10, 2024. Hearing scheduled for May 15, 2024.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="case_number",
                    extraction_text="2024-CV-12345",
                    attributes={"type": "civil_case"}
                ),
                lx.data.Extraction(
                    extraction_class="court",
                    extraction_text="Superior Court of California",
                    attributes={"jurisdiction": "California", "level": "Superior"}
                ),
                lx.data.Extraction(
                    extraction_class="party",
                    extraction_text="John Doe",
                    attributes={"role": "Plaintiff"}
                ),
                lx.data.Extraction(
                    extraction_class="party",
                    extraction_text="Jane Smith",
                    attributes={"role": "Defendant"}
                ),
                lx.data.Extraction(
                    extraction_class="legal_action",
                    extraction_text="Motion for Summary Judgment",
                    attributes={"filed_date": "April 10, 2024", "hearing_date": "May 15, 2024"}
                )
            ]
        )
    ]

    return extraction_prompt, examples


def report_extraction() -> Tuple[str, List[lx.data.ExampleData]]:
    """Extract report-specific information"""
    extraction_prompt = textwrap.dedent("""
    Extract the following report information:
    - Report title and date
    - Author and organization
    - Key findings and conclusions
    - Data points and statistics
    - Recommendations and next steps
    """).strip()

    examples = [
        lx.data.ExampleData(
            text="Q3 2024 Financial Report prepared by Finance Department on October 1, 2024. Key Finding: Revenue increased by 15% compared to Q2 2024, reaching $2.5M. Recommendation: Increase marketing budget by 20% for Q4 to sustain growth momentum.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="report_title",
                    extraction_text="Q3 2024 Financial Report",
                    attributes={"period": "Q3 2024", "type": "financial"}
                ),
                lx.data.Extraction(
                    extraction_class="author",
                    extraction_text="Finance Department",
                    attributes={"role": "department"}
                ),
                lx.data.Extraction(
                    extraction_class="report_date",
                    extraction_text="October 1, 2024",
                    attributes={"type": "preparation_date"}
                ),
                lx.data.Extraction(
                    extraction_class="finding",
                    extraction_text="Revenue increased by 15% compared to Q2 2024, reaching $2.5M",
                    attributes={"metric": "revenue", "change": "15% increase", "amount": "$2.5M"}
                ),
                lx.data.Extraction(
                    extraction_class="recommendation",
                    extraction_text="Increase marketing budget by 20% for Q4",
                    attributes={"action": "budget_increase", "department": "marketing", "percentage": "20%"}
                )
            ]
        )
    ]

    return extraction_prompt, examples


# Usage example:
def process_document(text: str, doc_type: str):
    """Process document using langextract with appropriate routing"""
    prompt, examples = route_classification(doc_type)

    # Use the prompt and examples with langextract
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-2.5-flash",
    )
    return result
