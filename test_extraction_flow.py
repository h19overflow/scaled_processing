"""
Simple test script for the structured extraction flow.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.doc_processing_system.pipelines.structured_extraction.models.state import PipelineState
from src.backend.doc_processing_system.pipelines.structured_extraction.core.prefect_tasks import structured_extraction_flow

# Very complex enterprise invoice with multiple challenging scenarios
TEST_TEXT = """
CONSOLIDATED TECHNOLOGY SERVICES LLC
Global Enterprise Solutions Division
Corporate Headquarters: 1500 Technology Boulevard, Suite 2800
Silicon Valley, CA 94025-3456
Secondary Office: 200 Innovation Center, Austin, TX 78701
Phone: +1 (650) 555-0199 | Fax: +1 (650) 555-0198
Email: billing@ctsllc.com | Website: www.ctsllc.com
Federal Tax ID: 94-1234567 | State Tax ID: CA-987654321
DUNS Number: 123456789

═══════════════════════════════════════════════════════════════════════════════
                                    INVOICE
═══════════════════════════════════════════════════════════════════════════════

BILL TO:                                    SHIP TO:
GlobalMega Corporation                      GlobalMega Corporation - West Coast Facility
Accounts Payable Department                 c/o Sarah Mitchell, IT Operations Manager
Attn: Jennifer Rodriguez, AP Supervisor     Building 7, Data Center Operations
Financial Operations Center                 2800 Enterprise Way
1250 Corporate Drive, Floor 15             Mountain View, CA 94040
New York, NY 10018-4578                   Phone: (415) 555-7890
Phone: (212) 555-6789 ext. 4567
Email: ap@globalmega.com

Invoice Number: CTS-2024-Q3-08759          Customer Account: GM-ENT-003456
Invoice Date: September 15, 2024           Sales Representative: Michael Chen
Due Date: October 15, 2024 (Net 30)        Territory: West Coast Enterprise
PO Number: GM-PO-2024-IT-789123           Contract Reference: MSA-2024-GM-001
Project Code: PROJ-INFRAMOD-2024-Q3        Payment Terms: Net 30 Days
Quote Reference: QTE-2024-789123           Currency: USD

REMIT TO:                                   QUESTIONS? CONTACT:
CTS Collections Department                  Michael Chen - Account Manager
P.O. Box 987654                            Direct: (650) 555-0145
San Francisco, CA 94111-0001               Mobile: (650) 555-0146
Wire Transfer: Wells Fargo                  Email: mchen@ctsllc.com
Account: 1234567890                         
Routing: 121000248                         Jennifer Park - Project Manager
                                           Direct: (650) 555-0147
                                           Email: jpark@ctsllc.com

═══════════════════════════════════════════════════════════════════════════════

SERVICE PERIOD: July 1, 2024 - September 30, 2024 (Q3 2024)

DESCRIPTION                                  QTY    UNIT    RATE        EXTENDED
────────────────────────────────────────────────────────────────────────────────
INFRASTRUCTURE SERVICES:
  Cloud Infrastructure Management           3 mo   Monthly  $12,500.00   $37,500.00
  24/7 Network Operations Center Support    2,190 hrs Hourly   $95.00   $208,050.00
  Database Administration (Oracle/MySQL)    480 hrs Hourly   $145.00    $69,600.00
  Security Monitoring & Incident Response   3 mo   Monthly  $8,750.00   $26,250.00
  
PROFESSIONAL SERVICES:
  Senior Solutions Architect (Mark Thompson) 160 hrs Hourly   $185.00    $29,600.00
  DevOps Engineer (Level III)               240 hrs Hourly   $135.00    $32,400.00
  Cloud Migration Specialist                120 hrs Hourly   $165.00    $19,800.00
  Technical Documentation & Training        80 hrs  Hourly   $125.00    $10,000.00

SOFTWARE LICENSES & SUBSCRIPTIONS:
  Enterprise Monitoring Suite (Datadog Pro) 500 users Monthly  $15.00     $22,500.00
  Security Software (CrowdStrike Falcon)    300 endpoints Monthly $8.50    $7,650.00
  Backup Solution (Veeam Enterprise Plus)   50 TB   Monthly  $85.00     $12,750.00
  API Management Platform (Kong Enterprise) 1 cluster Monthly $2,850.00   $8,550.00

HARDWARE & EQUIPMENT:
  Dell PowerEdge R750 Servers (2U Rack)     4 units Each    $8,500.00   $34,000.00
  Cisco Catalyst 9300 Switch Stack          2 units Each    $12,750.00  $25,500.00
  VMware vSphere Enterprise Plus Licenses   8 processors Each $4,245.00  $33,960.00
  SAN Storage Array (Pure Storage FA-C20)   1 unit  Each    $95,000.00  $95,000.00

TRAVEL & EXPENSES: (Pre-approved per MSA Section 4.2)
  On-site Implementation (Week of Aug 12-16) 1 trip  Fixed   $4,250.00   $4,250.00
  Senior Architect Travel - NY to CA (x3)    3 trips Each    $1,850.00   $5,550.00
  Training Workshop Delivery (2 days)        1 event Fixed   $2,750.00   $2,750.00
  
ADDITIONAL CHARGES:
  After-hours Emergency Support (8 incidents) 8 calls Each   $485.00     $3,880.00
  Rush Hardware Procurement Fee              1 fee   Fixed   $1,250.00   $1,250.00
  Custom Integration Development             60 hrs  Hourly  $195.00     $11,700.00
  Third-party Vendor Coordination           24 hrs  Hourly  $115.00     $2,760.00

────────────────────────────────────────────────────────────────────────────────
                                                      SUBTOTAL:     $705,540.00

DISCOUNTS:
  Volume Discount (>$500K annual spend) -5.0%                        ($35,277.00)
  Early Payment Discount Available: 2% if paid within 10 days        ($13,405.26)
  
                                               SUBTOTAL AFTER DISC:   $656,857.74

TAXES:
  California State Sales Tax (8.25%)                                  $54,190.76
  Santa Clara County Tax (1.75%)                                      $11,495.01
  Technology Service Fee (0.5%)                                       $3,284.29
  
                                                    TOTAL TAXES:      $68,970.06

SHIPPING & HANDLING:
  Standard Freight (Hardware Delivery)                                $2,850.00
  White Glove Setup Service                                           $4,500.00
  Expedited Shipping Surcharge                                        $750.00
  
                                              TOTAL SHIPPING:         $8,100.00

════════════════════════════════════════════════════════════════════════════════
                                          TOTAL AMOUNT DUE:      $733,927.80
════════════════════════════════════════════════════════════════════════════════

PAYMENT TERMS: Net 30 Days from Invoice Date
EARLY PAYMENT: 2% discount if paid within 10 business days
LATE PAYMENT: 1.5% monthly service charge on overdue amounts
PAYMENT METHODS: ACH Transfer (preferred), Wire Transfer, Company Check

REMITTANCE ADVICE: Please include Invoice Number CTS-2024-Q3-08759 with payment

NOTES:
• All services performed under Master Service Agreement MSA-2024-GM-001
• Hardware warranty begins upon delivery confirmation
• Software licenses are annual subscriptions (auto-renewal unless cancelled 60 days prior)
• This invoice includes charges for Q3 2024 service period
• Travel expenses comply with customer's pre-approved travel policy
• Emergency support charges per Section 7.3 of service agreement

Questions regarding this invoice should be directed to Accounts Receivable:
Phone: (650) 555-0199 ext. 2400 | Email: ar@ctsllc.com
"""

def main():
    print("🚀 Testing Structured Extraction Flow")
    print("=" * 50)
    
    # Create initial state
    initial_state = PipelineState(
        document_text=TEST_TEXT,
        document_id="test_001"
    )
    
    print(f"📄 Document ID: {initial_state.document_id}")
    print(f"📝 Document Preview: {initial_state.document_text[:80]}...")
    
    try:
        # Run the flow
        result = structured_extraction_flow(initial_state)
        
        print(f"\n✅ Flow Status: {result.status}")
        print(f"🏷️  Classification: {getattr(result, 'classification', 'N/A')}")
        print(f"🎯 Confidence: {getattr(result, 'classification_confidence', 'N/A')}")
        print(f"📦 Chunks: {len(result.chunks) if result.chunks else 0}")
        
        # Print any errors
        if hasattr(result, 'error') and result.error:
            print(f"⚠️  Error: {result.error}")
            
    except Exception as e:
        print(f"❌ Flow failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()