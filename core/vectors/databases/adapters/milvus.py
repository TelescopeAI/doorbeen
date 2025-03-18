from typing import List, Any

from core.assistants.utils.embeddings.embedding import BaseEmbedding
from core.vectors.databases.base import VectorDBAdapter
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType


class MilvusAdapter(VectorDBAdapter):
    def connect(self) -> None:
        connections.connect(**self.connection_params)
        if Collection.has_collection(self.storage_name):
            self.collection = Collection(self.storage_name)
        else:
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768)
            ]
            schema = CollectionSchema(fields, f"{self.storage_name} collection")
            self.collection = Collection(self.storage_name, schema)

    def store_embeddings(self, embeddings: List[BaseEmbedding]) -> None:
        entities = [
            [e.text for e in embeddings],
            [e.vector for e in embeddings]
        ]
        self.collection.insert(entities)

    def search(self, query_vector: List[float], k: int) -> List[Any]:
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["text"]
        )
        return [hit.entity.get('text') for hit in results[0]]