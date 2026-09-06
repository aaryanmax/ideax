import os
import glob
import json
import math
import uuid
import re
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional

Image.MAX_IMAGE_PIXELS = None

from app.engine.embedder import Embedder
from app.engine.tactical import TacticalClassifier
from app.engine.gating import evaluate_sfas_change
from app.engine.scl_mask import analyze_scl_window
from app.engine.vector_index import VectorIndexManager
from rasterio.windows import Window

def latlon_to_utm(lat, lon, zone):
    """Converts WGS84 Lat/Lon to UTM Easting/Northing."""
    a = 6378137.0
    f = 1 / 298.257223563
    k0 = 0.9996
    e = math.sqrt(f * (2 - f))
    e1sq = e**2 / (1 - e**2)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lon0_rad = math.radians((zone - 1) * 6 - 180 + 3)
    N = a / math.sqrt(1 - e**2 * math.sin(lat_rad)**2)
    T = math.tan(lat_rad)**2
    C = e1sq * math.cos(lat_rad)**2
    A = (lon_rad - lon0_rad) * math.cos(lat_rad)
    M = a * ((1 - e**2/4 - 3*e**4/64 - 5*e**6/256) * lat_rad
             - (3*e**2/8 + 3*e**4/32 + 45*e**6/1024) * math.sin(2*lat_rad)
             + (15*e**4/256 + 45*e**6/1024) * math.sin(4*lat_rad)
             - (35*e**6/3072) * math.sin(6*lat_rad))
    easting = k0 * N * (A + (1 - T + C) * A**3 / 6 + (5 - 18*T + T**2 + 72*C - 58*e1sq) * A**5 / 120) + 500000.0
    northing = k0 * (M + N * math.tan(lat_rad) * (A**2 / 2 + (5 - T + 9*C + 4*C**2) * A**4 / 24 + (61 - 58*T + T**2 + 600*C - 330*e1sq) * A**6 / 720))
    return easting, northing

class DataIngestor:
    def __init__(self, dataset_name: str = "mumbai"):
        print("Initializing Embedder...")
        self.embedder = Embedder()
        print("Initializing Tactical Classifier...")
        self.classifier = TacticalClassifier(self.embedder)
        
        # Paths
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.data_dir = os.path.join(project_root, "data")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        self.thumbnails_dir = os.path.join(self.processed_dir, "thumbnails")
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        
        self.index_path = os.path.join(self.processed_dir, f"{dataset_name.lower()}.index")
        self.metadata_path = os.path.join(self.processed_dir, f"{dataset_name.lower()}_metadata.json")
            
        print(f"Using Index: {self.index_path}")
        print(f"Using Metadata: {self.metadata_path}")
        
        self.index_manager = VectorIndexManager(dim=768)
        if os.path.exists(self.index_path):
            try:
                self.index_manager.load(self.index_path)
            except Exception as e:
                print(f"Warning: Failed to load index at {self.index_path}: {e}")


    def _find_jp2(self, safe_dir: str, pattern: str) -> str:
        res = glob.glob(os.path.join(safe_dir, "**", pattern), recursive=True)
        if not res:
            raise FileNotFoundError(f"Could not find {pattern} in {safe_dir}")
        return res[0]

    def _get_tile_info(self, jp2_path: str):
        # Extremely fast GML origin extraction directly from JP2 bytes
        with open(jp2_path, "rb") as f:
            data = f.read(2048)
        
        epsg_idx = data.find(b"EPSG::")
        if epsg_idx == -1:
            raise ValueError("Could not find EPSG in JP2 header.")
        epsg = int(data[epsg_idx+6:epsg_idx+11])
        zone = int(str(epsg)[-2:])
        
        pos_idx = data.find(b"<gml:pos>")
        if pos_idx == -1:
            raise ValueError("Could not find gml:pos in JP2 header.")
        pos_end = data.find(b"</gml:pos>", pos_idx)
        ulx_str, uly_str = data[pos_idx+9:pos_end].split()
        ulx, uly = float(ulx_str), float(uly_str)
        
        return zone, ulx, uly

    def ingest_safe_pair(self, t1_safe: str, t2_safe: str, lat: float, lon: float, site_name: str, label: str):
        print(f"Ingesting SAFE pair for {site_name} at ({lat}, {lon})")
        t1_tci = self._find_jp2(t1_safe, "*TCI_10m.jp2")
        t2_tci = self._find_jp2(t2_safe, "*TCI_10m.jp2")
        t2_scl = self._find_jp2(t2_safe, "*SCL_20m.jp2")
        
        zone, ulx, uly = self._get_tile_info(t1_tci)
        easting, northing = latlon_to_utm(lat, lon, zone)
        
        col_off = int((easting - ulx) / 10)
        row_off = int((uly - northing) / 10)
        
        patch_id = f"patch_{uuid.uuid4().hex[:8]}"
        t1_thumb_path = os.path.join(self.thumbnails_dir, f"{patch_id}_t1.png")
        t2_thumb_path = os.path.join(self.thumbnails_dir, f"{patch_id}_t2.png")
        
        # Crop T1 & T2
        window = Window(col_off - 256, row_off - 256, 512, 512)
        im1 = Image.open(t1_tci)
        patch1 = im1.crop((col_off - 256, row_off - 256, col_off + 256, row_off + 256))
        patch1.save(t1_thumb_path)
        
        im2 = Image.open(t2_tci)
        patch2 = im2.crop((col_off - 256, row_off - 256, col_off + 256, row_off + 256))
        patch2.save(t2_thumb_path)
        
        # Quality Gate (SCL)
        scl_result = analyze_scl_window(t2_scl, window, resolution="20m")
        if scl_result.get("is_masked"):
            print(f"WARNING: Scene is occluded! {scl_result.get('suppression_reason')}")
            
        # SFAS Semantic Gate & Embedding
        t1_emb = self.embedder.embed_image(patch1)
        t2_emb = self.embedder.embed_image(patch2)
        
        sfas_res = evaluate_sfas_change(t1_emb, t2_emb)
        print(f"SFAS Distance: {sfas_res.get('confidence', 0.0):.3f} (Significant: {sfas_res['is_change']})")
        
        # Tactical Classification
        tactical_res = self.classifier.classify(t2_emb)
        print(f"Tactical Classification: {tactical_res['classification']}")
        
        # Dates
        def _extract_date(s, default_val="Unknown"):
            m = re.search(r"(\d{4})(\d{2})(\d{2})T", s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            m = re.search(r"(\d{4})(\d{2})(\d{2})", s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            return default_val
        
        t1_date = _extract_date(t1_safe, "2021-01-12")
        t2_date = _extract_date(t2_safe, "2025-02-15")

        # Registration
        metadata_entry = {
            "patch_id": patch_id,
            "tile_id": patch_id,
            "center": [lat, lon],
            "coordinates": [[[lon-0.02, lat-0.02], [lon+0.02, lat-0.02], [lon+0.02, lat+0.02], [lon-0.02, lat+0.02], [lon-0.02, lat-0.02]]],
            "thumbnail_url": f"/static/tiles/thumbnails/{patch_id}_t2.png",
            "t1_thumbnail": f"/static/tiles/thumbnails/{patch_id}_t1.png",
            "t2_thumbnail": f"/static/tiles/thumbnails/{patch_id}_t2.png",
            "t1_date": t1_date,
            "t2_date": t2_date,
            "acquisition_date": t2_date,
            "col_off": col_off,
            "row_off": row_off,
            "sensor": "Sentinel-2 L2A",
            "site_name": site_name,
            "label": label or tactical_res['classification'],
            "sfas_distance": float(sfas_res.get('confidence', 0.0)),
            "is_significant_change": bool(sfas_res['is_change']),
            "tactical_confidence": float(tactical_res['confidence']),
            "spotrep": tactical_res.get('spotrep', "")
        }
        
        self._register(patch_id, t2_emb, metadata_entry)

    def ingest_raw_pair(self, t1_tci: str, t2_tci: str, lat: float, lon: float, site_name: str, label: str):
        print(f"Ingesting RAW pair for {site_name} at ({lat}, {lon})")
        
        zone, ulx, uly = self._get_tile_info(t1_tci)
        easting, northing = latlon_to_utm(lat, lon, zone)
        
        col_off = int((easting - ulx) / 10)
        row_off = int((uly - northing) / 10)
        
        patch_id = f"patch_{uuid.uuid4().hex[:8]}"
        t1_thumb_path = os.path.join(self.thumbnails_dir, f"{patch_id}_t1.png")
        t2_thumb_path = os.path.join(self.thumbnails_dir, f"{patch_id}_t2.png")
        
        # Crop T1 & T2
        window = Window(col_off - 256, row_off - 256, 512, 512)
        im1 = Image.open(t1_tci)
        patch1 = im1.crop((col_off - 256, row_off - 256, col_off + 256, row_off + 256))
        patch1.save(t1_thumb_path)
        
        im2 = Image.open(t2_tci)
        patch2 = im2.crop((col_off - 256, row_off - 256, col_off + 256, row_off + 256))
        patch2.save(t2_thumb_path)
            
        # SFAS Semantic Gate & Embedding
        t1_emb = self.embedder.embed_image(patch1)
        t2_emb = self.embedder.embed_image(patch2)
        
        sfas_res = evaluate_sfas_change(t1_emb, t2_emb)
        print(f"SFAS Distance: {sfas_res.get('confidence', 0.0):.3f} (Significant: {sfas_res['is_change']})")
        
        # Tactical Classification
        tactical_res = self.classifier.classify(t2_emb)
        print(f"Tactical Classification: {tactical_res['classification']}")
        
        # Dates
        def _extract_date(s, default_val="Unknown"):
            m = re.search(r"(\d{4})(\d{2})(\d{2})T", s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            m = re.search(r"(\d{4})(\d{2})(\d{2})", s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            return default_val
        
        t1_date = _extract_date(t1_tci, "2021-01-30")
        t2_date = _extract_date(t2_tci, "2024-01-05")

        # Registration
        metadata_entry = {
            "patch_id": patch_id,
            "tile_id": patch_id,
            "center": [lat, lon],
            "coordinates": [[[lon-0.02, lat-0.02], [lon+0.02, lat-0.02], [lon+0.02, lat+0.02], [lon-0.02, lat+0.02], [lon-0.02, lat-0.02]]],
            "thumbnail_url": f"/static/tiles/thumbnails/{patch_id}_t2.png",
            "t1_thumbnail": f"/static/tiles/thumbnails/{patch_id}_t1.png",
            "t2_thumbnail": f"/static/tiles/thumbnails/{patch_id}_t2.png",
            "t1_date": t1_date,
            "t2_date": t2_date,
            "acquisition_date": t2_date,
            "col_off": col_off,
            "row_off": row_off,
            "sensor": "Sentinel-2 L2A",
            "site_name": site_name,
            "label": label or tactical_res['classification'],
            "sfas_distance": float(sfas_res.get('confidence', 0.0)),
            "is_significant_change": bool(sfas_res['is_change']),
            "tactical_confidence": float(tactical_res['confidence']),
            "spotrep": tactical_res.get('spotrep', "")
        }
        
        self._register(patch_id, t2_emb, metadata_entry)

    def ingest_patch_package(self, patch_dir: str):
        print(f"Ingesting Pre-cropped Patch Package: {patch_dir}")
        meta_path = os.path.join(patch_dir, "metadata.json")
        with open(meta_path, "r") as f:
            meta = json.load(f)
            
        patch_id = meta.get("patch_id", f"patch_{uuid.uuid4().hex[:8]}")
        lat, lon = meta.get("location", {}).get("target_coordinates", [0, 0])
        site = meta.get("location", {}).get("site_name", "Unknown")
        label = meta.get("label", "Unknown")
        
        prov = meta.get("source_provenance", {})
        t1_src = prov.get("t1_source_file", "")
        t2_src = prov.get("t2_source_file", "")
        
        def _extract_date(s, default_val):
            m = re.search(r"(\d{4})(\d{2})(\d{2})T", s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            m = re.search(r"(\d{4})(\d{2})(\d{2})", s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            m = re.search(r"(\d{1,2})([A-Z]+)(\d{4})", s.upper())
            if m:
                day = m.group(1).zfill(2)
                month_str = m.group(2)
                year = m.group(3)
                month_map = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06", "JUNE": "06", "JUL": "07", "JULY": "07", "AUG": "08", "SEP": "09", "SEPT": "09", "OCT": "10", "NOV": "11", "DEC": "12"}
                month = month_map.get(month_str, "01")
                return f"{year}-{month}-{day}"
            return default_val

        t1_date = meta.get("bitemporal_pair", {}).get("t1_date")
        if not t1_date:
            t1_date = _extract_date(t1_src, "2023-11-06")
            
        t2_date = meta.get("bitemporal_pair", {}).get("t2_date")
        if not t2_date:
            t2_date = _extract_date(t2_src, "2026-05-11")
        
        t1_thumbs = glob.glob(os.path.join(patch_dir, "**", "*t1*.png"), recursive=True)
        t2_thumbs = glob.glob(os.path.join(patch_dir, "**", "*t2*.png"), recursive=True)
        
        if not t1_thumbs or not t2_thumbs:
            raise FileNotFoundError(f"Missing t1/t2 thumbnails in {patch_dir}")
            
        t1_thumb = t1_thumbs[0]
        t2_thumb = t2_thumbs[0]
        
        patch1 = Image.open(t1_thumb)
        patch2 = Image.open(t2_thumb)
        
        t1_emb = self.embedder.embed_image(patch1)
        t2_emb = self.embedder.embed_image(patch2)
        
        sfas_res = evaluate_sfas_change(t1_emb, t2_emb)
        tactical_res = self.classifier.classify(t2_emb)
        
        # Copy thumbnails to processed
        new_t1_path = os.path.join(self.thumbnails_dir, f"{patch_id}_t1.png")
        new_t2_path = os.path.join(self.thumbnails_dir, f"{patch_id}_t2.png")
        patch1.save(new_t1_path)
        patch2.save(new_t2_path)
        
        metadata_entry = {
            "patch_id": patch_id,
            "tile_id": patch_id,
            "center": [lat, lon],
            "coordinates": meta.get("geojson", {}).get("geometry", {}).get("coordinates", []),
            "thumbnail_url": f"/static/tiles/thumbnails/{patch_id}_t2.png",
            "t1_thumbnail": f"/static/tiles/thumbnails/{patch_id}_t1.png",
            "t2_thumbnail": f"/static/tiles/thumbnails/{patch_id}_t2.png",
            "t1_date": t1_date,
            "t2_date": t2_date,
            "acquisition_date": t2_date,
            "sensor": "Sentinel-2 L2A",
            "site_name": site,
            "label": label,
            "sfas_distance": float(sfas_res.get('confidence', 0.0)),
            "is_significant_change": bool(sfas_res['is_change']),
            "tactical_confidence": float(tactical_res['confidence']),
            "spotrep": tactical_res.get('spotrep', "")
        }
        
        self._register(patch_id, t2_emb, metadata_entry)

    def _register(self, patch_id: str, embedding: np.ndarray, metadata_entry: dict):
        # Determine FAISS ID (current length before adding)
        faiss_id = self.index_manager.index.ntotal if hasattr(self.index_manager, 'index') else 0
        metadata_entry["faiss_id"] = faiss_id

        # Update FAISS
        try:
            self.index_manager.add_vectors(np.expand_dims(embedding, axis=0))
            self.index_manager.save(self.index_path)
        except Exception as e:
            print(f"Error saving FAISS index: {e}")
            return
            
        # Update JSON — always use unique patch_id as key
        meta_dict = {}
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        meta_dict = json.loads(content)
            except Exception as e:
                print(f"Error reading JSON at {self.metadata_path}: {e}. Starting fresh.")
                
        meta_dict[patch_id] = metadata_entry
        
        try:
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta_dict, f, indent=2)
            print(f"Successfully registered {patch_id} into catalog with faiss_id {faiss_id}!")
        except Exception as e:
            print(f"Error writing to {self.metadata_path}: {e}")
