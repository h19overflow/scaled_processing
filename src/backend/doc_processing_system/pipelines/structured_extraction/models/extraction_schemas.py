from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ExtractionAttributes(BaseModel):
    """Base attributes for extraction results"""
    pass


class PostalAddressAttributes(ExtractionAttributes):
    """Attributes for postal address extraction"""
    postal_address: str = Field(description="Full formatted postal address")


class IssueDateAttributes(ExtractionAttributes):
    """Attributes for issue date extraction"""
    issue_date: str = Field(description="Issue date in DD.MM.YYYY format")
    iso_date: str = Field(description="Issue date in ISO format (YYYY-MM-DD)")


class InvoiceNumberAttributes(ExtractionAttributes):
    """Attributes for invoice number extraction"""
    invoice_number: str = Field(description="Invoice/bill number")


class AmountDueAttributes(ExtractionAttributes):
    """Attributes for amount due extraction"""
    amount_due: float = Field(description="Amount due as numeric value")
    currency: str = Field(default="MYR", description="Currency code")
    type: str = Field(default="final_payable", description="Type of amount")


class DueDateAttributes(ExtractionAttributes):
    """Attributes for due date extraction"""
    due_date: str = Field(description="Due date in original format")
    iso_date: str = Field(description="Due date in ISO format (YYYY-MM-DD)")


class BillerCodeAttributes(ExtractionAttributes):
    """Attributes for biller code extraction"""
    biller_code: str = Field(description="Biller payment code")


class ExtractionResult(BaseModel):
    """Single extraction result compatible with database storage"""
    extraction_class: str = Field(description="Type of extraction (postal_address, invoice_number, etc.)")
    extraction_text: str = Field(description="Original text that was extracted")
    attributes: Dict[str, Any] = Field(description="Structured attributes for the extraction")


class BillExtractionResult(BaseModel):
    """Complete bill extraction result with all fields"""
    postal_address: Optional[str] = Field(None, description="Customer postal address")
    issue_date: Optional[str] = Field(None, description="Bill issue date")
    invoice_number: Optional[str] = Field(None, description="Invoice/bill number")
    amount_due: Optional[float] = Field(None, description="Amount due as numeric value")
    due_date: Optional[str] = Field(None, description="Payment due date")
    biller_code: Optional[str] = Field(None, description="Biller payment code")
    
    # Additional extracted fields for JSONB storage
    account_number: Optional[str] = Field(None, description="Account number")
    bill_period: Optional[str] = Field(None, description="Billing period")
    previous_balance: Optional[float] = Field(None, description="Previous balance amount")
    current_charges: Optional[float] = Field(None, description="Current charges amount")
    
    def to_extraction_list(self) -> List[Dict[str, Any]]:
        """Convert to list format compatible with database storage"""
        extractions = []
        
        if self.postal_address:
            extractions.append({
                "extraction_class": "postal_address",
                "extraction_text": self.postal_address,
                "attributes": {"postal_address": self.postal_address}
            })
        
        if self.issue_date:
            iso_date = self._parse_date_to_iso(self.issue_date)
            extractions.append({
                "extraction_class": "issue_date", 
                "extraction_text": self.issue_date,
                "attributes": {"issue_date": self.issue_date, "iso_date": iso_date}
            })
        
        if self.invoice_number:
            extractions.append({
                "extraction_class": "invoice_number",
                "extraction_text": self.invoice_number,
                "attributes": {"invoice_number": self.invoice_number}
            })
        
        if self.amount_due is not None:
            extractions.append({
                "extraction_class": "amount_due",
                "extraction_text": f"JUMLAH BIL ANDA RM{self.amount_due:,.2f}",
                "attributes": {"amount_due": self.amount_due, "currency": "MYR", "type": "final_payable"}
            })
        
        if self.due_date:
            iso_date = self._parse_date_to_iso(self.due_date)
            extractions.append({
                "extraction_class": "due_date",
                "extraction_text": self.due_date,
                "attributes": {"due_date": self.due_date, "iso_date": iso_date}
            })
        
        if self.biller_code:
            extractions.append({
                "extraction_class": "biller_code",
                "extraction_text": self.biller_code,
                "attributes": {"biller_code": self.biller_code}
            })
        
        # Add additional fields to JSONB storage
        additional_fields = {}
        if self.account_number:
            additional_fields["account_number"] = {"account_number": self.account_number}
        if self.bill_period:
            additional_fields["bill_period"] = {"bill_period": self.bill_period}
        if self.previous_balance is not None:
            additional_fields["previous_balance"] = {"previous_balance": self.previous_balance, "currency": "MYR"}
        if self.current_charges is not None:
            additional_fields["current_charges"] = {"current_charges": self.current_charges, "currency": "MYR"}
        
        for field_name, attributes in additional_fields.items():
            extractions.append({
                "extraction_class": field_name,
                "extraction_text": str(list(attributes.values())[0]),
                "attributes": attributes
            })
        
        return extractions
    
    def _parse_date_to_iso(self, date_str: str) -> str:
        """Parse Malaysian date format to ISO format"""
        if not date_str:
            return ""
        
        try:
            # Format 1: DD.MM.YYYY (e.g., "01.08.2025")
            if '.' in date_str and len(date_str.split('.')) == 3:
                day, month, year = date_str.split('.')
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # Format 2: DD MMM YYYY (e.g., "31 Ogos 2025")
            elif ' ' in date_str:
                month_map = {
                    'Jan': '01', 'Feb': '02', 'Mac': '03', 'Apr': '04', 'Mei': '05', 'Jun': '06',
                    'Jul': '07', 'Ogos': '08', 'Sep': '09', 'Okt': '10', 'Nov': '11', 'Dis': '12',
                    'January': '01', 'February': '02', 'March': '03', 'April': '04', 'May': '05', 'June': '06',
                    'July': '07', 'August': '08', 'September': '09', 'October': '10', 'November': '11', 'December': '12'
                }
                
                parts = date_str.strip().split()
                if len(parts) == 3:
                    day, month_str, year = parts
                    month = month_map.get(month_str, '01')
                    return f"{year}-{month}-{day.zfill(2)}"
        except (ValueError, IndexError):
            pass
        
        return date_str

