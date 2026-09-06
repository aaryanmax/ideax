import json
import os
import numpy as np
from typing import List, Dict

class SemanticSearchEngine:
    def __init__(self, embedder, index_manager, metadata_path: str = None):
        self.embedder = embedder
        self.index_manager = index_manager
        self.metadata = {}
        self.faiss_map = {}
        self._text_model_512 = None
        self._tokenizer_512 = None
        if metadata_path and os.path.exists(metadata_path):
            self.load_metadata(metadata_path)
            
    def load_metadata(self, metadata_path: str):
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Support both new dict structure and legacy list
            if isinstance(data, dict):
                self.metadata = data
            elif isinstance(data, list):
                self.metadata = {v.get("patch_id", f"patch_{i}"): v for i, v in enumerate(data)}
            else:
                self.metadata = {}
        
        # Build strict mapping from FAISS integer ID to patch_id key
        self.faiss_map = {}
        for k, v in self.metadata.items():
            if "faiss_id" in v:
                self.faiss_map[int(v["faiss_id"])] = k
            
    def save_metadata(self, metadata_path: str):
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=4)

    def _embed_text_512(self, query: str) -> np.ndarray:
        if self._text_model_512 is None:
            from transformers import CLIPTokenizer, CLIPTextModelWithProjection
            self._tokenizer_512 = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
            self._text_model_512 = CLIPTextModelWithProjection.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
            self._text_model_512.eval()
        
        inputs = self._tokenizer_512([query], return_tensors="pt", padding=True, truncation=True)
        import torch
        with torch.no_grad():
            outputs = self._text_model_512(**inputs)
            emb = outputs.text_embeds
            emb = emb / emb.norm(p=2, dim=-1, keepdim=True)
        return emb.cpu().numpy()[0]
            
    def search_by_text(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        1. Encodes text via embedder.embed_text(query) or 512-dim text model based on index.d.
        2. Runs HNSW vector search.
        3. Resolves and returns top records formatted as GeoJSON-compatible dictionaries with similarity scores.
        """
        if self.index_manager.index.ntotal == 0:
            return []
            
        index_dim = self.index_manager.dim
        
        # 1. Encode text matching index dimension
        if index_dim == 512:
            query_embedding = self._embed_text_512(query)
        else:
            query_embedding = self.embedder.embed_text(query)
            if query_embedding.shape[-1] != index_dim:
                if query_embedding.shape[-1] > index_dim:
                    query_embedding = query_embedding[:index_dim]
                else:
                    query_embedding = np.pad(query_embedding, (0, index_dim - query_embedding.shape[-1]))
                norm = np.linalg.norm(query_embedding)
                if norm > 0:
                    query_embedding = query_embedding / norm
        
        # 2. Vector search
        distances, indices = self.index_manager.search(query_embedding, top_k=top_k)
        
        # 3. Resolve metadata — using strict faiss_id lookup
        results = []
        for score, idx in zip(distances[0], indices[0]):
            rec_key = self.faiss_map.get(int(idx))
            
            # Fallback for old catalogs that might be missing faiss_id
            if rec_key is None:
                if str(idx) in self.metadata:
                    rec_key = str(idx)
                elif f"patch_{idx}" in self.metadata:
                    rec_key = f"patch_{idx}"
            
            if rec_key is not None and rec_key in self.metadata:
                record = self.metadata[rec_key]
                
                # Extract geometry
                if "coordinates" in record and record["coordinates"]:
                    coords = record["coordinates"]
                elif "bounds" in record and record["bounds"]:
                    min_lat, min_lon, max_lat, max_lon = record["bounds"]
                    coords = [[
                        [min_lon, max_lat],
                        [max_lon, max_lat],
                        [max_lon, min_lat],
                        [min_lon, min_lat],
                        [min_lon, max_lat]
                    ]]
                else:
                    lat, lon = record.get("center", [28.6, 77.2])
                    coords = [[
                        [lon - 0.01, lat - 0.01],
                        [lon + 0.01, lat - 0.01],
                        [lon + 0.01, lat + 0.01],
                        [lon - 0.01, lat + 0.01],
                        [lon - 0.01, lat - 0.01],
                    ]]
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": coords
                    },
                    "properties": {
                        **record,
                        "patch_id": record.get("patch_id", rec_key),
                        "similarity_score": float(score),
                        "center": record.get("center"),
                        "file_path": record.get("file_path"),
                        "thumbnail_url": record.get("t2_thumbnail") or record.get("thumbnail_url"),
                        "t1_thumbnail": record.get("t1_thumbnail"),
                        "t2_thumbnail": record.get("t2_thumbnail"),
                        "t1_date": record.get("t1_date"),
                        "t2_date": record.get("t2_date"),
                        "site_name": record.get("site_name", "Surveillance Sector"),
                        "label": record.get("label", ""),
                        "col_off": record.get("col_off"),
                        "row_off": record.get("row_off")
                    }
                }
                results.append(feature)
        
        return results

    def find_similar_by_patch_id(self, patch_id: str, top_k: int = 6) -> List[Dict]:
        """
        Retrieves top_k similar patches excluding the source itself.
        """
        idx = None
        # Defensive lookup: explicitly grab faiss_id from metadata
        if isinstance(self.metadata, dict):
            record = self.metadata.get(patch_id)
            if not record:
                record = next((item for item in self.metadata.values() if item.get("patch_id") == patch_id), None)
            
            if record and "faiss_id" in record:
                idx = int(record["faiss_id"])
        else:
            record = next((item for item in self.metadata if item.get("patch_id") == patch_id), None)
            if record and "faiss_id" in record:
                idx = int(record["faiss_id"])
            
        if idx is None:
            # Fallback to string split if faiss_id is missing
            try:
                # E.g., for patch_0, patch_1 format
                idx = int(patch_id.split("_")[-1])
            except ValueError:
                return []
                
        # Read the embedding directly from FAISS index
        try:
            import faiss
            inner_index = faiss.downcast_index(self.index_manager.index.index) if hasattr(self.index_manager.index, 'index') else faiss.downcast_index(self.index_manager.index)
            vector = inner_index.reconstruct(idx)
        except Exception:
            return []
            
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        # Query FAISS
        # Request top_k + 1 to account for the seed patch itself
        distances, indices = self.index_manager.search(vector, top_k=top_k + 1)
        
        results = []
        for score, res_idx in zip(distances[0], indices[0]):
            rec_key = self.faiss_map.get(int(res_idx))
            
            if rec_key is None:
                if str(res_idx) in self.metadata:
                    rec_key = str(res_idx)
                elif f"patch_{res_idx}" in self.metadata:
                    rec_key = f"patch_{res_idx}"

            if rec_key is not None and rec_key in self.metadata:
                record = self.metadata[rec_key]
                if record.get("patch_id", rec_key) == patch_id:
                    continue  # exclude the source patch
                    
                # Extract geometry
                if "coordinates" in record and record["coordinates"]:
                    coords = record["coordinates"]
                elif "bounds" in record and record["bounds"]:
                    min_lat, min_lon, max_lat, max_lon = record["bounds"]
                    coords = [[
                        [min_lon, max_lat],
                        [max_lon, max_lat],
                        [max_lon, min_lat],
                        [min_lon, min_lat],
                        [min_lon, max_lat]
                    ]]
                else:
                    lat, lon = record.get("center", [28.6, 77.2])
                    coords = [[
                        [lon - 0.01, lat - 0.01],
                        [lon + 0.01, lat - 0.01],
                        [lon + 0.01, lat + 0.01],
                        [lon - 0.01, lat + 0.01],
                        [lon - 0.01, lat - 0.01],
                    ]]
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": coords
                    },
                    "properties": {
                        "patch_id": record.get("patch_id", rec_key),
                        "similarity_score": float(score),
                        "center": record.get("center"),
                        "file_path": record.get("file_path"),
                        "thumbnail_url": record.get("t2_thumbnail") or record.get("thumbnail_url"),
                        "t1_thumbnail": record.get("t1_thumbnail"),
                        "t2_thumbnail": record.get("t2_thumbnail"),
                        "col_off": record.get("col_off"),
                        "row_off": record.get("row_off")
                    }
                }
                results.append(feature)
                
                
        return results

class SearchEngineManager:
    def __init__(self, embedder):
        self.embedder = embedder
        self.engines = {}
        self.processed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed"))
        self.load_all_engines()
        
    def load_all_engines(self):
        import glob
        self.engines = {}
        index_files = glob.glob(os.path.join(self.processed_dir, "*.index"))
        for index_path in index_files:
            base_name = os.path.basename(index_path).replace(".index", "")
            metadata_path = os.path.join(self.processed_dir, f"{base_name}_metadata.json")
            if os.path.exists(metadata_path):
                self._load_engine(base_name, index_path, metadata_path)
                
    def _load_engine(self, name: str, index_path: str, metadata_path: str):
        print(f"[*] Loading dataset: {name}")
        from app.engine.vector_index import VectorIndexManager
        idx = VectorIndexManager(dim=768)
        idx.load(index_path)
        self.engines[name] = SemanticSearchEngine(self.embedder, idx, metadata_path)
        
    def reload_engine(self, name: str):
        index_path = os.path.join(self.processed_dir, f"{name}.index")
        metadata_path = os.path.join(self.processed_dir, f"{name}_metadata.json")
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            self._load_engine(name, index_path, metadata_path)
            
    def get_engine(self, name: str) -> SemanticSearchEngine:
        return self.engines.get(name)

