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

def cluster_geospatial_features(features: List[Dict], eps_km: float = 15.0, min_samples: int = 2) -> Dict:
    """
    Cluster GeoJSON features using DBSCAN over haversine distance.
    Returns the grouped clusters and mutates features to include `cluster_id` and `cluster_callsign`.
    """
    if not features:
        return {"features": features, "clusters": []}
        
    try:
        from sklearn.cluster import DBSCAN
    except ImportError:
        # Fallback if scikit-learn is not installed
        for feature in features:
            feature['properties']['cluster_id'] = -1
            feature['properties']['cluster_callsign'] = "ISOLATED SITE"
        return {"features": features, "clusters": []}
    
    # Extract coordinates in radians [latitude, longitude]
    coords_rad = np.radians([[f['properties']['center'][0], f['properties']['center'][1]] for f in features])
    
    db = DBSCAN(eps=eps_km / 6371.0088, min_samples=min_samples, metric='haversine')
    labels = db.fit_predict(coords_rad)
    
    NATO_ALPHABET = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL"]
    clusters_info = {}
    
    for i, feature in enumerate(features):
        cid = int(labels[i])
        
        callsign = f"{NATO_ALPHABET[cid]} CLUSTER" if 0 <= cid < len(NATO_ALPHABET) else f"CLUSTER_{cid}"
        if cid == -1:
            callsign = "ISOLATED SITE"
            
        feature['properties']['cluster_id'] = cid
        feature['properties']['cluster_callsign'] = callsign
        
        if cid not in clusters_info:
            clusters_info[cid] = {
                "cluster_id": cid,
                "callsign": callsign,
                "patch_count": 0,
                "lat_sum": 0.0,
                "lon_sum": 0.0
            }
        
        clusters_info[cid]["patch_count"] += 1
        clusters_info[cid]["lat_sum"] += feature['properties']['center'][0]
        clusters_info[cid]["lon_sum"] += feature['properties']['center'][1]
        
    clusters = []
    for cid, info in clusters_info.items():
        centroid = [
            info["lat_sum"] / info["patch_count"],
            info["lon_sum"] / info["patch_count"]
        ]
        clusters.append({
            "cluster_id": info["cluster_id"],
            "callsign": info["callsign"],
            "patch_count": info["patch_count"],
            "centroid": centroid
        })
        
    # Sort clusters: put named clusters first, then noise
    clusters.sort(key=lambda x: (x["cluster_id"] == -1, x["cluster_id"]))
    
    return {"features": features, "clusters": clusters}