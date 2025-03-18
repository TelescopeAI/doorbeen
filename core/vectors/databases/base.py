from typing import List, Any, Optional
from core.types.ts_model import TSModel
from core.assistants.utils.embeddings.embedding import BaseEmbedding
from core.vectors.databases.adapters.chromadb import ChromaAdapter
from core.vectors.databases.adapters.faiss import FaissAdapter
from core.vectors.databases.adapters.milvus import MilvusAdapter
from core.vectors.databases.adapters.weaviate import WeaviateAdapter
from core.vectors.databases.types import VectorDBTypes


class VectorDBAdapter(TSModel):
    connection_params: dict
    storage_name: str
    client: Optional[Any] = None
    collection: Optional[Any] = None
    vector_store: Optional[Any] = None

    def connect(self) -> None:
        raise NotImplementedError()

    def store_embeddings(self, embeddings: List[BaseEmbedding]) -> None:
        raise NotImplementedError()

    def search(self, query_vector: List[float], k: int) -> List[Any]:
        raise NotImplementedError()


class VectorDBService:
    @staticmethod
    def get_adapter(db_type: VectorDBTypes, storage_name: str) -> VectorDBAdapter:
        if db_type == VectorDBTypes.CHROMADB:
            adapter = ChromaAdapter(connection_params={'host': 'localhost', 'port': 8081},
                                    storage_name=storage_name).connect()
            return adapter
        elif db_type == VectorDBTypes.WEAVIATE:
            return WeaviateAdapter(connection_params={'host': 'localhost', 'port': 8081}, storage_name=storage_name)
        elif db_type == VectorDBTypes.FAISS:
            return FaissAdapter(connection_params={}, storage_name=storage_name)
        elif db_type == VectorDBTypes.MILVUS:
            return MilvusAdapter(connection_params={}, storage_name=storage_name)
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
