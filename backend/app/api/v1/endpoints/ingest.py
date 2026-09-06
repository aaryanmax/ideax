"""
Incremental Ingest Endpoint
Adds a new GeoTIFF/JP2 scene to the FAISS index without a full rebuild.
Accepts a server-side file path so it stays fully offline and demo-safe.
"""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from PIL import Image
import rasterio
import numpy as np

from app.engine.embedder import Embedder
from app.engine.vector_index import VectorIndexManager

router = APIRouter()

# ── Resolve paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

import threading

_embedder: Optional[Embedder] = None
_embedder_lock = threading.Lock()

def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                _embedder = Embedder()
    return _embedder


class IngestRequest(BaseModel):
    file_path: str
    tile_id: Optional[str] = None
    dataset: Optional[str] = "mumbai"
    acquisition_date: Optional[str] = None
    sensor: Optional[str] = "Sentinel-2 L2A"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cloud_cover_pct: Optional[float] = 0.0


@router.post("")
def ingest_scene(request: IngestRequest):
    fpath = request.file_path
    if not os.path.isabs(fpath):
        fpath = os.path.join(PROJECT_ROOT, fpath)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=400, detail=f"File not found: {fpath}")

    ds = (request.dataset or "mumbai").lower()
    
    idx_path = os.path.join(PROJECT_ROOT, "data", "processed", f"{ds}.index")
    meta_path = os.path.join(PROJECT_ROOT, "data", "processed", f"{ds}_metadata.json")

    if not os.path.exists(idx_path):
        raise HTTPException(status_code=500, detail=f"Index not found: {idx_path}. Run the build pipeline first.")

    try:
        with rasterio.open(fpath) as src:
            arr = src.read(
                [1, 2, 3] if src.count >= 3 else [1],
                out_shape=(min(3, src.count), 512, 512),
                resampling=rasterio.enums.Resampling.bilinear
            )
            crs = src.crs
            if request.latitude is None or request.longitude is None:
                bounds = src.bounds
                cx = (bounds.left + bounds.right) / 2
                cy = (bounds.bottom + bounds.top) / 2
                if crs and crs.to_epsg() != 4326:
                    from rasterio.warp import transform as reproject_pt
                    lons, lats = reproject_pt(crs, "EPSG:4326", [cx], [cy])
                    center_lat, center_lon = float(lats[0]), float(lons[0])
                else:
                    center_lat, center_lon = float(cy), float(cx)
            else:
                center_lat = request.latitude
                center_lon = request.longitude
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read raster: {e}")

    arr = np.transpose(arr, (1, 2, 0))
    if arr.dtype != np.uint8:
        import cv2
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    if arr.shape[2] == 1:
        import cv2
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    pil_img = Image.fromarray(arr[:, :, :3])

    emb = _get_embedder().embed_image(pil_img)

    idx_mgr = VectorIndexManager(dim=emb.shape[0])
    idx_mgr.load(idx_path)
    new_id = idx_mgr.index.ntotal
    tile_id = request.tile_id or f"patch_{new_id}"

    idx_mgr.add_vectors(emb.reshape(1, -1), ids=np.array([new_id], dtype=np.int64))
    idx_mgr.save(idx_path)

    metadata: dict = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    import datetime
    metadata[str(new_id)] = {
        "patch_id": tile_id,
        "file_path": fpath,
        "center": [center_lat, center_lon],
        "acquisition_date": request.acquisition_date or "",
        "sensor": request.sensor,
        "cloud_cover_pct": request.cloud_cover_pct,
        "dataset": ds,
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    try:
        from app.api.v1.endpoints.search import engine_manager
        engine_manager.reload_engine(ds)
    except Exception as e:
        print(f"Warning: Failed to reload search engine: {e}")

    return {
        "status": "ok",
        "tile_id": tile_id,
        "faiss_id": new_id,
        "dataset": ds,
        "index_total": idx_mgr.index.ntotal,
        "center": [center_lat, center_lon],
        "detail": f"Vector appended to {os.path.basename(idx_path)} — no rebuild required."
    }
