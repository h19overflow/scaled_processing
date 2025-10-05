from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.structured_extraction.utils import config_router


def test_process_document_returns_expected_structure():
    """Test that process_document returns the expected dictionary structure."""
    test_text = """
    ALAMAT POS
    TEST COMPANY SDN. BHD.
    NO. 123, JALAN TEST
    
    TARIKH BIL: 01.01.2025
    NO. INVOIS: 123456789
    JUMLAH BIL ANDA RM100.00
    Sila bayar sebelum: 31 January 2025
    Biller Code: 1234
    """
    
    result = config_router.process_document(test_text)
    
    # Check return structure
    assert isinstance(result, dict)
    assert 'extractions' in result
    assert 'status' in result
    assert 'total_extractions' in result
    
    # Check status is success
    assert result['status'] == 'completed'
    
    # Check extractions is a list
    assert isinstance(result['extractions'], list)
    
    # Check each extraction has required fields
    for extraction in result['extractions']:
        assert 'extraction_class' in extraction
        assert 'extraction_text' in extraction
        assert 'attributes' in extraction
        assert isinstance(extraction['attributes'], dict)


def test_process_document_handles_empty_input():
    """Test that process_document handles empty input gracefully."""
    result = config_router.process_document("")
    
    assert isinstance(result, dict)
    assert 'extractions' in result
    assert 'status' in result
    assert result['status'] == 'completed'
    assert isinstance(result['extractions'], list)


def test_process_document_extracts_core_fields():
    """Test that process_document extracts core fields when present."""
    test_text = """
    ALAMAT POS
    CORE FIELDS COMPANY SDN. BHD.
    NO. 456, JALAN CORE
    
    TARIKH BIL: 15.06.2025
    NO. INVOIS: 987654321
    JUMLAH BIL ANDA RM1,500.75
    Sila bayar sebelum: 30 Jun 2025
    Biller Code: 5678
    """
    
    result = config_router.process_document(test_text)
    
    # Extract all extraction classes
    extraction_classes = {ext['extraction_class'] for ext in result['extractions']}
    
    # Check that core fields are present
    expected_core_fields = {'amount_due', 'due_date', 'issue_date', 'invoice_number', 'biller_code'}
    found_core_fields = expected_core_fields.intersection(extraction_classes)
    
    # Should find most core fields (at least amount_due and one date field)
    assert len(found_core_fields) >= 2
    assert 'amount_due' in found_core_fields  # Most important field


def test_extraction_attributes_structure():
    """Test that extraction attributes have the expected structure."""
    test_text = """
    TARIKH BIL: 01.02.2025
    JUMLAH BIL ANDA RM250.50
    """
    
    result = config_router.process_document(test_text)
    
    for extraction in result['extractions']:
        attributes = extraction['attributes']
        
        # Test amount_due attributes
        if extraction['extraction_class'] == 'amount_due':
            assert 'amount_due' in attributes
            assert isinstance(attributes['amount_due'], (int, float))
            assert attributes['amount_due'] > 0
            
        # Test date attributes have iso_date when possible
        if extraction['extraction_class'] in ['issue_date', 'due_date']:
            if 'iso_date' in attributes:
                assert isinstance(attributes['iso_date'], str)
                assert len(attributes['iso_date']) == 10  # YYYY-MM-DD format
