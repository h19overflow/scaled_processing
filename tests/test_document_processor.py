import sys
from pathlib import Path
import json

# Ensure repo root is on sys.path so imports work
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.document_processing.utils import document_processor
from src.backend.doc_processing_system.pipelines.document_processing.utils.document_processor import DocumentProcessor


def test_file_not_found(tmp_path):
    dp = DocumentProcessor(temp_base_dir=str(tmp_path / "mineru"))
    result = dp.extract_document(str(tmp_path / "does_not_exist.pdf"), "doc_missing")
    assert result["status"] == "error"
    assert "File not found" in result["error"]


def test_successful_extraction_creates_markdown_and_csv(tmp_path, monkeypatch):
    temp_base = tmp_path / "mineru"
    dp = DocumentProcessor(temp_base_dir=str(temp_base))

    # Create a dummy raw file
    raw_file = tmp_path / "invoice_001.pdf"
    raw_file.write_bytes(b"%PDF-1.4 dummy")

    document_id = "invoice_001"

    # Mock parse_single_file to create expected MinerU output (content_list.json)
    def mock_parse_single_file(file_path, output_dir, backend=None):
        out_dir = Path(output_dir) / f"{Path(file_path).stem}_output"
        out_dir.mkdir(parents=True, exist_ok=True)
        content_list = [
            {"page_idx": 0, "type": "text", "text": "Invoice Header", "text_level": 1},
            {"page_idx": 0, "type": "table", "table_body": "<table><tr><td>Item</td></tr></table>"},
            {"page_idx": 1, "type": "text", "text": "Page 2 text", "text_level": 2}
        ]
        with open(out_dir / f"{Path(file_path).stem}_content_list.json", 'w', encoding='utf-8') as f:
            json.dump(content_list, f)

    monkeypatch.setattr(document_processor, 'parse_single_file', mock_parse_single_file)

    # Replace table_extractor with a simple mock that writes CSV
    class MockTableExtractor:
        def __init__(self, logger=None):
            pass

        def extract_tables_from_content_list(self, content_list_path, csv_path, document_id):
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write('col1,col2\nval1,val2')

    dp.table_extractor = MockTableExtractor()

    result = dp.extract_document(str(raw_file), document_id)
    assert result["status"] == "completed"

    # Check markdown exists and contains header and table html
    md_path = Path(result["processed_markdown_path"])
    assert md_path.exists()
    md_text = md_path.read_text(encoding='utf-8')
    assert "# Invoice Header" in md_text
    assert "<table>" in md_text

    # Check csv exists
    csv_path = Path(result["line_items_csv_path"])
    assert csv_path.exists()
    assert csv_path.read_text(encoding='utf-8').startswith('col1')


def test_pdf_error_triggers_repair_and_retry(tmp_path, monkeypatch):
    temp_base = tmp_path / "mineru"
    dp = DocumentProcessor(temp_base_dir=str(temp_base))

    raw_file = tmp_path / "broken.pdf"
    raw_file.write_bytes(b"%PDF-1.4 broken content")
    document_id = "broken_doc"

    # Behavior list: first call raises PdfiumError-like, second call creates content_list
    call_state = {"count": 0}

    def mock_parse(file_path, output_dir, backend=None):
        call_state['count'] += 1
        if call_state['count'] == 1:
            raise Exception("PdfiumError: page load failed")
        else:
            out_dir = Path(output_dir) / f"{Path(file_path).stem}_output"
            out_dir.mkdir(parents=True, exist_ok=True)
            content_list = [{"page_idx": 0, "type": "text", "text": "Repaired header", "text_level": 1}]
            with open(out_dir / f"{Path(file_path).stem}_content_list.json", 'w', encoding='utf-8') as f:
                json.dump(content_list, f)

    monkeypatch.setattr(document_processor, 'parse_single_file', mock_parse)

    # Monkeypatch _repair_pdf_file to write a repaired file and return its path
    def mock_repair(pdf_path, processing_dir):
        # Write repaired bytes but keep the same filename so downstream expected output dir matches
        repaired = Path(processing_dir) / f"{Path(pdf_path).name}"
        repaired.write_bytes(b"%PDF-1.4 repaired")
        return repaired

    monkeypatch.setattr(DocumentProcessor, '_repair_pdf_file', lambda self, p, d: mock_repair(p, d))

    # Mock table extractor
    dp.table_extractor = type('X', (), {"extract_tables_from_content_list": lambda self, a, b, c: open(b, 'w', encoding='utf-8').write('x')})()

    result = dp.extract_document(str(raw_file), document_id)
    assert result["status"] == "completed"
    # Ensure parse was called at least twice
    assert call_state['count'] >= 2


def test_non_pdf_error_bubbles_up_and_returns_error(tmp_path, monkeypatch):
    dp = DocumentProcessor(temp_base_dir=str(tmp_path / "mineru"))
    raw_file = tmp_path / "some.pdf"
    raw_file.write_bytes(b"%PDF-1.4")

    def raise_other(file_path, output_dir, backend=None):
        raise Exception("Unexpected runtime problem")

    monkeypatch.setattr(document_processor, 'parse_single_file', raise_other)

    result = dp.extract_document(str(raw_file), "doc_err")
    assert result["status"] == "error"
    assert "Extraction failed" in result["error"] or "Unexpected runtime problem" in result.get("error_details", "")
