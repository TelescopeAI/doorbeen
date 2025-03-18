from typing import List, Any

from core.assistants.utils.embeddings.embedding import BaseEmbedding
from core.vectors.databases.base import VectorDBAdapter
import chromadb
from langchain_chroma import Chroma

class ChromaAdapter(VectorDBAdapter):
    def connect(self) -> "ChromaAdapter":
        self.client = chromadb.HttpClient(**self.connection_params)
        self.collection = self.client.get_or_create_collection(name=self.storage_name)
        return self

    def store_embeddings(self, embeddings: List[BaseEmbedding]) -> None:
        self.collection.add(
            embeddings=[e.vector for e in embeddings],
            documents=[e.text for e in embeddings],
            metadatas=[e.metadata for e in embeddings],
            ids=[str(i) for i in range(len(embeddings))]
        )

    def search(self, query_vector: List[float], k: int) -> List[Any]:
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k
        )
        return results['documents'][0]

    def get_langchain_vectorstore(self, embedding_function):
        """
        Retrieve a LangChain Chroma vector store for this client.
        
        :param embedding_function: The embedding function to use with the vector store.
        :return: A LangChain Chroma vector store.
        """
        return Chroma(
            client=self.client,
            collection_name=self.storage_name,
            embedding_function=embedding_function
        )
