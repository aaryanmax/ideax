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

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_file:
        fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
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
        return None
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
    parser = argparse.ArgumentParser(description="Automated Sliding Window Indexer with Batching & Checkpointing")
    parser.add_argument("--state", required=True, help="State name (e.g., Gujarat)")
    parser.add_argument("--raw_dir", required=True, help="Path to raw data region dir")
    parser.add_argument("--log_file", help="Path to save verbose logs")
    parser.add_argument("--patch_size", type=int, default=512)
    parser.add_argument("--stride", type=int, default=512)
    parser.add_argument("--variance_thresh", type=float, default=12.0)
    parser.add_argument("--batch_size", type=int, default=16, help="GPU batch size for CLIP inference")
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info(f"=== Starting Batched Ingestion for {args.state} ===")
    logger.info(f"Raw Dir: {args.raw_dir}")
    logger.info(f"Patch Size: {args.patch_size}, Stride: {args.stride}, Batch Size: {args.batch_size}")

    PROCESSED_DIR  = os.path.join(PROJECT_ROOT, "data", "processed")
    THUMBNAILS_DIR = os.path.join(PROCESSED_DIR, "thumbnails")
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    INDEX_PATH      = os.path.join(PROCESSED_DIR, f"{args.state.lower()}.index")
    METADATA_PATH   = os.path.join(PROCESSED_DIR, f"{args.state.lower()}_metadata.json")
    CHECKPOINT_PATH = os.path.join(PROCESSED_DIR, f"{args.state.lower()}_checkpoint.json")

    # ---- Find T1 and T2 folders ----
    subdirs = sorted([os.path.join(args.raw_dir, d) for d in os.listdir(args.raw_dir) if os.path.isdir(os.path.join(args.raw_dir, d))])
    t1_dir, t2_dir = None, None
    for d in subdirs:
        if "T1_" in os.path.basename(d): t1_dir = d
        if "T2_" in os.path.basename(d): t2_dir = d
    
    if not t1_dir or not t2_dir:
        logger.error(f"Could not find T1_ and T2_ directories in {args.raw_dir}")
        sys.exit(1)

    t1_img = find_tci_10m(t1_dir)
    t2_img = find_tci_10m(t2_dir)
    d1 = extract_date(t1_img)
    d2 = extract_date(t2_img)

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

    def embed_batch(pil_imgs):
        inputs = processor(images=pil_imgs, return_tensors="pt")
        px = inputs.pixel_values.to(device, dtype=dtype)
        with torch.no_grad():
            feats = vision_model(pixel_values=px).image_embeds
            feats = feats / feats.norm(p=2, dim=-1, keepdim=True)
        return feats.cpu().float().numpy()

    EMBED_DIM = 768

    # Check for resume checkpoint
    completed_rows = set()
    metadata = {}
    faiss_counter = 0

    if os.path.exists(CHECKPOINT_PATH) and os.path.exists(METADATA_PATH) and os.path.exists(INDEX_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                chk = json.load(f)
                completed_rows = set(chk.get("completed_rows", []))
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            index = faiss.read_index(INDEX_PATH)
            faiss_counter = index.ntotal
            logger.info(f"[*] Resuming from checkpoint! {len(completed_rows)} rows already done, {faiss_counter} patches indexed.")
        except Exception as e:
            logger.warning(f"Could not load checkpoint ({e}). Starting fresh.")
            completed_rows = set()
            metadata = {}
            faiss_counter = 0
            hnsw  = faiss.IndexHNSWFlat(EMBED_DIM, 32, faiss.METRIC_INNER_PRODUCT)
            index = faiss.IndexIDMap(hnsw)
    else:
        hnsw  = faiss.IndexHNSWFlat(EMBED_DIM, 32, faiss.METRIC_INNER_PRODUCT)
        index = faiss.IndexIDMap(hnsw)

    # ---- Sliding Window Process ----
    logger.info("Opening images for sliding window extraction...")
    t_start = time.time()
    
    stats = {"total_windows": 0, "skipped_bounds": 0, "skipped_variance": 0, "indexed": faiss_counter}

    with rasterio.open(t1_img) as src1, rasterio.open(t2_img) as src2:
        width, height = src1.width, src1.height
        logger.info(f"Image Size: {width}x{height} pixels | CRS: {src1.crs}")

        cols = list(range(0, width, args.stride))
        rows = list(range(0, height, args.stride))
        
        pending_batch_imgs = []
        pending_batch_meta = []

        def flush_batch():
            nonlocal faiss_counter
            if not pending_batch_imgs:
                return
            t_b0 = time.time()
            embs = embed_batch(pending_batch_imgs)
            for i, vec in enumerate(embs):
                v = vec.astype(np.float32).reshape(1, -1)
                faiss.normalize_L2(v)
                fid = faiss_counter
                index.add_with_ids(v, np.array([fid], dtype=np.int64))
                
                meta_item = pending_batch_meta[i]
                meta_item["faiss_id"] = fid
                metadata[meta_item["patch_id"]] = meta_item
                
                faiss_counter += 1
                stats["indexed"] += 1
            
            b_time = time.time() - t_b0
            logger.info(f"Batch ({len(pending_batch_imgs)} patches) embedded & indexed in {b_time:.2f}s (~{b_time/len(pending_batch_imgs):.3f}s/patch)")
            pending_batch_imgs.clear()
            pending_batch_meta.clear()

        for row in rows:
            if row in completed_rows:
                continue
            
            for col in cols:
                stats["total_windows"] += 1
                
                arr2 = read_patch_rgb(src2, col, row, args.patch_size)
                if arr2 is None:
                    stats["skipped_bounds"] += 1
                    continue
                
                std_dev = np.std(arr2)
                if std_dev < args.variance_thresh:
                    stats["skipped_variance"] += 1
                    continue
                
                arr1 = read_patch_rgb(src1, col, row, args.patch_size)
                if arr1 is None:
                    stats["skipped_bounds"] += 1
                    continue

                cx, cy = src1.transform * (col + args.patch_size//2, row + args.patch_size//2)
                clons, clats = rasterio.warp.transform(src1.crs, "EPSG:4326", [cx], [cy])
                clat, clon = float(clats[0]), float(clons[0])
                coords = pixel_to_geojson_coords(src1, col, row, args.patch_size)

                patch_id = f"{args.state.lower()}_auto_{row}_{col}"
                t1n = f"{patch_id}_t1.png"
                t2n = f"{patch_id}_t2.png"

                img1 = Image.fromarray(arr1, mode="RGB")
                img2 = Image.fromarray(arr2, mode="RGB")
                img1.save(os.path.join(THUMBNAILS_DIR, t1n))
                img2.save(os.path.join(THUMBNAILS_DIR, t2n))

                mae = float(np.mean(np.abs(arr2.astype(np.float32) - arr1.astype(np.float32))))
                is_sig = bool(mae >= 18.0)
                conf = round(min(1.0, mae / 45.0), 2)

                site_label = f"{args.state} Sector ({clat:.3f}, {clon:.3f})"
                if abs(clat - 27.881) < 0.05 and abs(clon - 95.315) < 0.05:
                    site_label = "NagabangOyan (Assam-Arunachal)"
                elif abs(clat - 19.506) < 0.05 and abs(clon - 83.133) < 0.05:
                    site_label = "Sijimali Bauxite (Rayagada, Odisha)"

                meta_dict = {
                    "patch_id":              patch_id,
                    "tile_id":               patch_id,
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
                    "site_name":             site_label,
                    "label":                 "INFRASTRUCTURE_CHANGE" if is_sig else "TERRAIN_MONITOR",
                    "temporal_pair":         f"T1({d1}) vs T2({d2})",
                    "region":                os.path.basename(args.raw_dir),
                    "state":                 args.state,
                    "sfas_distance":         round(mae, 2),
                    "is_significant_change": is_sig,
                    "tactical_confidence":   conf,
                    "spotrep":               f"Change score: {mae:.1f}" if is_sig else "",
                }

                pending_batch_imgs.append(img2)
                pending_batch_meta.append(meta_dict)

                if len(pending_batch_imgs) >= args.batch_size:
                    flush_batch()

            # Flush end of row
            flush_batch()
            completed_rows.add(row)
            
            # Checkpoint after each completed row
            faiss.write_index(index, INDEX_PATH)
            with open(METADATA_PATH, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
                json.dump({"completed_rows": list(completed_rows)}, f)
            
            logger.info(f"[*] Checkpoint saved: Row {row} complete | Total indexed: {stats['indexed']}")

    # Clean up checkpoint on completion
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    logger.info(f"\n--- INGESTION COMPLETE ---")
    logger.info(f"Successfully Indexed   : {stats['indexed']}")
    logger.info(f"Total Elapsed Time     : {time.time() - t_start:.1f}s")
    logger.info("DONE.")

if __name__ == "__main__":
    main()
