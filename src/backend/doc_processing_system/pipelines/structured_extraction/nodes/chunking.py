"""
Document chunking node.
"""

from pathlib import Path
from typing import List

import tiktoken

from ..config.settings import Settings
from ..models.document import DocumentChunk
from ..models.state import MultiAgentState


def chunk_document(state: MultiAgentState, settings: Settings) -> MultiAgentState:
    """Chunk document into processing batches."""
    try:
        markdown_file_path = state["document_text"]
        if not markdown_file_path:
            raise ValueError("No markdown file path provided")

        text = _read_markdown_file(markdown_file_path)
        
        chunks = _create_chunks(
            text=text,
            document_id=state["document_id"],
            config=settings.chunking
        )

        return {
            **state,
            "chunks": chunks,
            "status": "chunked"
        }

    except Exception as e:
        return {
            **state,
            "error": f"Document chunking failed: {str(e)}",
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


def _create_chunks(text: str, document_id: str, config) -> List[DocumentChunk]:
    """Create document chunks based on configuration."""
    max_tokens = config.max_tokens
    overlap_tokens = config.overlap_tokens

    return _tiktoken_chunk(text, max_tokens, overlap_tokens)


def _tiktoken_chunk(text: str, max_tokens: int, overlap_tokens: int) -> List[DocumentChunk]:
    """Chunk using tiktoken tokenizer."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= max_tokens:
            return [DocumentChunk(
                chunk_id=0,
                text=text,
                start_char=0,
                end_char=len(text),
                token_count=total_tokens
            )]

        chunks = []
        chunk_id = 0
        start_token = 0

        while start_token < total_tokens:
            end_token = min(start_token + max_tokens, total_tokens)
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = encoding.decode(chunk_tokens)

            start_char = _token_to_char_position(text, tokens, start_token, encoding)
            end_char = _token_to_char_position(text, tokens, end_token, encoding)

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                token_count=len(chunk_tokens)
            )
            chunks.append(chunk)

            if end_token < total_tokens:
                start_token = end_token - overlap_tokens
            else:
                break

            chunk_id += 1

        return chunks
    except Exception as e:
        raise ValueError(f"Failed to chunk text: {str(e)}")




def _token_to_char_position(text: str, tokens: List[int], token_index: int, encoding) -> int:
    """Convert token index to character position in original text."""
    if token_index == 0:
        return 0
    if token_index >= len(tokens):
        return len(text)

    partial_tokens = tokens[:token_index]
    partial_text = encoding.decode(partial_tokens)
    return len(partial_text)


def test_chunking_with_markdown():
    """Test chunking with markdown file."""

    class MockChunkingConfig:
        max_tokens = 5128
        overlap_tokens = 200
        use_tiktoken = True

    class MockSettings:
        chunking = MockChunkingConfig()

    state: MultiAgentState = {
        "document_text": "docs/phases/system_progress_summary.md",
        "document_id": "test_doc_1",
        "chunks": None,
        "progressive_results": None,
        "consolidated_schema": None,
        "final_schema": None,
        "config": None,
        "extractions": None,
        "status": None,
        "error": None,
        "classification": None,
        "classification_confidence": None,
        "user_id": None,
        "feedback_context": None,
        "user_preferences": None
    }

    settings = MockSettings()
    result = chunk_document(state, settings)

    print(f"Status: {result['status']}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    else:
        print(f"Number of chunks created: {len(result['chunks'])}")
        for i, chunk in enumerate(result['chunks'][:3]):
            print(f"\nChunk {i}:")
            print(f"  Token count: {chunk.token_count}")
            print(f"  Text preview: {chunk.text[:200]}...")


if __name__ == "__main__":
    test_chunking_with_markdown()
