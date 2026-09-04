"""
app/engine/vector_index.py — adapted to load K's real satellite data pipeline output.
"""

import faiss
import numpy as np
import json
from pathlib import Path
from typing import Optional, List, Tuple
from app.models.schemas import TileMetadata, SearchResult
import time

class VectorIndex:
    def __init__(self, index_path: str, metadata_path: str, embeddings_path: str):
        """
        Load K's real FAISS index + metadata + embeddings.
        
        Args:
            index_path: Path to satellite_tiles.index (from step04/step08)
            metadata_path: Path to metadata.json (append output from step06)
            embeddings_path: Path to embeddings.npy (from step07 after step08 rebuild)
        """
        start = time.perf_counter()
        
        # Verify all files exist
        for p in [index_path, metadata_path, embeddings_path]:
            if not Path(p).exists():
                raise FileNotFoundError(f"Missing: {p}")
        
        # Load FAISS index
        self.index = faiss.read_index(index_path)
        self.ntotal = self.index.ntotal
        
        # Load metadata catalog
        with open(metadata_path) as f:
            self.metadata_list = json.load(f)
        
        # Load embeddings matrix
        self.embeddings = np.load(embeddings_path, mmap_mode='r')  # mmap for large files
        
        # Validate consistency (critical!)
        if len(self.metadata_list) != self.ntotal:
            raise RuntimeError(
                f"Metadata has {len(self.metadata_list)} entries but FAISS has {self.ntotal} vectors"
            )
        if self.embeddings.shape[0] != self.ntotal:
            raise RuntimeError(
                f"Embeddings has {self.embeddings.shape[0]} rows but FAISS has {self.ntotal} vectors"
            )
        if self.embeddings.shape[1] != 512:
            raise RuntimeError(
                f"Embeddings dim is {self.embeddings.shape[1]}, expected 512"
            )
        
        # Parse all metadata into Pydantic objects
        self.tiles = []
        for m in self.metadata_list:
            try:
                tile = TileMetadata(**m)
                self.tiles.append(tile)
            except Exception as e:
                print(f"[WARNING] Failed to parse metadata entry {m}: {e}")
        
        elapsed = time.perf_counter() - start
        print(f"[VectorIndex] Loaded {self.ntotal} tiles in {elapsed:.2f}s")
        print(f"  - FAISS index: {index_path}")
        print(f"  - Metadata: {len(self.tiles)} entries")
        print(f"  - Embeddings: {self.embeddings.shape}")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        date_range_start: Optional[str] = None,
        date_range_end: Optional[str] = None,
        sensor_filter: Optional[str] = None,
    ) -> Tuple[List[SearchResult], float]:
        """
        Semantic search via FAISS cosine similarity.
        
        Args:
            query_vector: Shape (512,) or (1, 512), L2-normalized
            top_k: Number of results
            date_range_start: ISO 8601 filter
            date_range_end: ISO 8601 filter
            sensor_filter: "Sentinel-2 L2A", "Sentinel-1 SAR", etc.
        
        Returns:
            (list of SearchResult, latency_ms)
        """
        # Reshape if needed
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Ensure L2-normalized (critical for cosine similarity with IndexFlatIP)
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm
        
        start = time.perf_counter()
        
        # FAISS search: returns (distances, indices)
        # For IndexFlatIP on normalized vectors, distance = cosine similarity
        distances, indices = self.index.search(query_vector, top_k * 3)  # fetch more, then filter
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            
            tile = self.tiles[idx]
            
            # Apply optional filters
            if date_range_start and tile.acquisition_date < date_range_start:
                continue
            if date_range_end and tile.acquisition_date > date_range_end:
                continue
            if sensor_filter and tile.sensor != sensor_filter:
                continue
            
            score = float(dist)
            score = max(0.0, min(1.0, score))

            results.append(
                SearchResult(
                    tile_id=tile.tile_id,
                    score=score,  # cosine similarity [0, 1]
                    metadata=tile,
                )
            )
            
            if len(results) >= top_k:
                break
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        return results, elapsed_ms

    def get_embedding(self, embedding_index: int) -> np.ndarray:
        """
        Retrieve a specific embedding by index (for clustering/change detection).
        Used by clustering and change detection modules.
        """
        if embedding_index >= self.embeddings.shape[0]:
            raise IndexError(f"embedding_index {embedding_index} out of range")
        return self.embeddings[embedding_index]

    def get_embeddings_batch(self, indices: List[int]) -> np.ndarray:
        """
        Retrieve multiple embeddings for clustering.
        Returns shape (len(indices), 512).
        """
        return self.embeddings[indices]