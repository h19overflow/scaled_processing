# ...existing code...
from pathlib import Path
import sys
import logging

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.document_processing.utils.document_output_manager import (
    DocumentOutputManager,
)


class FakeCRUD:
    def __init__(self, duplicate=False, create_raises=False):
        self.duplicate = duplicate
        self.create_raises = create_raises
        self._hash = "fakehash"

    def check_duplicate_by_raw_file(self, raw_path):
        if self.duplicate:
            return True, "existing_doc_id"
        return False, None

    def generate_file_hash(self, path):
        return self._hash

    def create(self, document, raw_hash):
        if self.create_raises:
            raise Exception("db down")
        return "db_document_123"

    def get_by_hash(self, content_hash):
        return None

    def generate_content_hash_from_bytes(self, b):
        return "hash_from_bytes"


class DummyConn:
    pass


def make_manager(tmp_path, crud=None):
    # Create manager with processed_documents_dir inside tmp_path
    proc_dir = tmp_path / "processed"
    m = DocumentOutputManager(processed_documents_dir=str(proc_dir))
    # Replace connection_manager and document_crud
    m.connection_manager = DummyConn()
    m.document_crud = crud or FakeCRUD()
    m.logger.setLevel(logging.DEBUG)
    return m


def test_check_and_process_document_duplicate(tmp_path):
    # create a dummy raw file
    raw = tmp_path / "dup.pdf"
    raw.write_bytes(b"data")

    mgr = make_manager(tmp_path, crud=FakeCRUD(duplicate=True))
    res = mgr.check_and_process_document(str(raw), user_id="u1")
    assert res["status"] == "duplicate"
    assert res["document_id"] == "existing_doc_id"


def test_check_and_process_document_ready_for_processing_db_success(tmp_path):
    raw = tmp_path / "new.pdf"
    raw.write_bytes(b"data")

    mgr = make_manager(tmp_path, crud=FakeCRUD(duplicate=False, create_raises=False))
    res = mgr.check_and_process_document(str(raw), user_id="u2")
    assert res["status"] == "ready_for_processing"
    assert "document_id" in res
    assert "db_document_id" in res and res["db_document_id"] == "db_document_123"


def test_check_and_process_document_db_create_fails_but_continues(tmp_path):
    raw = tmp_path / "new2.pdf"
    raw.write_bytes(b"data")

    mgr = make_manager(tmp_path, crud=FakeCRUD(duplicate=False, create_raises=True))
    res = mgr.check_and_process_document(str(raw), user_id="u3")
    assert res["status"] == "ready_for_processing"
    # When DB create fails code returns processing_result without db_document_id
    assert "db_document_id" not in res


def test_save_processed_document_and_get_info(tmp_path, monkeypatch):
    mgr = make_manager(tmp_path)

    # Monkeypatch _store_document_in_database to avoid DB calls
    calls = {}

    def fake_store(self, document_id, metadata, user_id):
        calls["called"] = True

    monkeypatch.setattr(
        DocumentOutputManager, "_store_document_in_database", fake_store
    )

    metadata = {
        "filename": "orig.pdf",
        "page_count": 2,
        "content_length": 123,
        "file_type": "pdf",
        "file_size": 456,
        "raw_file_path": str(tmp_path / "orig.pdf"),
    }

    res = mgr.save_processed_document("docX", "Hello content", metadata, user_id="u4")
    assert res["status"] == "saved"
    doc_dir = Path(res["document_directory"])
    assert doc_dir.exists()

    # Processed markdown and metadata files exist
    md = Path(res["processed_file_path"])
    meta = Path(res["metadata_file_path"])
    assert md.exists()
    assert meta.exists()

    # Now call get_document_path_info
    info = mgr.get_document_path_info("docX")
    assert info["status"] == "found"
    assert info["exists"]["directory"] is True
    assert info["exists"]["markdown"] is True
    assert info["exists"]["metadata"] is True


def test_generate_document_id_sanitization():
    mgr = DocumentOutputManager(processed_documents_dir="data/temp")
    # simulate weird filename
    path = Path('  a<>:"|?*my file.pdf')
    safe = mgr._generate_document_id(path)
    assert " " not in safe
    assert "<" not in safe
    assert '"' not in safe
    assert safe != ""
