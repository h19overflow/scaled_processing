"""
Document chunking node.
"""

from pathlib import Path
from typing import List

import tiktoken

from ..config.settings import Settings
from ..models.document import DocumentChunk
from ..models.state import PipelineState
from typing import Dict, Any
from prefect import task


@task(name="document-chunking",
      retries=2,
      retry_delay_seconds=10,
      description="Chunk document into processing batches.")
def chunk_document(state: PipelineState, settings: Settings) -> Dict[str, Any] :
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
        
        chunks = _create_chunks(
            text=text,
            document_id=state.document_id,
            config=settings.chunking
        )
        print(
            f"Created {len(chunks)} chunks from document {state.document_id}, each with up to {settings.chunking.max_tokens} tokens.,Type{type(chunks)}")

        return {
            "chunks": chunks,
            "document_text": text,  # Include actual document content for downstream nodes
            "status": "chunked"
        }

    except Exception as e:
        return {
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
    """Create document chunks using tiktoken tokenizer."""
    try:
        max_tokens = config.max_tokens
        overlap_tokens = config.overlap_tokens
        
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

