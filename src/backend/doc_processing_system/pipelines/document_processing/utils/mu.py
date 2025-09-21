# Copyright (c) Opendatalab. All rights reserved.
import copy
import json
import os
from pathlib import Path

from loguru import logger

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, read_fn
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
            new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            pdf_bytes_list[idx] = new_pdf_bytes

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
            pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)

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
        Path(__dir__) / "pdfs" / "GSPP_5407_202507_Billing.pdf",
    ]

    # Custom output directory (flatter structure)
    output_dir = os.path.join(__dir__, "output")

    # Process each file individually
    for pdf_file in individual_files:
        if pdf_file.exists():
            parse_single_file(
                file_path=pdf_file,
                output_dir=output_dir,
                backend="pipeline"
            )
            # Output will be: output/document1_output/document1.md
            #                 output/document2_output/document2.md
