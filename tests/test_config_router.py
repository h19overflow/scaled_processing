from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.structured_extraction.utils import config_router


def test_invoice_extraction_returns_prompt_and_examples():
    prompt, examples = config_router.invoice_extraction()
    assert isinstance(prompt, str)
    assert "Extract Malaysian utility bill" in prompt
    assert isinstance(examples, list)
    assert len(examples) > 0
    # Check that example items have expected attributes (duck-typed)
    ex = examples[0]
    assert hasattr(ex, 'text')
    assert hasattr(ex, 'extractions')


def test_process_document_delegates_to_lx_extract(monkeypatch):
    # Monkeypatch only the lx.extract function in config_router
    class FakeResult:
        def __init__(self, value):
            self.value = value
    def fake_extract(*args, **kwargs):
        return FakeResult('ok')

    # Patch the existing lx.extract function so invoice_extraction can still access lx.data
    monkeypatch.setattr(config_router.lx, 'extract', fake_extract, raising=True)

    res = config_router.process_document('some text')
    assert hasattr(res, 'value')
    assert res.value == 'ok'
