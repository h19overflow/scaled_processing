"""
DoclingProcessor - Smart document extraction with Granite VLM (inline model) and format detection.
Extracts rich markdown and images from documents using Granite-Docling VLM pipelines.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any

from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption, PowerpointFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmPipelineOptions, PaginatedPipelineOptions
from docling.datamodel import vlm_model_specs
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling_core.types.doc import ImageRefMode

DOCLING_AVAILABLE = True

class DoclingProcessor:
    """Smart document processor with Granite-Docling VLM and format detection."""

    def __init__(self, temp_base_dir: str = "data/temp/docling", use_gpu: bool = True):
        """Initialize DoclingProcessor with VLM-based extraction.

        Args:
            temp_base_dir: Base directory for temporary processing files
            use_gpu: Whether to use GPU acceleration
        """
        self.logger = logging.getLogger(__name__)
        self.temp_base_dir = Path(temp_base_dir)
        self.temp_base_dir.mkdir(parents=True, exist_ok=True)
        self.use_gpu = use_gpu

        if not DOCLING_AVAILABLE:
            self.logger.error(
                "Docling not available - install with: pip install 'docling[transformers]' or 'docling[mlx]'"
            )
            raise ImportError("Docling package with VLM support is required but not installed")

        # Initialize converters
        self._converters = self._initialize_vlm_converters()

        self.logger.info(f"DoclingProcessor initialized with Granite-Docling VLM (GPU: {self.use_gpu})")

    def extract_document(self, raw_file_path: str, document_id: str) -> Dict[str, Any]:
        """Extract document using Granite-Docling VLM with path-based output.

        Args:
            raw_file_path: Path to raw document file
            document_id: Unique document identifier

        Returns:
            Dict with paths to extracted content
        """
        try:
            raw_path = Path(raw_file_path)
            if not raw_path.exists():
                return self._error_result("File not found", raw_file_path)

            self.logger.info(f"Starting Granite-Docling VLM extraction for: {raw_path.name}")

            # Detect document format
            doc_format = self._detect_document_format(raw_path)
            self.logger.info(f"Document format: {doc_format}")

            # Create processing directories
            processing_dir = self._create_processing_directory(document_id)
            images_dir = processing_dir / "images"
            images_dir.mkdir(exist_ok=True)

            # Get appropriate converter for the document format
            converter = self._get_converter_for_format(doc_format)

            # Convert first page with VLM for markdown extraction
            self.logger.info("Extracting first page with Granite VLM...")
            first_page_result = converter.convert(str(raw_path), page_range=(1, 1))

            if first_page_result.status.name != "SUCCESS":
                return self._error_result(
                    "Granite-Docling VLM conversion failed",
                    raw_file_path,
                    error_details=f"Status: {first_page_result.status.name}",
                )

            # Export markdown from first page
            markdown_path = processing_dir / f"{document_id}_granite_vlm.md"
            first_page_result.document.save_as_markdown(
                str(markdown_path), image_mode=ImageRefMode.EMBEDDED
            )

            # Clean markdown placeholders
            self._clean_markdown_vlm_placeholders(markdown_path)

            # Extract tables from full document (separate conversion)
            tables_data = []
            try:
                self.logger.info("Extracting tables from full document...")
                full_result = converter.convert(str(raw_path))

                if full_result.status.name == "SUCCESS":
                    for idx, table in enumerate(full_result.document.tables):
                        df = table.export_to_dataframe()
                        tables_data.append({
                            "table_id": idx,
                            "data": df.to_dict("records"),
                        })

                    # Save tables to JSON
                    tables_path = processing_dir / f"{document_id}_tables.json"
                    with open(tables_path, "w", encoding="utf-8") as f:
                        json.dump(tables_data, f, indent=2, ensure_ascii=False)

                    self.logger.info(f"Extracted {len(tables_data)} tables from full document")
                else:
                    self.logger.warning(f"Full document conversion failed: {full_result.status.name}")

            except Exception as e:
                self.logger.warning(f"Table extraction failed: {e}")

            # File metadata from first page result
            file_info = self._get_file_info(raw_path, first_page_result.document)

            return {
                "status": "completed",
                "processed_markdown_path": str(markdown_path),
                "extracted_images_dir": str(images_dir),
                "document_id": document_id,
                "file_info": file_info,
                "processing_directory": str(processing_dir),
                "extraction_method": "granite_vlm",
            }

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return self._error_result("VLM extraction failed", raw_file_path, error_details=str(e))

    def _initialize_vlm_converters(self) -> Dict[str, DocumentConverter]:
        """Initialize converters using proper Granite-Docling VLM specifications."""
        try:
            # Use the correct Granite VLM model spec based on system capabilities
            if self.use_gpu:
                self.logger.info("Initializing Granite VLM with GPU acceleration...")
                vlm_options = vlm_model_specs.GRANITEDOCLING_TRANSFORMERS
            else:
                # For CPU or Apple Silicon, try MLX first then fallback
                try:
                    self.logger.info("Trying MLX backend for Granite VLM...")
                    vlm_options = vlm_model_specs.GRANITEDOCLING_MLX
                    self.logger.info("Using MLX backend successfully")
                except (ImportError, AttributeError) as e:
                    self.logger.info(f"MLX not available ({e}), falling back to transformers")
                    vlm_options = vlm_model_specs.GRANITEDOCLING_TRANSFORMERS

            # Configure VLM pipeline with performance optimizations
            vlm_pipeline_options = VlmPipelineOptions(
                vlm_options=vlm_options,
                generate_page_images=True,
                generate_picture_images=False,  # Disable for faster processing
                # Set timeout to avoid hanging
                document_timeout=300,  # 5 minutes max per document
            )

            # Office format options with reduced scale for performance
            office_opts = PaginatedPipelineOptions()
            office_opts.images_scale = 1.0

            self.logger.info("Granite VLM converters initialized successfully")

            return {
                "pdf": DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(
                            pipeline_cls=VlmPipeline,
                            pipeline_options=vlm_pipeline_options
                        )
                    }
                ),
                "docx": DocumentConverter(
                    format_options={InputFormat.DOCX: WordFormatOption(pipeline_options=office_opts)}
                ),
                "pptx": DocumentConverter(
                    format_options={InputFormat.PPTX: PowerpointFormatOption(pipeline_options=office_opts)}
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to initialize VLM converters: {e}")
            # Fallback to basic converter without VLM
            self.logger.warning("Falling back to basic document converter without VLM")
            office_opts = PaginatedPipelineOptions()
            return {
                "pdf": DocumentConverter(),
                "docx": DocumentConverter(
                    format_options={InputFormat.DOCX: WordFormatOption(pipeline_options=office_opts)}
                ),
                "pptx": DocumentConverter(
                    format_options={InputFormat.PPTX: PowerpointFormatOption(pipeline_options=office_opts)}
                ),
            }

    def _clean_markdown_vlm_placeholders(self, markdown_path: Path):
        """Remove VLM-specific placeholders from markdown."""
        try:
            text = markdown_path.read_text(encoding="utf-8")
            import re
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
            markdown_path.write_text(text, encoding="utf-8")
            self.logger.info(f"Cleaned markdown: {markdown_path.name}")
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    def _detect_document_format(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        return {'.pdf':'pdf','.docx':'docx','.pptx':'pptx'}.get(ext,'pdf')

    def _get_converter_for_format(self, fmt: str) -> DocumentConverter:
        return self._converters.get(fmt, self._converters['pdf'])

    def _create_processing_directory(self, doc_id: str) -> Path:
        p = self.temp_base_dir / doc_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _get_file_info(self, file_path: Path, document) -> Dict[str, Any]:
        try:
            stats = file_path.stat()
            pages = len(document.pages) if hasattr(document, 'pages') else 0
            length = len(document.export_to_markdown()) if hasattr(document,'export_to_markdown') else 0
            return {"filename":file_path.name, "file_size":stats.st_size, "page_count":pages, "content_length":length}
        except:
            return {"filename":file_path.name, "file_size":0, "page_count":0, "content_length":0}

    def _error_result(self, message: str, path: str, error_details: str = "") -> Dict[str, Any]:
        return {"status":"error","error":message,"error_details":error_details,"file_path":path}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    proc = DoclingProcessor(temp_base_dir="data/temp/granite_vlm", use_gpu=True)
    result = proc.extract_document("path/to/doc.pdf", "my_doc_001")
    print(result)
