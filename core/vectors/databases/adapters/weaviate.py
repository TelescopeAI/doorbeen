from typing import List, Any

from core.assistants.utils.embeddings.embedding import BaseEmbedding
from core.vectors.databases.base import VectorDBAdapter


class WeaviateAdapter(VectorDBAdapter):
    def connect(self) -> None:
        import weaviate
        self.client = weaviate.Client(**self.connection_params)
        if not self.client.schema.exists(self.storage_name):
            self.client.schema.create_class({
                "class": self.storage_name,
                "vectorizer": "none"
            })

    def store_embeddings(self, embeddings: List[BaseEmbedding]) -> None:
        with self.client.batch as batch:
            for e in embeddings:
                batch.add_data_object(
                    data_object={"text": e.text, **e.metadata},
                    class_name=self.storage_name,
                    vector=e.vector
                )

    def search(self, query_vector: List[float], k: int) -> List[Any]:
        result = (
            self.client.query
            .get(self.storage_name, ["text"])
            .with_near_vector({"vector": query_vector})
            .with_limit(k)
            .do()
        )
        return [item['text'] for item in result['data']['Get'][self.storage_name]]