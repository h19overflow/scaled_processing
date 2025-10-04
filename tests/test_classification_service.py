from pathlib import Path
import sys
import asyncio

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.doc_processing_system.pipelines.structured_extraction.utils import classification_service
from src.backend.doc_processing_system.pipelines.structured_extraction.utils.classification_service import DocumentClassificationService


class FakeAgentHigh:
    async def classify_document(self, text):
        return {"classification": "invoice", "confidence": 0.85}

class FakeAgentLow:
    async def classify_document(self, text):
        return {"classification": "other", "confidence": 0.3}

class FakeAgentError:
    async def classify_document(self, text):
        raise Exception("LLM error")


def test_classify_document_uses_llm_when_confident(monkeypatch):
    # Patch ClassificationAgent used in module
    monkeypatch.setattr(classification_service, 'ClassificationAgent', lambda: FakeAgentHigh())
    svc = DocumentClassificationService(connection_manager=None)
    res = asyncio.run(svc.classify_document("some text"))
    assert res["method"] == "llm"
    assert res["classification"] == "invoice"
    assert res["confidence"] >= 0.7


def test_classify_document_falls_back_to_keywords_when_low_confidence(monkeypatch):
    monkeypatch.setattr(classification_service, 'ClassificationAgent', lambda: FakeAgentLow())
    svc = DocumentClassificationService(connection_manager=None)
    # Provide text containing keyword 'invoice' to trigger keyword matcher
    res = asyncio.run(svc.classify_document("This document contains an invoice and payment details."))
    assert res["method"] == "keyword"
    assert res["classification"] in ("invoice", "unknown")


def test_classify_document_handles_agent_exceptions(monkeypatch):
    monkeypatch.setattr(classification_service, 'ClassificationAgent', lambda: FakeAgentError())
    svc = DocumentClassificationService(connection_manager=None)
    res = asyncio.run(svc.classify_document("any"))
    assert res["method"] == "fallback"
    assert res["classification"] == "other"

