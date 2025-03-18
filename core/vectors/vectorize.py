import logging
import time
from typing import Any, Generator, List

from core.assistants.utils.embeddings.embedding import BaseEmbedding, NomicEmbedder
from core.commons.documents.processor import DocumentProcessor
from core.types.ts_model import TSModel
from core.vectors.databases.adapters.chromadb import ChromaAdapter
from core.vectors.databases.adapters.faiss import FaissAdapter
from core.vectors.databases.adapters.milvus import MilvusAdapter
from core.vectors.databases.adapters.weaviate import WeaviateAdapter
from core.vectors.databases.types import VectorDBTypes
from core.vectors.databases.base import VectorDBService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VectorizeDocuments(TSModel):

    def __init__(self, **data: Any):
        super().__init__(**data)

    def vectorize(self) -> Generator[BaseEmbedding, None, None]:
        start_time = time.time()
        processor = DocumentProcessor(chunk_size=3000, chunk_overlap=500)
        pdf_folder = "/Users/zinomex/Desktop/Telescope/observer/dummy/documents"
        logging.info(f"Processing PDFs in folder: {pdf_folder}")

        pdf_start_time = time.time()
        pdfs = list(processor.load_pdfs(pdf_folder, file_count=1))
        pdf_end_time = time.time()
        logging.info(f"Loaded {len(pdfs)} PDFs in {pdf_end_time - pdf_start_time:.2f} seconds")

        chunk_start_time = time.time()
        chunks = list(processor.chunk_documents(pdfs))
        chunk_end_time = time.time()
        logging.info(f"Created {len(chunks)} chunks in {chunk_end_time - chunk_start_time:.2f} seconds")

        nomic_embedder = NomicEmbedder.create()
        embedding_start_time = time.time()
        embedding_count = 0
        for embedding in nomic_embedder.generate_embeddings(chunks):
            embedding_count += 1
            logging.info(f"Generated embedding {embedding_count} for chunk from {embedding.metadata['source']}")
            logging.info(f"First 10 elements of the embedding vector: {embedding.vector[:10]}")
            yield embedding

        embedding_end_time = time.time()
        logging.info(
            f"Generated {embedding_count} embeddings in {embedding_end_time - embedding_start_time:.2f} seconds")

        total_time = time.time() - start_time
        logging.info(f"Total vectorization process took {total_time:.2f} seconds")

    def store_embeddings(self, embeddings: List[BaseEmbedding], db_type: VectorDBTypes, storage_name: str) -> None:
        logging.info(f"Storing {len(embeddings)} embeddings in {db_type.value} database")
        start_time = time.time()

        adapter = VectorDBService.get_adapter(db_type, storage_name)
        adapter.connect()
        adapter.store_embeddings(embeddings)

        end_time = time.time()
        logging.info(f"Stored embeddings in {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    vectorizer = VectorizeDocuments()
    embeddings = list(vectorizer.vectorize())
    vectorizer.store_embeddings(embeddings, VectorDBTypes.CHROMADB, "my_embeddings")

