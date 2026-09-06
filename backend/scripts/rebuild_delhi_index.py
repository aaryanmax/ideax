"""
rebuild_delhi_index.py
======================
Rebuilds data/processed/delhi.index and delhi_metadata.json from:

  HERO DATASET - T43RGM_EastDelhi_Noida (3-timestamp multi-temporal):
    T1 = 2020-12-25  (baseline, pre-construction)
    T2 = 2021-02-23  (early construction phase)
    T3 = 2026-05-18  (current state)

  SECONDARY - T43RFM_WestDelhi_Gurgaon (bitemporal):
    T1 = 2026-02-17
    T2 = 2026-08-31

  Multi-temporal strategy for T43RGM POIs:
    For each POI we create 3 entries:
      (a) pair_T1_T3: 2020-12-25 vs 2026-05-18  -- full 5.5yr change (primary)
      (b) pair_T1_T2: 2020-12-25 vs 2021-02-23  -- early construction onset
      (c) pair_T2_T3: 2021-02-23 vs 2026-05-18  -- mid-to-current development

  The FAISS index always stores T_latest embedding (T3 for RGM, T2 for RFM).

Run (server must be stopped first):
    C:/Users/Admin/Projects/.supervenv/Scripts/python.exe scripts/rebuild_delhi_index.py
"""

import os, sys, glob, json, time, re
import numpy as np

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR  = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

import rasterio, rasterio.warp
from rasterio.windows import Window
from PIL import Image
import cv2, faiss, torch
from transformers import CLIPProcessor, CLIPVisionModelWithProjection

RAW_RGM = os.path.join(PROJECT_ROOT, "data", "raw", "Delhi", "T43RGM_EastDelhi_Noida")
RAW_RFM = os.path.join(PROJECT_ROOT, "data", "raw", "Delhi", "T43RFM_WestDelhi_Gurgaon")

PROCESSED_DIR  = os.path.join(PROJECT_ROOT, "data", "processed")
THUMBNAILS_DIR = os.path.join(PROCESSED_DIR, "thumbnails")
INDEX_PATH     = os.path.join(PROCESSED_DIR, "delhi.index")
METADATA_PATH  = os.path.join(PROCESSED_DIR, "delhi_metadata.json")

PATCH_SIZE = 512
EMBED_DIM  = 768

# ---------------------------------------------------------------------------
# T43RGM HERO POIs (East Delhi / Noida / Jewar) - lat/lon in EPSG:4326
# Tile covers approx: lat 27.9-29.0N, lon 77.0-78.1E
# ---------------------------------------------------------------------------
RGM_POIS = [
    # --- Jewar / IATA:DXN Airport (flagship change site) ---
    (28.1880, 77.5550, "Jewar Noida International Airport - Main Runway",      "AIRFIELD_RUNWAY_DEVELOPMENT"),
    (28.2000, 77.5650, "Jewar Airport - Northern Apron & Taxiway",             "AIRFIELD_RUNWAY_DEVELOPMENT"),
    (28.1750, 77.5450, "Jewar Airport - Southern Terminal Zone",               "AIRFIELD_RUNWAY_DEVELOPMENT"),

    # --- Greater Noida / Yamuna Expressway development ---
    (28.4700, 77.5100, "Greater Noida Urban Expansion",                        "URBAN_INFRASTRUCTURE_GROWTH"),
    (28.5100, 77.3900, "Noida Sector 62 IT Corridor",                         "URBAN_INFRASTRUCTURE_GROWTH"),
    (28.5800, 77.3200, "Noida Expressway High Density Zone",                   "URBAN_INFRASTRUCTURE_GROWTH"),

    # --- Yamuna River & Floodplain ---
    (28.5000, 77.3600, "Yamuna River Floodplain - Noida Stretch",              "WATER_BODY_RESERVOIR"),
    (28.4000, 77.4000, "Yamuna Expressway Greenfield Corridor",                "TRANSPORT_CORRIDOR_DEVELOPMENT"),

    # --- Industrial / Power ---
    (28.5500, 77.5500, "Dadri Gas Power Station & Industrial Zone",            "INDUSTRIAL_ZONE_EXPANSION"),
    (28.3000, 77.6000, "Bulandshahr Peripheral Industrial Belt",               "INDUSTRIAL_ZONE_EXPANSION"),

    # --- Agricultural / Seasonal land ---
    (28.2500, 77.5000, "Jewar-Bulandshahr Kharif Crop Fields",                "AGRICULTURAL_LAND_SEASONAL"),
    (28.3500, 77.4500, "Yamuna Khadar Agricultural Floodplain",               "AGRICULTURAL_LAND_SEASONAL"),
]

# ---------------------------------------------------------------------------
# T43RFM SECONDARY POIs (West Delhi / Gurugram) - lat/lon in EPSG:4326
# Tile covers approx: lat 27.9-29.0N, lon 75.9-77.0E
# ---------------------------------------------------------------------------
RFM_POIS = [
    # --- IGI Airport ---
    (28.5562, 77.1000, "Indira Gandhi International Airport (IGI) Terminal 2",  "AIRFIELD_OPERATIONS_ZONE"),
    (28.5500, 77.0800, "IGI Airport South Runway & Cargo Zone",                 "AIRFIELD_OPERATIONS_ZONE"),

    # --- Gurugram Cyber City ---
    (28.4950, 77.0900, "Gurugram Cyber City High-Rise Commercial",              "URBAN_INFRASTRUCTURE_GROWTH"),
    (28.4700, 77.0500, "Gurugram Southern Residential Sprawl",                  "URBAN_INFRASTRUCTURE_GROWTH"),

    # --- Dwarka / West Delhi Urban ---
    (28.5800, 77.0700, "Dwarka Sub-City High-Density Residential",              "URBAN_INFRASTRUCTURE_GROWTH"),

    # --- Delhi-Gurgaon Expressway ---
    (28.5100, 77.0900, "NH-48 Delhi-Gurugram Expressway Corridor",              "TRANSPORT_CORRIDOR_DEVELOPMENT"),

    # --- Green / Water ---
    (28.4200, 76.9800, "Badshahpur Nala & Aravalli Ridge",                     "WETLAND_ECOLOGICAL_ZONE"),
    (28.6000, 76.8000, "Sultanpur National Park Wetlands",                      "WETLAND_ECOLOGICAL_ZONE"),
]


def find_tci_10m(root):
    matches = glob.glob(os.path.join(root, "**", "*TCI_10m.jp2"), recursive=True)
    if not matches:
        raise FileNotFoundError(f"No TCI_10m.jp2 under: {root}")
    return matches[0]

def extract_date(path):
    m = re.search(r"(\d{8})T", os.path.basename(path))
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return "Unknown"

def latlon_to_pixel(src, lat, lon):
    x, y = rasterio.warp.transform("EPSG:4326", src.crs, [lon], [lat])
    col, row = ~src.transform * (x[0], y[0])
    col, row = int(col), int(row)
    margin = PATCH_SIZE // 2
    if col < margin or row < margin or col + margin >= src.width or row + margin >= src.height:
        return None
    return col, row

def read_patch_rgb(src, col, row):
    half = PATCH_SIZE // 2
    arr = src.read([1, 2, 3], window=Window(col - half, row - half, PATCH_SIZE, PATCH_SIZE))
    arr = np.transpose(arr, (1, 2, 0))
    if arr.dtype != np.uint8:
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return arr

def pixel_to_geojson_coords(src, col, row):
    half = PATCH_SIZE // 2
    left, bottom, right, top = rasterio.windows.bounds(Window(col - half, row - half, PATCH_SIZE, PATCH_SIZE), src.transform)
    lons, lats = rasterio.warp.transform(src.crs, "EPSG:4326",
                                          [left, right, right, left, left],
                                          [bottom, bottom, top, top, bottom])
    return [[[float(lo), float(la)] for lo, la in zip(lons, lats)]]

def make_record(patch_id, col, row, src_for_coords, center_lat, center_lon,
                t1_date, t2_date, t1_thumb, t2_thumb, site_name, label,
                region, state, faiss_id, temporal_pair_label):
    coords = pixel_to_geojson_coords(src_for_coords, col, row)
    return {
        "patch_id":              patch_id,
        "tile_id":               patch_id,
        "faiss_id":              faiss_id,
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
        "temporal_pair":         temporal_pair_label,
        "region":                region,
        "state":                 state,
        "sfas_distance":         0.0,
        "is_significant_change": False,
        "tactical_confidence":   0.0,
        "spotrep":               "",
    }


def main():
    t_start = time.time()
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    # ---- Load model -------------------------------------------------------
    local_ai  = os.getenv("LOCAL_AI_DIR", "")
    model_dir = os.path.join(local_ai, "clip-vit-large-patch14")
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    dtype     = torch.float16 if device == "cuda" else torch.float32
    print(f"[Model] Loading CLIP-ViT-Large-Patch14 on {device.upper()} ({dtype})...")

    processor    = CLIPProcessor.from_pretrained(model_dir, local_files_only=True)
    vision_model = CLIPVisionModelWithProjection.from_pretrained(
        model_dir, local_files_only=True, torch_dtype=dtype).to(device)
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
    metadata     = {}
    faiss_counter = 0

    # =======================================================================
    # PART 1: T43RGM HERO — 3-timestamp multi-temporal
    # =======================================================================
    print("\n" + "="*60)
    print("PART 1: T43RGM EastDelhi/Noida/Jewar (3-timestamp)")
    print("="*60)

    t1_rgm = find_tci_10m(os.path.join(RAW_RGM, "T1_20201225_T43RGM"))
    t2_rgm = find_tci_10m(os.path.join(RAW_RGM, "T2_20210223_T43RGM"))
    t3_rgm = find_tci_10m(os.path.join(RAW_RGM, "T3_20260518_T43RGM"))

    d1 = extract_date(t1_rgm)   # 2020-12-25
    d2 = extract_date(t2_rgm)   # 2021-02-23
    d3 = extract_date(t3_rgm)   # 2026-05-18
    print(f"  T1={d1}  T2={d2}  T3={d3}")

    with rasterio.open(t1_rgm) as src1, \
         rasterio.open(t2_rgm) as src2, \
         rasterio.open(t3_rgm) as src3:

        print(f"  T1: {src1.width}x{src1.height}px | CRS: {src1.crs}")

        for poi_idx, (lat, lon, site_name, label) in enumerate(RGM_POIS):
            print(f"\n  [{poi_idx+1:02d}/{len(RGM_POIS)}] {site_name}")

            pix = latlon_to_pixel(src1, lat, lon)
            if pix is None:
                print(f"    !! ({lat}, {lon}) outside T43RGM bounds - skipping")
                continue
            col, row = pix

            arr1 = read_patch_rgb(src1, col, row)
            arr2 = read_patch_rgb(src2, col, row)
            arr3 = read_patch_rgb(src3, col, row)

            img1 = Image.fromarray(arr1, mode="RGB")
            img2 = Image.fromarray(arr2, mode="RGB")
            img3 = Image.fromarray(arr3, mode="RGB")

            cx, cy = src1.transform * (col, row)
            clons, clats = rasterio.warp.transform(src1.crs, "EPSG:4326", [cx], [cy])
            clat, clon = float(clats[0]), float(clons[0])

            slug = re.sub(r"[^a-z0-9]+", "_", site_name.lower()).strip("_")[:38]

            # --- Pair A: T1(2020) vs T3(2026) — PRIMARY full-range change ---
            pid_a  = f"delhi_rgm_{slug}_{poi_idx:02d}_T1T3"
            t1n_a  = f"{pid_a}_t1.png"
            t2n_a  = f"{pid_a}_t2.png"
            img1.save(os.path.join(THUMBNAILS_DIR, t1n_a))
            img3.save(os.path.join(THUMBNAILS_DIR, t2n_a))
            emb_a  = embed_image(img3)
            vec = emb_a.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)
            index.add_with_ids(vec, np.array([faiss_counter], dtype=np.int64))
            metadata[pid_a] = make_record(pid_a, col, row, src1, clat, clon,
                d1, d3, t1n_a, t2n_a, site_name, label, "EastDelhi/Noida", "Delhi",
                faiss_counter, f"T1({d1}) vs T3({d3}) — full 5.5yr range")
            faiss_counter += 1
            print(f"    [A] faiss={faiss_counter-1} | T1({d1})→T3({d3}) | ({clat:.4f},{clon:.4f})")

            # --- Pair B: T1(2020) vs T2(2021) — early onset ---
            pid_b  = f"delhi_rgm_{slug}_{poi_idx:02d}_T1T2"
            t1n_b  = f"{pid_b}_t1.png"
            t2n_b  = f"{pid_b}_t2.png"
            img1.save(os.path.join(THUMBNAILS_DIR, t1n_b))
            img2.save(os.path.join(THUMBNAILS_DIR, t2n_b))
            emb_b  = embed_image(img2)
            vec = emb_b.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)
            index.add_with_ids(vec, np.array([faiss_counter], dtype=np.int64))
            metadata[pid_b] = make_record(pid_b, col, row, src1, clat, clon,
                d1, d2, t1n_b, t2n_b, site_name, label, "EastDelhi/Noida", "Delhi",
                faiss_counter, f"T1({d1}) vs T2({d2}) — early construction onset")
            faiss_counter += 1
            print(f"    [B] faiss={faiss_counter-1} | T1({d1})→T2({d2}) early onset")

            # --- Pair C: T2(2021) vs T3(2026) — mid-to-current ---
            pid_c  = f"delhi_rgm_{slug}_{poi_idx:02d}_T2T3"
            t1n_c  = f"{pid_c}_t1.png"
            t2n_c  = f"{pid_c}_t2.png"
            img2.save(os.path.join(THUMBNAILS_DIR, t1n_c))
            img3.save(os.path.join(THUMBNAILS_DIR, t2n_c))
            emb_c  = embed_image(img3)
            vec = emb_c.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)
            index.add_with_ids(vec, np.array([faiss_counter], dtype=np.int64))
            metadata[pid_c] = make_record(pid_c, col, row, src1, clat, clon,
                d2, d3, t1n_c, t2n_c, site_name, label, "EastDelhi/Noida", "Delhi",
                faiss_counter, f"T2({d2}) vs T3({d3}) — mid-to-current development")
            faiss_counter += 1
            print(f"    [C] faiss={faiss_counter-1} | T2({d2})→T3({d3}) mid-to-current")

    # =======================================================================
    # PART 2: T43RFM SECONDARY — WestDelhi/Gurugram (bitemporal)
    # =======================================================================
    print("\n" + "="*60)
    print("PART 2: T43RFM WestDelhi/Gurugram (bitemporal)")
    print("="*60)

    t1_rfm = find_tci_10m(os.path.join(RAW_RFM, "T1_20260217_T43RFM"))
    t2_rfm = find_tci_10m(os.path.join(RAW_RFM, "T2_20260831_T43RFM"))
    d1_rfm = extract_date(t1_rfm)   # 2026-02-17
    d2_rfm = extract_date(t2_rfm)   # 2026-08-31
    print(f"  T1={d1_rfm}  T2={d2_rfm}")

    with rasterio.open(t1_rfm) as src1, rasterio.open(t2_rfm) as src2:
        print(f"  T1: {src1.width}x{src1.height}px | CRS: {src1.crs}")

        for poi_idx, (lat, lon, site_name, label) in enumerate(RFM_POIS):
            print(f"\n  [{poi_idx+1:02d}/{len(RFM_POIS)}] {site_name}")

            pix = latlon_to_pixel(src1, lat, lon)
            if pix is None:
                print(f"    !! ({lat}, {lon}) outside T43RFM bounds - skipping")
                continue
            col, row = pix

            arr1 = read_patch_rgb(src1, col, row)
            arr2 = read_patch_rgb(src2, col, row)
            img1 = Image.fromarray(arr1, mode="RGB")
            img2 = Image.fromarray(arr2, mode="RGB")

            cx, cy = src1.transform * (col, row)
            clons, clats = rasterio.warp.transform(src1.crs, "EPSG:4326", [cx], [cy])
            clat, clon = float(clats[0]), float(clons[0])

            slug   = re.sub(r"[^a-z0-9]+", "_", site_name.lower()).strip("_")[:38]
            pid    = f"delhi_rfm_{slug}_{poi_idx:02d}"
            t1n    = f"{pid}_t1.png"
            t2n    = f"{pid}_t2.png"
            img1.save(os.path.join(THUMBNAILS_DIR, t1n))
            img2.save(os.path.join(THUMBNAILS_DIR, t2n))

            emb = embed_image(img2)
            vec = emb.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)
            index.add_with_ids(vec, np.array([faiss_counter], dtype=np.int64))
            metadata[pid] = make_record(pid, col, row, src1, clat, clon,
                d1_rfm, d2_rfm, t1n, t2n, site_name, label,
                "WestDelhi/Gurugram", "Delhi", faiss_counter,
                f"T1({d1_rfm}) vs T2({d2_rfm})")
            faiss_counter += 1
            print(f"    OK faiss={faiss_counter-1} | ({clat:.4f},{clon:.4f})")

    # ---- Save ------------------------------------------------------------
    print(f"\n[Save] Writing FAISS index ({faiss_counter} vectors) -> {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)
    print(f"[Save] Writing metadata -> {METADATA_PATH}")
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Delhi index rebuilt: {faiss_counter} patches in {elapsed:.1f}s")
    print(f"  T43RGM (hero): {len(RGM_POIS)*3} entries (12 POIs x 3 temporal pairs)")
    print(f"  T43RFM (secondary): {len(RFM_POIS)} entries (8 POIs bitemporal)")
    print(f"{'='*60}\n")

    # ---- Sanity queries ---------------------------------------------------
    print("[Sanity] Running text queries...")
    try:
        from app.engine.vector_index import VectorIndexManager
        from app.engine.embedder import Embedder
        from app.engine.search import SemanticSearchEngine
        vm = VectorIndexManager(dim=EMBED_DIM)
        vm.load(INDEX_PATH)
        embedder = Embedder()
        engine   = SemanticSearchEngine(embedder, vm, METADATA_PATH)
        for q in ["airport runway construction", "jewar international airport", "dense urban buildings", "agricultural crop fields"]:
            results = engine.search_by_text(q, top_k=3)
            print(f"\n  '{q}'")
            for r in results:
                p = r["properties"]
                print(f"    [{p['similarity_score']:.4f}] {p['site_name']} | {p['temporal_pair']} | ({p['center'][0]:.3f},{p['center'][1]:.3f})")
        print("\nSanity OK!\n")
    except Exception as e:
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
