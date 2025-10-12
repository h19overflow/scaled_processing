"""
Document chunking node.
"""

from pathlib import Path
from typing import Dict, Any

from ..models.state import PipelineState


def read_markdown(state: PipelineState) -> Dict[str, Any]:
    """Chunk document into processing batches."""
    try:
        document_input = state.document_text
        if not document_input:
            raise ValueError("No document text or file path provided")

        # Check if input is a file path or actual content
        if document_input.startswith(('docs/', '/', './', '../')) or document_input.endswith('.md'):
            # It's a file path - read the file
            text = _read_markdown_file(document_input)
        else:
            # It's actual document content
            text = document_input
        return {
            "document_text": text,  # Include actual document content for downstream tasks_core
            "status": "markdown_read"
        }

    except Exception as e:
        return {
            "error": f"Document markdown reading failed: {str(e)}",
            "status": "error"
        }


def _read_markdown_file(file_path: str) -> str:
    """Read content from markdown file."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        if not path.suffix.lower() == '.md':
            raise ValueError(f"File is not a markdown file: {file_path}")

        return path.read_text(encoding='utf-8')

    except Exception as e:
        raise ValueError(f"Failed to read markdown file {file_path}: {str(e)}")


