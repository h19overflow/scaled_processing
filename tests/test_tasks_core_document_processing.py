from pathlib import Path
import sys
import json
import logging

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import the modules under test
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import document_processing_task
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import document_saving_task
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import duplicate_detection_task


def test_docling_processing_task_success(tmp_path, monkeypatch):
    # Create dummy raw file
    raw = tmp_path / 'file.pdf'
    raw.write_bytes(b'%PDF-1.4 dummy')

    # Fake DocumentProcessor that returns a completed extraction
    class FakeProcessor:
        def __init__(self, *a, **k):
            pass
        def extract_document(self, raw_file_path, document_id):
            # create a fake processed markdown
            out_dir = tmp_path / f'{document_id}_proc'
            out_dir.mkdir(parents=True, exist_ok=True)
            md = out_dir / f'{document_id}_processed.md'
            md.write_text('# header\ncontent')
            return {
                'status': 'completed',
                'processed_markdown_path': str(md),
                'file_info': {'filename': raw.name},
                'processing_directory': str(out_dir)
            }

    # Patch the DocumentProcessor name in the module
    monkeypatch.setattr(document_processing_task, 'DocumentProcessor', FakeProcessor)

    # Execute the prefect task synchronously via .run
    res = document_processing_task.docling_processing_task.run(str(raw), 'doc1')
    assert res['status'] == 'completed'
    assert res['document_id'] == 'doc1'
    assert 'processed_markdown_path' in res


def test_docling_processing_task_failure(tmp_path, monkeypatch):
    raw = tmp_path / 'file2.pdf'
    raw.write_bytes(b'%PDF-1.4')

    class FakeProcessorErr:
        def __init__(self, *a, **k):
            pass
        def extract_document(self, raw_file_path, document_id):
            return {'status': 'error', 'error': 'parse failed', 'error_details': ''}

    monkeypatch.setattr(document_processing_task, 'DocumentProcessor', FakeProcessorErr)
    res = document_processing_task.docling_processing_task.run(str(raw), 'doc2')
    assert res['status'] == 'error'
    assert res['document_id'] == 'doc2'


def test_document_saving_task_success(tmp_path, monkeypatch):
    # Create a vision-enhanced markdown file
    md = tmp_path / 'vision.md'
    md.write_text('enhanced content')
    raw = tmp_path / 'raw.pdf'
    raw.write_bytes(b'data')

    # Fake DocumentOutputManager that saves processed files
    class FakeOutputManager:
        def __init__(self, *a, **k):
            pass
        def save_processed_document(self, document_id, processed_content, metadata, user_id='default'):
            doc_dir = tmp_path / document_id
            doc_dir.mkdir(parents=True, exist_ok=True)
            processed_file = doc_dir / f"{document_id}_processed.md"
            processed_file.write_text(processed_content)
            metadata_file = doc_dir / f"{document_id}_metadata.json"
            metadata_file.write_text(json.dumps(metadata))
            return {
                'status': 'saved',
                'document_id': document_id,
                'processed_file_path': str(processed_file),
                'metadata_file_path': str(metadata_file),
                'document_directory': str(doc_dir)
            }

    # Patch the class used in the module
    monkeypatch.setattr(document_saving_task, 'DocumentOutputManager', FakeOutputManager)

    # Patch messaging ProducerHandler and create_message to avoid external calls
    class FakeProducer:
        def __init__(self, *a, **k):
            pass
        def produce_message(self, topic, key, value):
            return True

    monkeypatch.setattr(document_saving_task, 'ProducerHandler', FakeProducer)
    monkeypatch.setattr(document_saving_task, 'create_message', lambda event_type, data, source: json.dumps({'event_type': event_type, 'data': data, 'source': source}))

    res = document_saving_task.document_saving_task.run(str(md), 'docsave', content_length=123, page_count=1, raw_file_path=str(raw), user_id='u1')
    assert res['status'] == 'completed'
    assert res['save_result']['status'] == 'saved'
    assert res['final_content_length'] == len('enhanced content')


def test_duplicate_detection_task_duplicate_and_ready(monkeypatch, tmp_path):
    # Fake DocumentCRUD to simulate duplicate and non-duplicate
    class FakeCrudDup:
        def __init__(self, *a, **k):
            pass
        def check_duplicate_by_raw_file(self, path):
            return True, 'existing123'

    class FakeCrudNew:
        def __init__(self, *a, **k):
            pass
        def check_duplicate_by_raw_file(self, path):
            return False, None

    # Patch the DocumentCRUD in the module
    monkeypatch.setattr(duplicate_detection_task, 'DocumentCRUD', lambda cm: FakeCrudDup())
    # ConnectionManager can be a dummy
    monkeypatch.setattr(duplicate_detection_task, 'ConnectionManager', lambda: None)

    raw = tmp_path / 'dup.pdf'
    raw.write_bytes(b'data')
    res = duplicate_detection_task.duplicate_detection_task.run(str(raw))
    assert res['status'] == 'duplicate'
    assert res['document_id'] == 'existing123'

    # Now test non-duplicate path
    monkeypatch.setattr(duplicate_detection_task, 'DocumentCRUD', lambda cm: FakeCrudNew())
    res2 = duplicate_detection_task.duplicate_detection_task.run(str(raw))
    assert res2['status'] == 'ready_for_processing'
    assert 'document_id' in res2

