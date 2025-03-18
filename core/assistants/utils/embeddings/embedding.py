from langchain_community.embeddings import OllamaEmbeddings
from typing import List, Generator, Optional
import logging
import time

from core.commons.documents.processor import TextChunk
from core.types.ts_model import TSModel
from langchain_core.embeddings import Embeddings as LangchainEmbeddings



# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class BaseEmbedding(TSModel):
    vector: List[float]
    text: str
    metadata: dict


class NomicEmbedder(TSModel):
    model_name: str = "nomic-embed-text"
    embeddings: Optional[OllamaEmbeddings] = None

    @staticmethod
    def create() -> "NomicEmbedder":
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        logging.info(f"Initialized NomicEmbedder with model: {"nomic-embed-text"}")
        return NomicEmbedder(embeddings=embeddings)

    def generate_embeddings(self, chunks: List[TextChunk]) -> Generator[BaseEmbedding, None, None]:
        start_time = time.time()
        total_chunks = len(chunks)
        logging.info(f"Starting to generate embeddings for {total_chunks} chunks")

        for i, chunk in enumerate(chunks, 1):
            chunk_start_time = time.time()
            logging.info(f"Processing chunk {i}/{total_chunks}")
            try:
                # Generate embedding for each chunk
                vector = self.embeddings.embed_query(chunk.text)
                logging.info(f"Successfully generated embedding for chunk {i}")

                # Create an Embedding object
                chunk_embedding = BaseEmbedding(
                    vector=vector,
                    text=chunk.text,
                    metadata=chunk.metadata
                )
                chunk_end_time = time.time()
                logging.info(f"Chunk {i} processed in {chunk_end_time - chunk_start_time:.2f} seconds")
                yield chunk_embedding
            except Exception as e:
                logging.error(f"Error generating embedding for chunk {i}: {str(e)}")

        end_time = time.time()
        logging.info(f"Finished generating embeddings for {total_chunks} chunks in {end_time - start_time:.2f} seconds")


class NomicEmbeddingFunction(LangchainEmbeddings):
    def __init__(self):
        self.nomic_embedder = NomicEmbedder.create()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            chunk = TextChunk(text=text, metadata={})
            embedding = next(self.nomic_embedder.generate_embeddings([chunk]))
            embeddings.append(embedding.vector)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        chunk = TextChunk(text=text, metadata={})
        embedding = next(self.nomic_embedder.generate_embeddings([chunk]))
        return embedding.vector


if __name__ == "__main__":
    embedder = NomicEmbedder.create()
    chunks = [
        TextChunk(
            text="This is a test sentence",
            metadata={"source": "test"}
        )
    ]
    logging.info("Starting embedding generation in main")
    for i, embedding in enumerate(embedder.generate_embeddings(chunks), 1):
        logging.info(f"Embedding {i} generated")
        print(f"Embedding for chunk from {embedding.metadata['source']}:")
        print(embedding.vector[:10])
        print("-" * 50)
    logging.info("Finished embedding generation in main")
