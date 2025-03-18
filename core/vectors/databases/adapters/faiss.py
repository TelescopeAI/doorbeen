from typing import List, Any

import faiss
import os
import pickle

from core.assistants.utils.embeddings.embedding import BaseEmbedding
from core.vectors.databases.base import VectorDBAdapter


class FaissAdapter(VectorDBAdapter):
    def connect(self) -> None:
        self.index_file = f"{self.storage_name}_index.faiss"
        self.texts_file = f"{self.storage_name}_texts.pkl"
        if os.path.exists(self.index_file):
            self.index = faiss.read_index(self.index_file)
            with open(self.texts_file, 'rb') as f:
                self.texts = pickle.load(f)
        else:
            self.index = faiss.IndexFlatL2(len(self.connection_params.get('dimension', 768)))
            self.texts = []

    def store_embeddings(self, embeddings: List[BaseEmbedding]) -> None:
        vectors = [e.vector for e in embeddings]
        self.index.add(vectors)
        self.texts.extend([e.text for e in embeddings])
        faiss.write_index(self.index, self.index_file)
        with open(self.texts_file, 'wb') as f:
            pickle.dump(self.texts, f)

    def search(self, query_vector: List[float], k: int) -> List[Any]:
        distances, indices = self.index.search([query_vector], k)
        return [self.texts[i] for i in indices[0]]