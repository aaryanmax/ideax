import os, sys, glob, json, time, re, argparse, logging
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

def setup_logger(log_file):
    logger = logging.getLogger("AutoIngestion")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    if log_file:
        fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    return logger

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

def read_patch_rgb(src, col, row, size):
    arr = src.read([1, 2, 3], window=Window(col, row, size, size))
    if arr.shape[1] != size or arr.shape[2] != size:
        return None  # Out of bounds or edge
    arr = np.transpose(arr, (1, 2, 0))
    if arr.dtype != np.uint8:
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return arr

def pixel_to_geojson_coords(src, col, row, size):
    left, bottom, right, top = rasterio.windows.bounds(Window(col, row, size, size), src.transform)
    lons, lats = rasterio.warp.transform(src.crs, "EPSG:4326",
                                          [left, right, right, left, left],
                                          [bottom, bottom, top, top, bottom])
    return [[[float(lo), float(la)] for lo, la in zip(lons, lats)]]

def main():
    parser = argparse.ArgumentParser(description="Automated Sliding Window Indexer")
    parser.add_argument("--state", required=True, help="State name (e.g., Gujarat)")
    parser.add_argument("--raw_dir", required=True, help="Path to raw data region dir (e.g., data/raw/Gujarat/T42QWM_Dholera)")
    parser.add_argument("--log_file", help="Path to save verbose logs")
    parser.add_argument("--patch_size", type=int, default=512)
    parser.add_argument("--stride", type=int, default=512)
    parser.add_argument("--variance_thresh", type=float, default=12.0, help="Min stddev to keep patch (filters desert/water)")
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info(f"=== Starting Automated Ingestion for {args.state} ===")
    logger.info(f"Raw Dir: {args.raw_dir}")
    logger.info(f"Patch Size: {args.patch_size}, Stride: {args.stride}, Var Thresh: {args.variance_thresh}")
    
    if args.log_file:
        logger.info(f"Detailed logs being written to: {args.log_file}")

    PROCESSED_DIR  = os.path.join(PROJECT_ROOT, "data", "processed")
    THUMBNAILS_DIR = os.path.join(PROCESSED_DIR, "thumbnails")
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    INDEX_PATH     = os.path.join(PROCESSED_DIR, f"{args.state.lower()}.index")
    METADATA_PATH  = os.path.join(PROCESSED_DIR, f"{args.state.lower()}_metadata.json")

    # ---- Find T1 and T2 folders ----
    subdirs = sorted([os.path.join(args.raw_dir, d) for d in os.listdir(args.raw_dir) if os.path.isdir(os.path.join(args.raw_dir, d))])
    t1_dir, t2_dir = None, None
    for d in subdirs:
        if "T1_" in os.path.basename(d): t1_dir = d
        if "T2_" in os.path.basename(d): t2_dir = d
    
    if not t1_dir or not t2_dir:
        logger.error(f"Could not find T1_ and T2_ directories in {args.raw_dir}")
        sys.exit(1)

    logger.info(f"Discovered T1 Directory: {t1_dir}")
    logger.info(f"Discovered T2 Directory: {t2_dir}")

    t1_img = find_tci_10m(t1_dir)
    t2_img = find_tci_10m(t2_dir)
    d1 = extract_date(t1_img)
    d2 = extract_date(t2_img)

    logger.info(f"T1 Date: {d1} | File: {os.path.basename(t1_img)}")
    logger.info(f"T2 Date: {d2} | File: {os.path.basename(t2_img)}")

    # ---- Load AI Model ----
    local_ai  = os.getenv("LOCAL_AI_DIR", "")
    model_dir = os.path.join(local_ai, "clip-vit-large-patch14")
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    dtype     = torch.float16 if device == "cuda" else torch.float32
    logger.info(f"Loading CLIP-ViT-Large on {device.upper()} ({dtype})...")
    
    t_load = time.time()
    processor    = CLIPProcessor.from_pretrained(model_dir, local_files_only=True)
    vision_model = CLIPVisionModelWithProjection.from_pretrained(
        model_dir, local_files_only=True, torch_dtype=dtype).to(device)
    vision_model.eval()
    logger.info(f"Model loaded in {time.time() - t_load:.1f}s")

    def embed_image(pil_img):
        inputs = processor(images=pil_img, return_tensors="pt")
        px = inputs.pixel_values.to(device, dtype=dtype)
        with torch.no_grad():
            feats = vision_model(pixel_values=px).image_embeds
            feats = feats / feats.norm(p=2, dim=-1, keepdim=True)
        return feats.cpu().float().numpy()[0]

    EMBED_DIM = 768
    hnsw  = faiss.IndexHNSWFlat(EMBED_DIM, 32, faiss.METRIC_INNER_PRODUCT)
    index = faiss.IndexIDMap(hnsw)
    metadata = {}
    faiss_counter = 0

    # ---- Sliding Window Process ----
    logger.info("Opening images for sliding window extraction...")
    t_start = time.time()
    
    stats = {"total_windows": 0, "skipped_bounds": 0, "skipped_variance": 0, "indexed": 0}

    with rasterio.open(t1_img) as src1, rasterio.open(t2_img) as src2:
        width, height = src1.width, src1.height
        logger.info(f"Image Size: {width}x{height} pixels")
        logger.info(f"CRS: {src1.crs}")

        # Calculate grid
        cols = list(range(0, width, args.stride))
        rows = list(range(0, height, args.stride))
        
        for row in rows:
            for col in cols:
                stats["total_windows"] += 1
                
                arr2 = read_patch_rgb(src2, col, row, args.patch_size)
                if arr2 is None:
                    stats["skipped_bounds"] += 1
                    continue
                
                # Variance filter to skip empty desert/water/clouds
                std_dev = np.std(arr2)
                if std_dev < args.variance_thresh:
                    stats["skipped_variance"] += 1
                    logger.debug(f"Skipped patch at col={col}, row={row} | StdDev={std_dev:.1f} < {args.variance_thresh} (Likely empty)")
                    continue
                
                # Fetch T1 now that we know we want it
                arr1 = read_patch_rgb(src1, col, row, args.patch_size)
                if arr1 is None:
                    stats["skipped_bounds"] += 1
                    continue

                # Calculate Geo coordinates
                cx, cy = src1.transform * (col + args.patch_size//2, row + args.patch_size//2)
                clons, clats = rasterio.warp.transform(src1.crs, "EPSG:4326", [cx], [cy])
                clat, clon = float(clats[0]), float(clons[0])
                coords = pixel_to_geojson_coords(src1, col, row, args.patch_size)

                # Generate IDs
                patch_id = f"{args.state.lower()}_auto_{row}_{col}"
                t1n = f"{patch_id}_t1.png"
                t2n = f"{patch_id}_t2.png"

                # Save thumbnails
                img1 = Image.fromarray(arr1, mode="RGB")
                img2 = Image.fromarray(arr2, mode="RGB")
                img1.save(os.path.join(THUMBNAILS_DIR, t1n))
                img2.save(os.path.join(THUMBNAILS_DIR, t2n))

                # Embed & Index
                emb = embed_image(img2)
                vec = emb.astype(np.float32).reshape(1, -1)
                faiss.normalize_L2(vec)
                index.add_with_ids(vec, np.array([faiss_counter], dtype=np.int64))
                
                # Metadata
                metadata[patch_id] = {
                    "patch_id":              patch_id,
                    "tile_id":               patch_id,
                    "faiss_id":              faiss_counter,
                    "center":                [clat, clon],
                    "coordinates":           coords,
                    "col_off":               col,
                    "row_off":               row,
                    "thumbnail_url":         f"/static/tiles/thumbnails/{t2n}",
                    "t1_thumbnail":          f"/static/tiles/thumbnails/{t1n}",
                    "t2_thumbnail":          f"/static/tiles/thumbnails/{t2n}",
                    "t1_date":               d1,
                    "t2_date":               d2,
                    "acquisition_date":      d2,
                    "sensor":                "Sentinel-2 L2A",
                    "site_name":             f"Auto-Discovered Zone ({clat:.3f}, {clon:.3f})",
                    "label":                 "AUTO_DISCOVERED",
                    "temporal_pair":         f"T1({d1}) vs T2({d2})",
                    "region":                os.path.basename(args.raw_dir),
                    "state":                 args.state,
                    "sfas_distance":         0.0,
                    "is_significant_change": False,
                    "tactical_confidence":   0.0,
                    "spotrep":               "",
                }
                
                logger.debug(f"Indexed [faiss={faiss_counter}] | {patch_id} | StdDev={std_dev:.1f} | Loc: ({clat:.4f}, {clon:.4f})")
                faiss_counter += 1
                stats["indexed"] += 1

                if stats["indexed"] % 50 == 0:
                    logger.info(f"Progress: Extracted {stats['indexed']} patches so far...")

    # ---- Save Outputs ----
    logger.info(f"\n--- INGESTION COMPLETE ---")
    logger.info(f"Total Windows Evaluated: {stats['total_windows']}")
    logger.info(f"Skipped (Out of bounds): {stats['skipped_bounds']}")
    logger.info(f"Skipped (Low Variance) : {stats['skipped_variance']}")
    logger.info(f"Successfully Indexed   : {stats['indexed']}")
    logger.info(f"Time Taken           : {time.time() - t_start:.1f}s")

    logger.info(f"Writing FAISS index -> {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)
    logger.info(f"Writing Metadata    -> {METADATA_PATH}")
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        
    logger.info("DONE.")

if __name__ == "__main__":
    main()
