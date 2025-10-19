
from pydantic_ai import Agent
from ..models.extraction_schemas import BillExtractionResult
from dotenv import load_dotenv
load_dotenv()
# Create PydanticAI agent for bill extraction
extraction_agent = Agent(
    'gemini-2.0-flash',
    result_type=BillExtractionResult,
    system_prompt="""You are an expert at extracting structured information from Malaysian utility bills.

Extract the following information from utility bills:
- postal_address: Customer postal address (combine multiple lines into single address)
- issue_date: Bill issue date (TARIKH BIL) in DD.MM.YYYY format
- invoice_number: Invoice number (NO. INVOIS)
- amount_due: Final amount due (Caj Semasa NEM RM104,965.38 or Caj Semasa RM104,965.38") as numeric value only
- due_date: Payment due date (from "Sila bayar sebelum: [date]") 
- biller_code: Biller code for payment
- account_number: Account number (NO. AKAUN) if available
- bill_period: Billing period if mentioned
- previous_balance: Previous balance amount if mentioned
- current_charges: Current charges amount if mentioned

Important rules:
1. Extract each field type only ONCE - choose the primary/main value if multiple exist
2. For amount_due, extract only the numeric value from "JUMLAH BIL ANDA RM[amount]"
3. Fields might appear in Malay language
4. Return null/None for fields that are not found
5. For dates, preserve the original format but be consistent
6. For postal addresses, combine multiple lines into a single formatted address

Example patterns:
- Due date: "Sila bayar sebelum 31 Ogos 2025" → extract "31 Ogos 2025"
- Amount: "JUMLAH BIL ANDA RM170,358.25" → extract 170358.25 (numeric only)
- Date: "TARIKH BIL: 01.08.2025" → extract "01.08.2025"
""")