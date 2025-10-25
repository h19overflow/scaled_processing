# ...existing code...
from pathlib import Path
import json
import pandas as pd
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.document_processing.utils.table_line_item_extractor import (
    TableLineItemExtractor,
)


def test_extract_tables_to_line_items_from_markdown(tmp_path):
    md = """
    <html>
    <body>
    <table>
      <tr><th>Item</th><th>Price</th></tr>
      <tr><td>Apple</td><td>1.20</td></tr>
      <tr><td>Banana</td><td>0.80</td></tr>
    </table>
    </body>
    </html>
    """

    extractor = TableLineItemExtractor()
    items = extractor.extract_tables_to_line_items(md, "doc1")
    # Should extract two line items
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["line_item_label"] == "Apple"
    # data_json should contain Price
    import json as _json

    data0 = _json.loads(items[0]["data_json"])
    assert "Price" in data0


def test_extract_tables_from_content_list_and_save_csv(tmp_path):
    # Create a sample content_list.json with a table entry
    content_list = [
        {"page_idx": 0, "type": "text", "text": "Header"},
        {
            "page_idx": 0,
            "type": "table",
            "table_body": "<table><tr><th>Item</th><th>Qty</th></tr><tr><td>Pen</td><td>3</td></tr></table>",
        },
    ]

    content_path = tmp_path / "doc_output" / "doc1_content_list.json"
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(json.dumps(content_list), encoding="utf-8")

    extractor = TableLineItemExtractor()
    csv_path = tmp_path / "doc_output" / "doc1_line_items.csv"

    ok = extractor.extract_tables_from_content_list(content_path, csv_path, "doc1")
    assert ok is True
    assert csv_path.exists()
    # Read CSV and check header contains line_item_id
    df = pd.read_csv(csv_path)
    assert "line_item_id" in df.columns
    assert df.iloc[0]["line_item_label"] == "Pen"


def test_save_line_items_to_csv_empty_returns_false(tmp_path):
    extractor = TableLineItemExtractor()
    out = tmp_path / "nothing.csv"
    ok = extractor.save_line_items_to_csv([], out)
    assert ok is False


# ...existing code...
