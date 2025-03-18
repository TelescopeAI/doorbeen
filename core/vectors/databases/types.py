from enum import Enum


class VectorDBTypes(Enum):
    CHROMADB = "chromadb"
    FAISS = "faiss"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    MILVUS = "milvus"
    QDRANT = "qdrant"
    SPARSE_ARRAY = "sparse_array"