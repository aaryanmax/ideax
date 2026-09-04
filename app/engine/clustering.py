"""
Unsupervised clustering for tile discovery.
Groups semantically similar tiles in embedding space.
"""

import numpy as np
from typing import List, Dict, Optional
from app.models.schemas import TileMetadata


class TileClusterer:
    """
    KNN-based tile similarity search (fast, no training).
    For larger deployments, can swap in HDBSCAN.
    """
    
    def __init__(self, vector_index):
        """
        Args:
            vector_index: VectorIndex instance (has embeddings, tiles metadata)
        """
        self.vector_index = vector_index
        self.embeddings = vector_index.embeddings
        self.tiles = vector_index.tiles
    
    def find_similar_tiles(
        self,
        seed_tile_id: str,
        top_k: int = 10,
        distance_threshold: float = 0.4,
    ) -> List[Dict]:
        """
        Find tiles semantically similar to a seed tile using cosine distance.
        
        Args:
            seed_tile_id: Target tile ID to match against
            top_k: Max number of results
            distance_threshold: Cosine distance cutoff (0=identical, 1=opposite)
        
        Returns:
            List of dicts: {tile_id, score, metadata, distance}
        """
        # Find seed tile's embedding index
        seed_idx = None
        for i, tile in enumerate(self.tiles):
            if tile.tile_id == seed_tile_id:
                seed_idx = i
                break
        
        if seed_idx is None:
            raise ValueError(f"Tile not found: {seed_tile_id}")
        
        seed_embedding = self.embeddings[seed_idx]
        
        # Compute cosine distances to all tiles
        # For L2-normalized embeddings: distance = 1 - dot_product
        similarities = np.dot(self.embeddings, seed_embedding)  # shape (N,)
        distances = 1.0 - similarities
        
        # Sort by distance (ascending)
        sorted_indices = np.argsort(distances)
        results = []
        
        for idx in sorted_indices:
            if idx == seed_idx:  # skip self
                continue
            
            dist = distances[idx]
            if dist > distance_threshold:
                continue
            
            tile = self.tiles[idx]
            results.append({
                "tile_id": tile.tile_id,
                "score": float(1.0 - dist),  # similarity [0, 1]
                "distance": float(dist),     # distance [0, 1]
                "metadata": tile.dict(),     # full tile metadata
            })
            
            if len(results) >= top_k:
                break
        
        return results