"""
DoclingProcessor - Smart document extraction with format detection and path-based I/O.
Extracts rich markdown and images from documents using adaptive Docling pipelines.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption, PowerpointFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, PaginatedPipelineOptions
from docling_core.types.doc import ImageRefMode
from docling.datamodel.base_models import InputFormat
from docling.document_extractor import  DocumentExtractor
DOCLING_AVAILABLE = True
from typing import List
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str = Field(examples=["Widget"])
    sku: str = Field(examples=["WGT-001"])
    quantity: int = Field(examples=[2])
    unit_price: float = Field(examples=[19.99])
    subtotal: float = Field(examples=[39.98])
    tax: float = Field(examples=[2.40])
    notes: str = Field(default="", examples=["Urgent delivery"])


class InvoiceWithItems(BaseModel):
    invoice_number: str = Field(examples=["A123"])
    date: str = Field(examples=["2025-09-14"])
    supplier: str = Field(examples=["Acme Corp"])
    total: float = Field(examples=[123.45])
    vat: float = Field(examples=[3.45])
    line_items: List[LineItem] = Field(default_factory=list)

class DoclingProcessor:
    """Smart document processor with format detection and adaptive pipelines."""
    
    def __init__(self, base_extraction_path: str = "data/extractions/docling"):
        """Initialize DoclingProcessor with file-based I/O.
        
        Args:
            base_extraction_path: Base directory for temporary processing files
        """
        self.logger = logging.getLogger(__name__)
        self.temp_base_dir = Path(base_extraction_path)
        self.temp_base_dir.mkdir(parents=True, exist_ok=True)
        
        if not DOCLING_AVAILABLE:
            self.logger.error("Docling not available - install with: pip install docling")
            raise ImportError("Docling package is required but not installed")
        
        # Initialize adaptive converters
        self._converters = self._initialize_converters()
        
        self.logger.info("DoclingProcessor initialized with adaptive pipelines")
    
    def extract_document(self, raw_file_path: str, document_id: str) -> Dict[str, Any]:
        """Extract document to markdown and images with path-based output.
        
        Args:
            raw_file_path: Path to raw document file
            document_id: Unique document identifier
            user_id: User who uploaded document
            
        Returns:
            Dict with paths to extracted content: {
                "status": "completed",
                "processed_markdown_path": "/path/to/document.md",
                "extracted_images_dir": "/path/to/images/",
                "document_id": "doc_id",
                "file_info": {...}
            }
        """
        try:
            raw_path = Path(raw_file_path)
            if not raw_path.exists():
                return self._error_result("File not found", raw_file_path)
            
            self.logger.info(f"Starting Docling extraction for: {raw_path.name}")
            
            # Step 1: Detect document format and complexity
            doc_format = self._detect_document_format(raw_path)
            complexity = self._get_file_complexity(raw_path)
            
            self.logger.info(f"Document format: {doc_format}, complexity: {complexity}")
            
            # Step 2: Create processing directories
            processing_dir = self._create_processing_directory(document_id)
            images_dir = processing_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Step 3: Convert document with appropriate pipeline
            converter = self._get_converter_for_format(doc_format)
            conv_result = converter.convert(str(raw_path))
            
            if conv_result.status.name != "SUCCESS":
                return self._error_result("Docling conversion failed", raw_file_path, 
                                        error_details=f"Status: {conv_result.status.name}")
            
            # Step 4: Export markdown with embedded images
            markdown_path = processing_dir / f"{document_id}_docling.md"
            conv_result.document.save_as_markdown(
                str(markdown_path),
                image_mode=ImageRefMode.EMBEDDED
            )

            # Step 4: Export Tables JSON with embedded images
            tables_data = []
            for table_ix, table in enumerate(conv_result.document.tables):
                # Convert to DataFrame to strip metadata
                df = table.export_to_dataframe()

                # Create clean table object
                clean_table = {
                    "table_id": table_ix,
                    "data": df.to_dict('records'),  # Clean row data
                    "columns": df.columns.tolist(),  # Column names
                    "shape": df.shape  # Dimensions
                }
                tables_data.append(clean_table)

            # Save as clean JSON
            with open(processing_dir/f"{document_id}_table_json", "w", encoding="utf-8") as f:
                json.dump(tables_data, f, indent=2, ensure_ascii=False)
            # FUTURE - Add table extraction to docling
            print(f"Saved {len(tables_data)} tables as clean JSON!")
            # Create an extractor instance with allowed document formats
            # extractor = DocumentExtractor(
            #     allowed_formats=[InputFormat.IMAGE, InputFormat.PDF]
            # )
            # result = extractor.extract(
            #     source=str(raw_path),
            #     template=InvoiceWithItems,  # Import your model as shown previously
            # )
            #
            # # Save the page-level extracted results as JSON (each page is a dict)
            # extraction_json_path = processing_dir / f"{document_id}_extracted.json"
            # with open(extraction_json_path, "w", encoding="utf-8") as f:
            #     page_data = [page.extracted_data for page in result.pages]
            #     json.dump(page_data, f, indent=2, ensure_ascii=False)
            #
            # print(f"Saved structured extraction as {extraction_json_path.name}")
            #
            # # --- Optionally, save line items for all pages as a single flat list (if desired) ---
            # all_line_items = []
            # for page in result.pages:
            #     if 'line_items' in page.extracted_data:
            #         all_line_items.extend(page.extracted_data['line_items'])
            #
            # line_items_path = processing_dir / f"{document_id}_all_line_items.json"
            # with open(line_items_path, "w", encoding="utf-8") as f:
            #     json.dump(all_line_items, f, indent=2, ensure_ascii=False)
            #
            # print(f"Saved all line items as {line_items_path.name}")
            # # Step 6: Get file metadata
            file_info = self._get_file_info(raw_path, conv_result.document)
            #
            # self.logger.info(f"✅ Docling extraction completed: {markdown_path}")
            # self.logger.info(f"📁 Images extracted to: {images_dir}")
            #
            return {
                "status": "completed",
                "processed_markdown_path": str(markdown_path),
                "extracted_images_dir": str(images_dir),
                "document_id": document_id,
                "file_info": file_info,
                "processing_directory": str(processing_dir)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Docling extraction failed: {e}")
            return self._error_result("Extraction failed", raw_file_path, error_details=str(e))

    # HELPER FUNCTIONS
    def _initialize_converters(self) -> Dict[str, DocumentConverter]:
        """Initialize converters for different document formats."""
        # High-quality PDF configuration
        pdf_config = PdfPipelineOptions()
        pdf_config.images_scale = 2.0
        pdf_config.generate_page_images = True
        pdf_config.do_ocr = True
        
        # Balanced Office format configuration
        office_config = PaginatedPipelineOptions()
        office_config.images_scale = 1.5
        
        # Create converters
        converters = {
            "pdf": DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_config)}
            ),
            "docx": DocumentConverter(
                format_options={InputFormat.DOCX: WordFormatOption(pipeline_options=office_config)}
            ),
            "pptx": DocumentConverter(
                format_options={InputFormat.PPTX: PowerpointFormatOption(pipeline_options=office_config)}
            )
        }
        
        return converters
    
    def _detect_document_format(self, file_path: Path) -> str:
        """Detect document format from file extension."""
        extension = file_path.suffix.lower()
        format_map = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.pptx': 'pptx',
            '.html': 'html'
        }
        return format_map.get(extension, 'pdf')
    
    def _get_file_complexity(self, file_path: Path) -> str:
        """Determine file complexity based on size."""
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > 50:
            return "high"
        elif file_size_mb > 10:
            return "medium"
        else:
            return "low"
    
    def _get_converter_for_format(self, doc_format: str) -> DocumentConverter:
        """Get appropriate converter for document format."""
        return self._converters.get(doc_format, self._converters["pdf"])
    
    def _create_processing_directory(self, document_id: str) -> Path:
        """Create unique processing directory for document."""
        processing_dir = self.temp_base_dir / document_id
        processing_dir.mkdir(parents=True, exist_ok=True)
        return processing_dir
    
    def _extract_images_to_directory(self, document, images_dir: Path):
        """Extract document images to specified directory."""
        try:
            # Get document images
            if hasattr(document, 'pictures') and document.pictures:
                for i, picture in enumerate(document.pictures):
                    image_path = images_dir / f"image_{i}.png"
                    # Save image data to file
                    if hasattr(picture, 'image') and picture.image:
                        with open(image_path, 'wb') as f:
                            f.write(picture.image)
                        self.logger.debug(f"Extracted image: {image_path}")
            
            self.logger.info(f"Extracted {len(list(images_dir.glob('*.png')))} images")
            
        except Exception as e:
            self.logger.warning(f"Failed to extract images: {e}")
    
    def _get_file_info(self, file_path: Path, document) -> Dict[str, Any]:
        """Extract file metadata information."""
        try:
            file_stats = file_path.stat()
            
            # Get page count if available
            page_count = 0
            if hasattr(document, 'pages') and document.pages:
                page_count = len(document.pages)
            
            return {
                "filename": file_path.name,
                "file_type": file_path.suffix.lower().replace('.', ''),
                "file_size": file_stats.st_size,
                "page_count": page_count,
                "content_length": len(document.export_to_markdown()) if hasattr(document, 'export_to_markdown') else 0
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get file info: {e}")
            return {
                "filename": file_path.name,
                "file_type": file_path.suffix.lower().replace('.', ''),
                "file_size": 0,
                "page_count": 0,
                "content_length": 0
            }
    
    def _error_result(self, message: str, file_path: str, error_details: str = "") -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            "status": "error",
            "error": message,
            "error_details": error_details,
            "file_path": file_path,
            "message": f"{message}: {error_details}" if error_details else message
        }