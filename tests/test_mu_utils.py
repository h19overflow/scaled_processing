from pathlib import Path
import sys
import types

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.document_processing.utils import mu


def test_custom_prepare_env_creates_dirs(tmp_path):
    out = tmp_path / "out"
    img_dir, md_dir = mu.custom_prepare_env(str(out), "file1")
    # Returned are local_image_dir, local_md_dir - both should exist
    assert Path(img_dir).exists()
    assert Path(md_dir).exists()
    # They should be nested under output_dir and contain file1_output
    assert Path(md_dir).name.endswith("_output")


class DummyPdfReader:
    def __init__(self, stream, strict=True):
        # Pretend there is one page
        self.pages = [object()]


class DummyPdfWriter:
    def __init__(self):
        self._pages = []

    def add_page(self, p):
        self._pages.append(p)

    def write(self, stream):
        # write some bytes
        stream.write(b"repaired-by-pypdf2")


def test_repair_pdf_fallback_with_pypdf2(monkeypatch):
    original = mu.repair_pdf_fallback

    # Inject fake PyPDF2 module
    fake = types.ModuleType("PyPDF2")
    fake.PdfReader = DummyPdfReader
    fake.PdfWriter = DummyPdfWriter
    sys.modules["PyPDF2"] = fake

    try:
        orig_bytes = b"brokenpdf"
        repaired = mu.repair_pdf_fallback(orig_bytes)
        assert isinstance(repaired, (bytes, bytearray))
        assert repaired == b"repaired-by-pypdf2"
    finally:
        del sys.modules["PyPDF2"]


def test_repair_pdf_fallback_with_pdfplumber(monkeypatch):
    # Make PyPDF2 import raise, and provide pdfplumber that can open
    fake_pypdf2 = types.ModuleType("PyPDF2")

    def bad_init(*a, **k):
        raise Exception("bad")

    fake_pypdf2.PdfReader = lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    sys.modules["PyPDF2"] = fake_pypdf2

    class FakePdf:
        def __init__(self, stream):
            self.pages = [1]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = types.ModuleType("pdfplumber")
    fake_pdfplumber.open = lambda stream: FakePdf(stream)
    sys.modules["pdfplumber"] = fake_pdfplumber

    try:
        orig = b"origbytes"
        out = mu.repair_pdf_fallback(orig)
        # pdfplumber validated, so original bytes returned
        assert out == orig
    finally:
        del sys.modules["PyPDF2"]
        del sys.modules["pdfplumber"]


def test_repair_pdf_fallback_all_failures_return_original(monkeypatch):
    # Simulate both PyPDF2 and pdfplumber missing/raising
    fake_pypdf2 = types.ModuleType("PyPDF2")
    fake_pypdf2.PdfReader = lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    sys.modules["PyPDF2"] = fake_pypdf2

    # pdfplumber raises as well
    fake_pdfplumber = types.ModuleType("pdfplumber")

    def open_fail(stream):
        raise Exception("nope")

    fake_pdfplumber.open = open_fail
    sys.modules["pdfplumber"] = fake_pdfplumber

    try:
        orig = b"orig2"
        out = mu.repair_pdf_fallback(orig)
        assert out == orig
    finally:
        del sys.modules["PyPDF2"]
        del sys.modules["pdfplumber"]
