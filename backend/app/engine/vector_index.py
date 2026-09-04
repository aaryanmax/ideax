import faiss
import numpy as np
from typing import Tuple, Optional

class VectorIndexManager:
    def __init__(self, dim: int = 768, m: int = 32, metric: str = 'cosine'):
        """
        Initializes an HNSW flat index using METRIC_INNER_PRODUCT (for cosine similarity on normalized vectors).
        """
        self.dim = dim
        self.m = m
        self.metric = metric
        
        # faiss.METRIC_INNER_PRODUCT combined with L2 normalization yields cosine similarity
        hnsw_index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_INNER_PRODUCT)
        # Wrap with IndexIDMap to support custom IDs (required if we want to pass specific IDs)
        self.index = faiss.IndexIDMap(hnsw_index)
        
    def add_vectors(self, vectors: np.ndarray, ids: Optional[np.ndarray] = None):
        """
        Ensures vectors are cast to float32 and L2-normalized before insertion.
        """
        vectors = np.array(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = np.expand_dims(vectors, axis=0)
            
        # L2 normalize for cosine similarity
        faiss.normalize_L2(vectors)
        
        if ids is None:
            # Generate sequential IDs based on current total
            start_id = self.index.ntotal
            ids = np.arange(start_id, start_id + vectors.shape[0], dtype=np.int64)
        else:
            ids = np.array(ids, dtype=np.int64)
            
        self.index.add_with_ids(vectors, ids)
        
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Queries top-k nearest neighbors, returning distances (similarities) and index IDs.
        """
        query_vector = np.array(query_vector, dtype=np.float32)
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
            
        # L2 normalize query
        faiss.normalize_L2(query_vector)
        
        # distances returned are dot products (similarities) since we use METRIC_INNER_PRODUCT
        distances, indices = self.index.search(query_vector, top_k)
        return distances, indices

    def save(self, index_path: str):
        """Native FAISS serialization to write index."""
        faiss.write_index(self.index, index_path)
        
    def load(self, index_path: str):
        """Native FAISS serialization to load index."""
        self.index = faiss.read_index(index_path)
        self.dim = self.index.d
