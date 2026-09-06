"""
rebuild_mumbai_index.py
=======================
Completely rebuilds data/processed/mumbai.index and mumbai_metadata.json
from the actual raw SAFE data in data/raw/Mumbai/T43QBB_Mumbai_Core/.

Uses:
  - T43QBB T1 (Jan 2021) and T2 (Feb 2025) TCI_10m.jp2
  - CLIP-ViT-Large-Patch14 (768-dim) on CUDA FP16
  - Real Mumbai geographic POIs

Run from backend dir:
    cd backend
    .supervenv\Scripts\python.exe scripts\rebuild_mumbai_index.py
"""

import os
import sys
import glob
import json
import time
import re
import numpy as np

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR  = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

import rasterio
import rasterio.warp
from rasterio.windows import Window
from PIL import Image
import cv2
import faiss
import torch
from transformers import CLIPProcessor, CLIPVisionModelWithProjection

TILE_SLUG    = "T43QBB_Mumbai_Core"
RAW_BASE     = os.path.join(PROJECT_ROOT, "data", "raw", "Mumbai", TILE_SLUG)
PROCESSED_DIR   = os.path.join(PROJECT_ROOT, "data", "processed")
THUMBNAILS_DIR  = os.path.join(PROCESSED_DIR, "thumbnails")
INDEX_PATH      = os.path.join(PROCESSED_DIR, "mumbai.index")
METADATA_PATH   = os.path.join(PROCESSED_DIR, "mumbai_metadata.json")

PATCH_SIZE = 512
EMBED_DIM  = 768

MUMBAI_POIS = [
    (18.9900, 73.0700, "Navi Mumbai Intl Airport (NMIA) Construction",   "AIRFIELD_RUNWAY_DEVELOPMENT"),
    (18.9960, 73.0600, "NMIA South Access Taxiway Zone",                  "AIRFIELD_RUNWAY_DEVELOPMENT"),
    (19.0931, 72.8593, "Chhatrapati Shivaji Maharaj Intl Airport (CSIA)", "AIRFIELD_OPERATIONS_ZONE"),
    (18.9500, 72.9500, "JNPT Nhava Sheva Port",                           "PORT_LOGISTICS_EXPANSION"),
    (18.9600, 72.9600, "JNPT Container Terminal Extension",               "PORT_LOGISTICS_EXPANSION"),
    (19.0100, 72.8400, "Mumbai Port Trust Indira Dock",                   "PORT_LOGISTICS_EXPANSION"),
    (19.0700, 72.8700, "Bandra Kurla Complex BKC High Density Urban",     "URBAN_INFRASTRUCTURE_GROWTH"),
    (19.0400, 72.8500, "Dharavi Redevelopment Zone",                      "URBAN_INFRASTRUCTURE_GROWTH"),
    (18.9100, 72.8100, "South Mumbai CBD Nariman Point",                  "URBAN_INFRASTRUCTURE_GROWTH"),
    (19.2100, 72.9700, "Thane Urban Sprawl",                              "URBAN_INFRASTRUCTURE_GROWTH"),
    (19.0600, 72.8200, "Bandra Worli Sea Link Corridor",                  "COASTAL_INFRASTRUCTURE"),
    (19.0000, 72.8900, "Mahim Causeway And Creek",                        "COASTAL_INFRASTRUCTURE"),
    (19.1900, 72.9600, "Thane Creek Flamingo Sanctuary",                  "WETLAND_ECOLOGICAL_ZONE"),
    (19.0300, 73.0200, "Airoli Ghansoli Industrial Zone",                 "INDUSTRIAL_ZONE_EXPANSION"),
    (18.9800, 73.0000, "Ulwe NMIA Support Infrastructure",                "INDUSTRIAL_ZONE_EXPANSION"),
    (19.1500, 72.9900, "Mulund Thane Manufacturing Belt",                 "INDUSTRIAL_ZONE_EXPANSION"),
    (19.0700, 72.9900, "Eastern Express Freeway Interchange",             "TRANSPORT_CORRIDOR_DEVELOPMENT"),
    (18.9700, 73.0300, "New Panvel Rail Yard",                            "TRANSPORT_CORRIDOR_DEVELOPMENT"),
    (19.1200, 72.9100, "Powai Lake IIT Bombay Campus",                    "WATER_BODY_RESERVOIR"),
    (19.2500, 73.0500, "Ulhas River Estuary",                             "WATER_BODY_RESERVOIR"),
]


def find_tci_10m(root):
    matches = glob.glob(os.path.join(root, "**", "*TCI_10m.jp2"), recursive=True)
    if not matches:
        raise FileNotFoundError(f"No TCI_10m.jp2 found under: {root}")
    return matches[0]


def latlon_to_pixel(src, lat, lon):
    x, y = rasterio.warp.transform("EPSG:4326", src.crs, [lon], [lat])
    x, y = x[0], y[0]
    col, row = ~src.transform * (x, y)
    col, row = int(col), int(row)
    margin = PATCH_SIZE // 2
    if col < margin or row < margin:
        return None
    if col + margin >= src.width or row + margin >= src.height:
        return None
    return col, row


def read_patch_rgb(src, col, row):
    half = PATCH_SIZE // 2
    window = Window(col - half, row - half, PATCH_SIZE, PATCH_SIZE)
    arr = src.read([1, 2, 3], window=window)
    arr = np.transpose(arr, (1, 2, 0))
    if arr.dtype != np.uint8:
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return arr


def pixel_to_geojson_coords(src, col, row):
    half = PATCH_SIZE // 2
    window = Window(col - half, row - half, PATCH_SIZE, PATCH_SIZE)
    left, bottom, right, top = rasterio.windows.bounds(window, src.transform)
    lons, lats = rasterio.warp.transform(
        src.crs, "EPSG:4326",
        [left, right, right, left, left],
        [bottom, bottom, top, top, bottom],
    )
    return [[[float(lo), float(la)] for lo, la in zip(lons, lats)]]


def extract_date(path):
    m = re.search(r"(\d{8})T", os.path.basename(path))
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return "Unknown"


def main():
    t_start = time.time()
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    t1_dir = os.path.join(RAW_BASE, "T1_20210112_T43QBB")
    t2_dir = os.path.join(RAW_BASE, "T2_20250215_T43QBB")

    t1_tci = find_tci_10m(t1_dir)
    t2_tci = find_tci_10m(t2_dir)

    t1_date = extract_date(t1_tci)
    t2_date = extract_date(t2_tci)

    print(f"[T1] {t1_tci}")
    print(f"[T2] {t2_tci}")
    print(f"[Dates] T1={t1_date}  T2={t2_date}")

    local_ai  = os.getenv("LOCAL_AI_DIR", "")
    model_dir = os.path.join(local_ai, "clip-vit-large-patch14")
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"CLIP model not found at {model_dir}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype  = torch.float16 if device == "cuda" else torch.float32
    print(f"\n[Model] Loading CLIP-ViT-Large-Patch14 on {device.upper()} ({dtype})...")

    processor    = CLIPProcessor.from_pretrained(model_dir, local_files_only=True)
    vision_model = CLIPVisionModelWithProjection.from_pretrained(
        model_dir, local_files_only=True, torch_dtype=dtype
    ).to(device)
    vision_model.eval()
    print(f"[Model] Ready. dim={EMBED_DIM}")

    def embed_image(pil_img):
        inputs = processor(images=pil_img, return_tensors="pt")
        px = inputs.pixel_values.to(device, dtype=dtype)
        with torch.no_grad():
            feats = vision_model(pixel_values=px).image_embeds
            feats = feats / feats.norm(p=2, dim=-1, keepdim=True)
        return feats.cpu().float().numpy()[0]

    hnsw  = faiss.IndexHNSWFlat(EMBED_DIM, 32, faiss.METRIC_INNER_PRODUCT)
    index = faiss.IndexIDMap(hnsw)
    metadata = {}
    faiss_counter = 0

    print(f"\n[Rasters] Opening JP2 files (this may take a moment)...")
    with rasterio.open(t1_tci) as src1, rasterio.open(t2_tci) as src2:
        print(f"  T1: {src1.width}x{src1.height}px | CRS: {src1.crs}")
        print(f"  T2: {src2.width}x{src2.height}px | CRS: {src2.crs}")
        print(f"\n[Patches] Processing {len(MUMBAI_POIS)} POIs...\n")

        for idx, (lat, lon, site_name, label) in enumerate(MUMBAI_POIS):
            print(f"  [{idx+1:02d}/{len(MUMBAI_POIS)}] {site_name}")

            pix = latlon_to_pixel(src1, lat, lon)
            if pix is None:
                print(f"    !! ({lat}, {lon}) outside bounds - skipping")
                continue

            col, row = pix
            print(f"    -> pixel ({col}, {row})")

            arr1 = read_patch_rgb(src1, col, row)
            arr2 = read_patch_rgb(src2, col, row)

            img1 = Image.fromarray(arr1, mode="RGB")
            img2 = Image.fromarray(arr2, mode="RGB")

            slug = re.sub(r"[^a-z0-9]+", "_", site_name.lower()).strip("_")[:40]
            patch_id = f"mumbai_{slug}_{idx:02d}"

            t1_thumb = f"{patch_id}_t1.png"
            t2_thumb = f"{patch_id}_t2.png"
            img1.save(os.path.join(THUMBNAILS_DIR, t1_thumb))
            img2.save(os.path.join(THUMBNAILS_DIR, t2_thumb))

            t2_emb = embed_image(img2)

            coords = pixel_to_geojson_coords(src1, col, row)
            cx, cy = src1.transform * (col, row)
            clons, clats = rasterio.warp.transform(src1.crs, "EPSG:4326", [cx], [cy])
            center_lat, center_lon = float(clats[0]), float(clons[0])

            emb_f32 = t2_emb.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(emb_f32)
            index.add_with_ids(emb_f32, np.array([faiss_counter], dtype=np.int64))

            metadata[patch_id] = {
                "patch_id":              patch_id,
                "tile_id":               patch_id,
                "faiss_id":              faiss_counter,
                "center":                [center_lat, center_lon],
                "coordinates":           coords,
                "col_off":               col,
                "row_off":               row,
                "thumbnail_url":         f"/static/tiles/thumbnails/{t2_thumb}",
                "t1_thumbnail":          f"/static/tiles/thumbnails/{t1_thumb}",
                "t2_thumbnail":          f"/static/tiles/thumbnails/{t2_thumb}",
                "t1_date":               t1_date,
                "t2_date":               t2_date,
                "acquisition_date":      t2_date,
                "sensor":                "Sentinel-2 L2A",
                "site_name":             site_name,
                "label":                 label,
                "region":                "Mumbai",
                "state":                 "Maharashtra",
                "sfas_distance":         0.0,
                "is_significant_change": False,
                "tactical_confidence":   0.0,
                "spotrep":               "",
            }
            faiss_counter += 1
            print(f"    OK faiss_id={faiss_counter-1} center=({center_lat:.4f}, {center_lon:.4f})")

    print(f"\n[Save] Writing index -> {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)

    print(f"[Save] Writing metadata -> {METADATA_PATH}")
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Mumbai index rebuilt: {faiss_counter} patches in {elapsed:.1f}s")
    print(f"{'='*60}\n")

    # Quick sanity check
    print("[Sanity] Loading engine and running text queries...")
    try:
        from app.engine.vector_index import VectorIndexManager
        from app.engine.embedder import Embedder
        from app.engine.search import SemanticSearchEngine

        vm = VectorIndexManager(dim=EMBED_DIM)
        vm.load(INDEX_PATH)
        embedder = Embedder()
        engine = SemanticSearchEngine(embedder, vm, METADATA_PATH)

        test_queries = [
            "airport runway construction",
            "port container terminal ships",
            "urban dense city buildings",
            "water body lake reservoir",
        ]
        print()
        for q in test_queries:
            results = engine.search_by_text(q, top_k=3)
            print(f"  Query: '{q}'")
            for r in results:
                p = r["properties"]
                print(f"    [{p['similarity_score']:.4f}] {p['site_name']} | {p['center']}")
            print()
        print("Sanity OK!\n")
    except Exception as e:
        import traceback
        print(f"Sanity check error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
