# examples/convert_with_granite_transformers.py

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel import vlm_model_specs

# 1. Path to your local PDF
source = "GSPP_0901_202508_Billing.pdf"

# 2. Use the Transformers-based Granite-Docling spec (Windows/CPU-friendly)
pipeline_options = VlmPipelineOptions(
    vlm_options=vlm_model_specs.GRANITEDOCLING_TRANSFORMERS
)

# 3. Map PDF input to the VLM pipeline with Granite-Docling Transformers
format_options = {
    InputFormat.PDF: PdfFormatOption(
        pipeline_cls=VlmPipeline,
        pipeline_options=pipeline_options
    )
}

# 4. Instantiate converter with custom options
converter = DocumentConverter(format_options=format_options)

# 5. Convert and export to Markdown
result = converter.convert(source)
print(result.document.export_to_markdown())
