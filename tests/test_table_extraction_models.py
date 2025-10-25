from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.data_models.table_extraction import (
    TableFieldMapping,
    TableExtractionConfig,
    TableExtractionResult,
)


def test_table_field_mapping_extracts_float_and_int_and_handles_bounds():
    # Prepare table data with a numeric field
    tables_data = [
        {
            "table_id": 1,
            "data": [
                {"Amount (RM)": "950.00", "Count": "10"},
                {"Amount (RM)": "1,200.50", "Count": "5"},
            ],
        }
    ]

    # Float field mapping
    fm_float = TableFieldMapping(
        field_name="amount",
        english_translation="Amount",
        table_id=1,
        extraction_path="data[0]['Amount (RM)']",
        example_value="950.00",
        field_type="float",
        is_required=True,
    )

    val = fm_float.extract_value(tables_data)
    assert isinstance(val, float)
    assert abs(val - 950.00) < 0.001

    # Int field mapping
    fm_int = TableFieldMapping(
        field_name="count",
        english_translation="Count",
        table_id=1,
        extraction_path="data[0]['Count']",
        example_value="10",
        field_type="int",
        is_required=False,
    )

    val_int = fm_int.extract_value(tables_data)
    assert isinstance(val_int, int)
    assert val_int == 10

    # Out of bounds index returns None
    fm_oob = TableFieldMapping(
        field_name="oob",
        english_translation="OOB",
        table_id=1,
        extraction_path="data[5]['Count']",
        example_value="",
        field_type="string",
        is_required=False,
    )

    assert fm_oob.extract_value(tables_data) is None


def test_table_extraction_config_and_result_methods():
    mapping1 = TableFieldMapping(
        field_name="amount",
        english_translation="Amount",
        table_id=2,
        extraction_path="data[0]['x']",
        example_value="",
        field_type="string",
        is_required=True,
    )

    mapping2 = TableFieldMapping(
        field_name="qty",
        english_translation="Quantity",
        table_id=2,
        extraction_path="data[0]['y']",
        example_value="",
        field_type="int",
        is_required=False,
    )

    config = TableExtractionConfig(
        document_type="invoice", description="desc", field_mappings=[mapping1, mapping2]
    )

    assert config.get_field_mapping("amount") is mapping1
    assert config.get_field_mapping("missing") is None

    tables_data = [{"table_id": 2, "data": [{"x": "foo", "y": "12"}]}]

    extracted = config.extract_all_fields(tables_data)
    assert "amount" in extracted
    assert "qty" in extracted
    assert config.get_required_fields() == ["amount"]

    # TableExtractionResult conversion
    result = TableExtractionResult(
        document_id="doc1",
        document_name="Doc 1",
        table_extractions={
            "amount": {
                "value": "100",
                "english_translation": "Amount",
                "table_id": 2,
                "field_type": "string",
            }
        },
        extraction_config="cfg1",
        tables_count=1,
    )

    converted = result.to_extraction_results()
    assert isinstance(converted, list)
    assert converted[0]["extraction_text"] == "100"
