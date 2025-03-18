import os
from typing import List, Generator, Optional
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.types.ts_model import TSModel


class PDFDocument(TSModel):
    file_path: str
    content: str


class TextChunk(TSModel):
    text: str
    metadata: dict = {}


class DocumentProcessor(TSModel):
    chunk_size: int = 1000
    chunk_overlap: int = 200

    def load_pdfs(self, folder_path: str, file_count: Optional[int] = None) -> Generator[PDFDocument, None, None]:
        print(f"Starting to process PDFs in folder: {folder_path}")
        try:
            pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
            if file_count is not None:
                pdf_files = pdf_files[:file_count]
            
            for filename in pdf_files:
                file_path = os.path.join(folder_path, filename)
                print(f"Processing PDF: {file_path}")
                try:
                    reader = PdfReader(file_path)
                    content = ""
                    for page in reader.pages:
                        content += page.extract_text()
                    pdf_doc = PDFDocument(file_path=file_path, content=content)
                    print(f"Successfully processed PDF: {file_path}")
                    yield pdf_doc
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
        except PermissionError:
            print(f"Permission denied: Unable to access {folder_path}")
        except FileNotFoundError:
            print(f"Folder not found: {folder_path}")
        except Exception as e:
            print(f"An error occurred while loading PDFs: {str(e)}")

    def chunk_documents(self, documents: List[PDFDocument]) -> Generator[TextChunk, None, None]:
        print("Starting to chunk documents")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        for doc in documents:
            print(f"Chunking document: {doc.file_path}")
            doc_chunks = text_splitter.split_text(doc.content)
            for i, chunk in enumerate(doc_chunks):
                text_chunk = TextChunk(
                    text=chunk,
                    metadata={"source": doc.file_path, "chunk_index": i}
                )
                print(f"Created chunk {i} from {doc.file_path}")
                yield text_chunk
        print("Finished chunking all documents")

if __name__ == "__main__":
    processor = DocumentProcessor()
    pdf_folder = "/Users/zinomex/Desktop/Telescope/observer/dummy/documents"
    print(f"Processing PDFs in folder: {pdf_folder}")
    
    pdfs = list(processor.load_pdfs(pdf_folder))
    print(f"Loaded {len(pdfs)} PDFs")
    
    chunks = list(processor.chunk_documents(pdfs))
    print(f"Created {len(chunks)} chunks in total")
    
    for chunk in chunks:
        try:
            print(f"Chunk from {chunk.metadata['source']}:")
            print(chunk.text[:100].encode('utf-8', errors='ignore').decode('utf-8') + "...")
        except Exception as e:
            print(f"Error printing chunk: {str(e)}")
        print("-" * 50)