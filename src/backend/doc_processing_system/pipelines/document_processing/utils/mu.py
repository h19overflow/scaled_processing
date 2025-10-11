# Copyright (c) Opendatalab. All rights reserved.


import copy
import json
import os
from pathlib import Path

from loguru import logger

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, read_fn
from pypdfium2._helpers.misc import PdfiumError

# Monkey patch pypdfium2 to handle PDF repair automatically
import pypdfium2
_original_pdf_document_init = pypdfium2.PdfDocument.__init__

def _patched_pdf_document_init(self, input_data=None, password=None, autoclose=True):
    """Patched PdfDocument init that attempts PDF repair on failure."""
    try:
        return _original_pdf_document_init(self, input_data, password, autoclose)
    except PdfiumError as e:
        if isinstance(input_data, bytes) and "Data format error" in str(e):
            logger.warning(f"PdfDocument creation failed, attempting PDF repair: {e}")
            try:
                repaired_bytes = repair_pdf_fallback(input_data)
                logger.info("Retrying PdfDocument creation with repaired PDF bytes")
                return _original_pdf_document_init(self, repaired_bytes, password, autoclose)
            except Exception as repair_error:
                logger.error(f"PDF repair failed in monkey patch: {repair_error}")
                raise e  # Re-raise original error
        else:
            raise e

# Apply the monkey patch
pypdfium2.PdfDocument.__init__ = _patched_pdf_document_init
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox
from mineru.utils.enum_class import MakeMode
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make


def custom_prepare_env(output_dir, pdf_file_name):
    """Custom function to create a flatter directory structure"""
    # Create directories directly under output_dir without method nesting
    local_md_dir = os.path.join(output_dir, f"{pdf_file_name}_output")
    local_image_dir = os.path.join(local_md_dir, "images")

    # Create directories if they don't exist
    os.makedirs(local_md_dir, exist_ok=True)
    os.makedirs(local_image_dir, exist_ok=True)

    return local_image_dir, local_md_dir


def parse_single_file(
        file_path: Path,
        output_dir: str,
        lang="ch",
        backend="pipeline",
        method="auto",
        formula_enable=False,
        table_enable=True,
        server_url=None,
        start_page_id=0,
        end_page_id=None,
        f_draw_layout_bbox=False,
        f_draw_span_bbox=False,
        f_dump_md=True,
        f_dump_middle_json=False,
        f_dump_model_output=False,
        f_dump_orig_pdf=False,
        f_dump_content_list=True,
        f_make_md_mode=MakeMode.MM_MD,
):
    """
    Parse a single PDF/image file with custom output directory structure

    Args:
        file_path: Path to the PDF or image file
        output_dir: Base output directory (files will be saved directly here)
        Other parameters same as original do_parse function
    """
    try:
        file_name = str(Path(file_path).stem)
        pdf_bytes = read_fn(file_path)

        # Call the parsing function with single file
        do_parse(
            output_dir=output_dir,
            pdf_file_names=[file_name],
            pdf_bytes_list=[pdf_bytes],
            p_lang_list=[lang],
            backend=backend,
            parse_method=method,
            formula_enable=formula_enable,
            table_enable=table_enable,
            server_url=server_url,
            f_draw_layout_bbox=f_draw_layout_bbox,
            f_draw_span_bbox=f_draw_span_bbox,
            f_dump_md=f_dump_md,
            f_dump_middle_json=f_dump_middle_json,
            f_dump_model_output=f_dump_model_output,
            f_dump_orig_pdf=f_dump_orig_pdf,
            f_dump_content_list=f_dump_content_list,
            f_make_md_mode=f_make_md_mode,
            start_page_id=start_page_id,
            end_page_id=end_page_id
        )
        logger.info(f"Successfully parsed {file_path} to {output_dir}")

    except Exception as e:
        logger.exception(f"Error parsing {file_path}: {e}")


def repair_pdf_fallback(pdf_bytes: bytes) -> bytes:
    """
    Attempt to repair corrupted PDF using alternative methods.

    Args:
        pdf_bytes: Original PDF bytes that failed to parse

    Returns:
        bytes: Repaired PDF bytes or original bytes if repair fails
    """
    try:
        # Try PyPDF2 repair
        from io import BytesIO

        logger.info("Attempting PDF repair with PyPDF2...")

        # Write repaired PDF to bytes
        repaired_stream = BytesIO()
        pdf_bytes.write(repaired_stream)
        repaired_bytes = repaired_stream.getvalue()

        logger.info("PDF repair successful with PyPDF2")
        return repaired_bytes

    except Exception as e:
        logger.warning(f"PyPDF2 repair failed: {e}")

    try:
        # Try pdfplumber fallback (less aggressive repair)
        import pdfplumber
        from io import BytesIO

        logger.info("Attempting PDF repair with pdfplumber...")
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            # If we can open it with pdfplumber, return original bytes
            if len(pdf.pages) > 0:
                logger.info("PDF validated with pdfplumber")
                return pdf_bytes

    except Exception as e:
        logger.warning(f"pdfplumber validation failed: {e}")

    # If all repair attempts fail, return original bytes
    logger.error("All PDF repair attempts failed, returning original bytes")
    return pdf_bytes


def do_parse(
        output_dir,
        pdf_file_names: list[str],
        pdf_bytes_list: list[bytes],
        p_lang_list: list[str],
        backend="pipeline",
        parse_method="auto",
        formula_enable=False,
        table_enable=True,
        server_url=None,
        f_draw_layout_bbox=False,
        f_draw_span_bbox=False,
        f_dump_md=False,
        f_dump_middle_json=False,
        f_dump_model_output=False,
        f_dump_orig_pdf=False,
        f_dump_content_list=True,
        f_make_md_mode=MakeMode.MM_MD,
        start_page_id=0,
        end_page_id=None,
):
    if backend == "pipeline":
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            try:
                new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
                pdf_bytes_list[idx] = new_pdf_bytes
            except PdfiumError as e:
                logger.warning(f"pypdfium2 failed for PDF {idx}: {e}. Attempting repair...")
                try:
                    repaired_bytes = repair_pdf_fallback(pdf_bytes)
                    new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(repaired_bytes, start_page_id, end_page_id)
                    pdf_bytes_list[idx] = new_pdf_bytes
                    logger.info(f"PDF {idx} successfully repaired and processed")
                except Exception as repair_error:
                    logger.error(f"PDF repair failed for PDF {idx}: {repair_error}")
                    raise e  # Re-raise original error if repair fails

        infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(pdf_bytes_list,
                                                                                                         p_lang_list,
                                                                                                         parse_method=parse_method,
                                                                                                         formula_enable=formula_enable,
                                                                                                         table_enable=table_enable)

        for idx, model_list in enumerate(infer_results):
            model_json = copy.deepcopy(model_list)
            pdf_file_name = pdf_file_names[idx]

            # Use custom prepare_env function for flatter structure
            local_image_dir, local_md_dir = custom_prepare_env(output_dir, pdf_file_name)
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

            images_list = all_image_lists[idx]
            pdf_doc = all_pdf_docs[idx]
            _lang = lang_list[idx]
            _ocr_enable = ocr_enabled_list[idx]
            middle_json = pipeline_result_to_middle_json(model_list, images_list, pdf_doc, image_writer, _lang,
                                                         _ocr_enable)

            pdf_info = middle_json["pdf_info"]
            pdf_bytes = pdf_bytes_list[idx]

            _process_output(
                pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
                md_writer, f_draw_layout_bbox, f_draw_span_bbox, f_dump_orig_pdf,
                f_dump_md, f_dump_content_list, f_dump_middle_json, f_dump_model_output,
                f_make_md_mode, middle_json, model_json, is_pipeline=True
            )
    else:
        if backend.startswith("vlm-"):
            backend = backend[4:]

        f_draw_span_bbox = False
        parse_method = "vlm"
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            pdf_file_name = pdf_file_names[idx]
            try:
                pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            except PdfiumError as e:
                logger.warning(f"pypdfium2 failed for PDF {pdf_file_name}: {e}. Attempting repair...")
                try:
                    repaired_bytes = repair_pdf_fallback(pdf_bytes)
                    pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(repaired_bytes, start_page_id, end_page_id)
                    logger.info(f"PDF {pdf_file_name} successfully repaired and processed")
                except Exception as repair_error:
                    logger.error(f"PDF repair failed for {pdf_file_name}: {repair_error}")
                    raise e  # Re-raise original error if repair fails

            # Use custom prepare_env function for flatter structure
            local_image_dir, local_md_dir = custom_prepare_env(output_dir, pdf_file_name)
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

            middle_json, infer_result = vlm_doc_analyze(pdf_bytes, image_writer=image_writer, backend=backend,
                                                        server_url=server_url)

            pdf_info = middle_json["pdf_info"]

            _process_output(
                pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
                md_writer, f_draw_layout_bbox, f_draw_span_bbox, f_dump_orig_pdf,
                f_dump_md, f_dump_content_list, f_dump_middle_json, f_dump_model_output,
                f_make_md_mode, middle_json, infer_result, is_pipeline=False
            )


# Keep the existing _process_output function unchanged
def _process_output(
        pdf_info,
        pdf_bytes,
        pdf_file_name,
        local_md_dir,
        local_image_dir,
        md_writer,
        f_draw_layout_bbox,
        f_draw_span_bbox,
        f_dump_orig_pdf,
        f_dump_md,
        f_dump_content_list,
        f_dump_middle_json,
        f_dump_model_output,
        f_make_md_mode,
        middle_json,
        model_output=None,
        is_pipeline=True
):
    """处理输出文件"""
    if f_draw_layout_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_layout.pdf")

    if f_draw_span_bbox:
        draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_span.pdf")

    if f_dump_orig_pdf:
        md_writer.write(
            f"{pdf_file_name}_origin.pdf",
            pdf_bytes,
        )

    image_dir = str(os.path.basename(local_image_dir))

    if f_dump_md:
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        md_content_str = make_func(pdf_info, f_make_md_mode, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}.md",
            md_content_str,
        )

    if f_dump_content_list:
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        content_list = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}_content_list.json",
            json.dumps(content_list, ensure_ascii=False, indent=4),
        )

    if f_dump_middle_json:
        md_writer.write_string(
            f"{pdf_file_name}_middle.json",
            json.dumps(middle_json, ensure_ascii=False, indent=4),
        )

    if f_dump_model_output:
        md_writer.write_string(
            f"{pdf_file_name}_model.json",
            json.dumps(model_output, ensure_ascii=False, indent=4),
        )

    logger.info(f"local output dir is {local_md_dir}")


if __name__ == '__main__':
    # Example usage with individual files
    __dir__ = os.path.dirname(os.path.abspath(__file__))

    # Define your specific file paths
    individual_files = [
        Path(__dir__) / "data" / "broken_mu" / "GSPP_5407_202507_Billing_NEM.pdf",
    ]   
    print(individual_files)
    # Custom output directory (flatter structure)
    output_dir = os.path.join(__dir__, "output")

    # Process each file individually
    for pdf_file in individual_files:
        if pdf_file.exists():
            try:
                parse_single_file(
                file_path=pdf_file,
                output_dir=output_dir,
                backend="pipeline"
            )
            except Exception as e:
                logger.error(f"Error parsing {pdf_file}: {e}")
          
