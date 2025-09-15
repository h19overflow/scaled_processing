from src.backend.doc_processing_system.pipelines.document_processing.utils.docling_processor import DoclingProcessor
if __name__ == "__main__":

    try:
        processor = DoclingProcessor()
        file_path = r"/data/documents/CODB-ENGLISH-Utilities.pdf"

        result = processor.extract_document(file_path,"test")
        print(result)
    except Exception as e:
        print(e)