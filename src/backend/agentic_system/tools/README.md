---
# Agentic System Tools - Comprehensive Examples

This README provides detailed examples of tool outputs from our pydantic-ai tool wrappers. These tools interface directly with the TemporalCRUD and LineItemCRUD classes to provide structured data for agentic systems.

## 🕐 Temporal Analysis Tools

The temporal analysis tools provide access to date-based document information extracted from invoices, contracts, and other documents.

### Tool: `get_documents_by_date_range`

**Input:**
```python
DateRangeQuery(
    start_date="2023-08-01",
    end_date="2023-12-31",
    limit=3
)
```

**Output Structure:**
```python
[
    {
        'document_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'document_name': 'Invoice_2023_Q4_Supplies.pdf',
        'extraction_class': 'invoice_date',
        'extraction_text': 'December 15, 2023',
        'iso_date': '2023-12-15',
        'date_type': 'invoice_date',
        'created_at': '2023-12-20T14:30:25.123456'
    },
    {
        'document_id': 'b2c3d4e5-f6g7-8901-bcde-f12345678901',
        'document_name': 'Contract_ServiceAgreement_2023.pdf',
        'extraction_class': 'contract_start',
        'extraction_text': 'September 1st, 2023',
        'iso_date': '2023-09-01',
        'date_type': 'contract_start',
        'created_at': '2023-09-05T09:15:42.789012'
    },
    {
        'document_id': 'c3d4e5f6-g7h8-9012-cdef-123456789012',
        'document_name': 'Receipt_OfficeSupplies_Aug2023.pdf',
        'extraction_class': 'purchase_date',
        'extraction_text': 'August 22, 2023',
        'iso_date': '2023-08-22',
        'date_type': 'purchase_date',
        'created_at': '2023-08-25T16:45:18.345678'
    }
]
```

### Tool: `get_documents_by_date_type`

**Input:**
```python
DateTypeQuery(
    date_type="invoice_date",
    limit=2
)
```

**Output Structure:**
```python
[
    {
        'document_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'document_name': 'Invoice_TechServices_Dec2023.pdf',
        'extraction_text': 'Invoice Date: December 15, 2023',
        'iso_date': '2023-12-15',
        'date_type': 'invoice_date',
        'created_at': '2023-12-20T14:30:25.123456'
    },
    {
        'document_id': 'b2c3d4e5-f6g7-8901-bcde-f12345678901',
        'document_name': 'Invoice_ConsultingFee_Nov2023.pdf',
        'extraction_text': 'Date: November 28, 2023',
        'iso_date': '2023-11-28',
        'date_type': 'invoice_date',
        'created_at': '2023-12-01T11:22:33.456789'
    }
]
```

### Tool: `get_recent_temporal_data`

**Input:**
```python
RecentDataQuery(
    days=7,
    limit=2
)
```

**Output Structure:**
```python
[
    {
        'document_id': 'x1y2z3a4-b5c6-7890-wxyz-abc123456789',
        'document_name': 'Invoice_Weekly_Services.pdf',
        'extraction_class': 'due_date',
        'extraction_text': 'Payment Due: January 15, 2024',
        'iso_date': '2024-01-15',
        'date_type': 'due_date',
        'created_at': '2024-01-08T10:15:30.123456'
    },
    {
        'document_id': 'y2z3a4b5-c6d7-8901-xyza-bcd234567890',
        'document_name': 'Contract_Amendment_Jan2024.pdf',
        'extraction_class': 'effective_date',
        'extraction_text': 'Effective Date: January 10, 2024',
        'iso_date': '2024-01-10',
        'date_type': 'effective_date',
        'created_at': '2024-01-07T14:22:45.789012'
    }
]
```

### Tool: `get_temporal_statistics`

**Input:** No parameters required

**Output Structure:**
```python
{
    'total_temporal_records': 1247,
    'extraction_classes': {
        'invoice_date': 523,
        'due_date': 478,
        'contract_start': 89,
        'contract_end': 67,
        'purchase_date': 90
    },
    'date_types': {
        'invoice_date': 523,
        'due_date': 478,
        'contract_start': 89,
        'contract_end': 67,
        'purchase_date': 90
    },
    'generated_at': '2024-01-10T15:30:45.123456'
}
```

## 🛒 Line Item Analysis Tools

The line item analysis tools provide access to product and pricing information extracted from invoices, receipts, and purchase orders.

### Tool: `get_line_items_by_document`

**Input:**
```python
DocumentLineItemQuery(
    document_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    limit=2
)
```

**Output Structure:**
```python
[
    {
        # Identifiers
        'document_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'document_name': 'Invoice_TechSupplies_Dec2023.pdf',

        # Product Information
        'product': {
            'description': 'Wireless Bluetooth Headphones - Premium Quality',
            'raw_text': 'Bluetooth Headphones Premium'
        },

        # Financial Information
        'pricing': {
            'quantity': 2.0,
            'unit_price': 89.99,
            'total_amount': 179.98,
            'currency': 'USD'
        },

        # Formatted Display Values (for easy frontend use)
        'display': {
            'quantity_text': '2',
            'unit_price_text': 'USD 89.99',
            'total_amount_text': 'USD 179.98',
            'full_description': 'Wireless Bluetooth Headphones - Premium Quality with noise cancellation and 20-hour...'
        },

        # Metadata
        'metadata': {
            'created_at': '2023-12-20T14:30:25.123456',
            'has_pricing': True,
            'has_quantity': True
        }
    },
    {
        # Identifiers
        'document_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'document_name': 'Invoice_TechSupplies_Dec2023.pdf',

        # Product Information
        'product': {
            'description': 'USB-C Charging Cable 6ft',
            'raw_text': 'USB-C Cable 6ft'
        },

        # Financial Information
        'pricing': {
            'quantity': 5.0,
            'unit_price': 12.50,
            'total_amount': 62.50,
            'currency': 'USD'
        },

        # Formatted Display Values
        'display': {
            'quantity_text': '5',
            'unit_price_text': 'USD 12.50',
            'total_amount_text': 'USD 62.50',
            'full_description': 'USB-C Charging Cable 6ft'
        },

        # Metadata
        'metadata': {
            'created_at': '2023-12-20T14:30:25.123456',
            'has_pricing': True,
            'has_quantity': True
        }
    }
]
```

### Tool: `get_line_items_by_amount_range`

**Input:**
```python
AmountRangeQuery(
    min_amount=100.0,
    max_amount=500.0,
    limit=2
)
```

**Output Structure:**
```python
[
    {
        'document_id': 'b2c3d4e5-f6g7-8901-bcde-f12345678901',
        'document_name': 'Purchase_Order_Electronics.pdf',

        'product': {
            'description': 'Professional Gaming Monitor 27" 4K',
            'raw_text': 'Gaming Monitor 27in 4K Professional'
        },

        'pricing': {
            'quantity': 1.0,
            'unit_price': 449.99,
            'total_amount': 449.99,
            'currency': 'USD'
        },

        'display': {
            'quantity_text': '1',
            'unit_price_text': 'USD 449.99',
            'total_amount_text': 'USD 449.99',
            'full_description': 'Professional Gaming Monitor 27" 4K with HDR support and 144Hz refresh rate'
        },

        'metadata': {
            'created_at': '2023-12-18T11:45:30.789012',
            'has_pricing': True,
            'has_quantity': True
        }
    },
    {
        'document_id': 'c3d4e5f6-g7h8-9012-cdef-123456789012',
        'document_name': 'Invoice_OfficeEquipment.pdf',

        'product': {
            'description': 'Ergonomic Office Chair with Lumbar Support',
            'raw_text': 'Office Chair Ergonomic Lumbar Support'
        },

        'pricing': {
            'quantity': 1.0,
            'unit_price': 299.95,
            'total_amount': 299.95,
            'currency': 'USD'
        },

        'display': {
            'quantity_text': '1',
            'unit_price_text': 'USD 299.95',
            'total_amount_text': 'USD 299.95',
            'full_description': 'Ergonomic Office Chair with Lumbar Support'
        },

        'metadata': {
            'created_at': '2023-12-15T09:30:15.345678',
            'has_pricing': True,
            'has_quantity': True
        }
    }
]
```

### Tool: `get_recent_line_items`

**Input:**
```python
RecentLineItemQuery(
    days=14,
    limit=2
)
```

**Output Structure:**
```python
[
    {
        'document_id': 'x1y2z3a4-b5c6-7890-wxyz-abc123456789',
        'document_name': 'Receipt_Staples_Jan2024.pdf',

        'product': {
            'description': 'Printer Paper - 500 sheets, Letter Size',
            'raw_text': 'Printer Paper 500 sheets Letter'
        },

        'pricing': {
            'quantity': 10.0,
            'unit_price': 4.99,
            'total_amount': 49.90,
            'currency': 'USD'
        },

        'display': {
            'quantity_text': '10',
            'unit_price_text': 'USD 4.99',
            'total_amount_text': 'USD 49.90',
            'full_description': 'Printer Paper - 500 sheets, Letter Size'
        },

        'metadata': {
            'created_at': '2024-01-08T16:22:18.456789',
            'has_pricing': True,
            'has_quantity': True
        }
    },
    {
        'document_id': 'y2z3a4b5-c6d7-8901-xyza-bcd234567890',
        'document_name': 'Invoice_SoftwareLicense.pdf',

        'product': {
            'description': 'Annual Software License - Project Management Suite',
            'raw_text': 'Software License Annual Project Management'
        },

        'pricing': {
            'quantity': 1.0,
            'unit_price': 1200.00,
            'total_amount': 1200.00,
            'currency': 'USD'
        },

        'display': {
            'quantity_text': '1',
            'unit_price_text': 'USD 1200.00',
            'total_amount_text': 'USD 1200.00',
            'full_description': 'Annual Software License - Project Management Suite'
        },

        'metadata': {
            'created_at': '2024-01-05T13:15:42.123456',
            'has_pricing': True,
            'has_quantity': True
        }
    }
]
```

### Tool: `search_line_items_by_description`

**Input:**
```python
DescriptionSearchQuery(
    keyword="adhesive",
    limit=2
)
```

**Output Structure:**
```python
[
    {
        'document_id': 'z3a4b5c6-d7e8-9012-zabc-def345678901',
        'document_name': 'Purchase_Order_Workshop_Supplies.pdf',

        'product': {
            'description': 'Industrial Strength Adhesive Tape - 2" x 50yd',
            'raw_text': 'Adhesive Tape Industrial 2in x 50yd'
        },

        'pricing': {
            'quantity': 12.0,
            'unit_price': 15.75,
            'total_amount': 189.00,
            'currency': 'USD'
        },

        'display': {
            'quantity_text': '12',
            'unit_price_text': 'USD 15.75',
            'total_amount_text': 'USD 189.00',
            'full_description': 'Industrial Strength Adhesive Tape - 2" x 50yd'
        },

        'metadata': {
            'created_at': '2023-12-10T10:30:25.678901',
            'has_pricing': True,
            'has_quantity': True
        }
    },
    {
        'document_id': 'a4b5c6d7-e8f9-0123-abcd-efg456789012',
        'document_name': 'Invoice_Construction_Materials.pdf',

        'product': {
            'description': 'Multi-Purpose Adhesive Glue - 1 Gallon Container',
            'raw_text': 'Adhesive Glue Multi-Purpose 1 Gallon'
        },

        'pricing': {
            'quantity': 3.0,
            'unit_price': 28.99,
            'total_amount': 86.97,
            'currency': 'USD'
        },

        'display': {
            'quantity_text': '3',
            'unit_price_text': 'USD 28.99',
            'total_amount_text': 'USD 86.97',
            'full_description': 'Multi-Purpose Adhesive Glue - 1 Gallon Container'
        },

        'metadata': {
            'created_at': '2023-11-28T14:45:12.234567',
            'has_pricing': True,
            'has_quantity': True
        }
    }
]
```

### Tool: `get_line_item_statistics`

**Input:** No parameters required

**Output Structure:**
```python
{
    'total_line_items': 3247,
    'documents_with_line_items': 892,
    'avg_items_per_document': 3.64,
    'currency_breakdown': {
        'USD': 2890,
        'EUR': 245,
        'GBP': 89,
        'CAD': 23
    },
    'generated_at': '2024-01-10T15:45:33.789012'
}
```

## Data Structure Details

### Temporal Data Fields

- **`document_id`**: UUID of the source document
- **`document_name`**: Original filename or document identifier
- **`extraction_class`**: Type of temporal extraction (invoice_date, due_date, etc.)
- **`extraction_text`**: Raw text where the date was found
- **`iso_date`**: Standardized ISO date format (YYYY-MM-DD)
- **`date_type`**: Semantic type from attributes (same as extraction_class)
- **`created_at`**: When the extraction was processed

### Line Item Data Fields

#### Product Section
- **`description`**: Clean product description
- **`raw_text`**: Original extracted text

#### Pricing Section (Numeric Types)
- **`quantity`**: Numeric quantity (float or null)
- **`unit_price`**: Numeric unit price (float or null)
- **`total_amount`**: Numeric total amount (float or null)
- **`currency`**: Currency code (string)

#### Display Section (Frontend Ready)
- **`quantity_text`**: Formatted quantity for display
- **`unit_price_text`**: Formatted unit price with currency
- **`total_amount_text`**: Formatted total with currency
- **`full_description`**: Truncated description (100 chars + ellipsis)

#### Metadata Section
- **`created_at`**: ISO timestamp when processed
- **`has_pricing`**: Boolean flag for pricing availability
- **`has_quantity`**: Boolean flag for quantity availability

## Usage in Agent Development

These tools are designed to be used by pydantic-ai agents for:

1. **Financial Analysis**: Analyzing spending patterns, invoice amounts, and budget tracking
2. **Temporal Analysis**: Finding documents by date ranges, tracking contract timelines
3. **Product Search**: Finding specific items, categories, or suppliers
4. **Compliance Reporting**: Generating reports on purchases, dates, and financial data

The structured outputs ensure consistent data formats across different agents and use cases, making integration with frontend systems and further processing straightforward.

## Error Handling

All tools include comprehensive error handling:

```python
# Example error response
[{"error": "Failed to retrieve line items by amount range: Invalid amount format"}]

# Or for statistics
{"error": "Failed to retrieve temporal statistics: Database connection failed"}
```

Errors are returned in the same structure as successful responses to maintain consistency for agent processing.
