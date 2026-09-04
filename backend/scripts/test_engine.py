import sys
import os
import re
import time
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend to safely render and save PNG
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import cv2
from PIL import Image
import rasterio
from rasterio.windows import Window
from rasterio.windows import transform as win_transform_fn
from rasterio.warp import transform as reproject_coords
from scipy.spatial.distance import cosine

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.engine.embedder import Embedder
from app.engine.gating import evaluate_sfas_change
from app.engine.tiler import extract_change_polygons

def resolve_path(path: str) -> str:
    """Resolves relative file paths against standard workspace locations."""
    if os.path.isabs(path) and os.path.exists(path):
        return path
    candidates = [
        os.path.abspath(path),
        os.path.join(PROJECT_ROOT, path),
        os.path.join(BACKEND_DIR, path),
        os.path.join(PROJECT_ROOT, "data", "processed", os.path.basename(path))
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return path

def parse_granule_metadata(path: str) -> dict:
    """Extracts satellite acquisition and sensor metadata from filename and raster attributes."""
    filename = os.path.basename(path)
    meta = {
        "filename": filename,
        "sensor": "Sentinel-2 MSI (Level-2A BOA True Color Image 10m)",
        "granule": "Unknown",
        "timestamp": "Unknown"
    }
    match = re.search(r"(T\d{2}[A-Z]{3})_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})", filename)
    if match:
        tile, y, m, d, hh, mm, ss = match.groups()
        meta["granule"] = tile
        meta["timestamp"] = f"{y}-{m}-{d} {hh}:{mm}:{ss} UTC"
    return meta

def extract_patch_and_bounds(raster_path: str, window: Window):
    """
    Extracts a spatial patch using rasterio.windows.Window without loading the full raster.
    Returns the RGB array and EPSG:4326 decimal-degree bounding box coordinates.
    """
    with rasterio.open(raster_path) as src:
        arr = src.read(window=window)
        crs = src.crs
        src_transform = src.transform
        patch_transform = win_transform_fn(window, src_transform)

    # Transpose (C, H, W) to (H, W, C)
    arr = np.transpose(arr, (1, 2, 0))
    if arr.dtype != np.uint8:
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    if arr.shape[2] == 1:
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    elif arr.shape[2] > 3:
        arr = arr[:, :, :3]

    # Calculate 4 corners of window in spatial coordinates
    w, h = int(window.width), int(window.height)
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    spatial_coords = [rasterio.transform.xy(patch_transform, r, c) for c, r in corners]
    xs = [pt[0] for pt in spatial_coords]
    ys = [pt[1] for pt in spatial_coords]

    # Reproject to EPSG:4326 (WGS84 Lat/Lon in decimal degrees)
    if crs and crs.to_string() != "EPSG:4326":
        try:
            lons, lats = reproject_coords(crs, "EPSG:4326", xs, ys)
        except Exception:
            lons, lats = xs, ys
    else:
        lons, lats = xs, ys

    bounds_geo = {
        "min_lon": min(lons),
        "max_lon": max(lons),
        "min_lat": min(lats),
        "max_lat": max(lats),
        "top_left": (max(lats), min(lons)),
        "bottom_right": (min(lats), max(lons)),
        "patch_transform": patch_transform,
        "crs": crs
    }
    return arr, bounds_geo

def compute_difference_mask(img1: np.ndarray, img2: np.ndarray):
    """Computes difference mask for the patch using grayscale diff and Otsu thresholding."""
    gray1 = cv2.cvtColor(img1[:, :, :3], cv2.COLOR_RGB2GRAY) if img1.shape[2] >= 3 else img1[:, :, 0]
    gray2 = cv2.cvtColor(img2[:, :, :3], cv2.COLOR_RGB2GRAY) if img2.shape[2] >= 3 else img2[:, :, 0]
    
    diff = cv2.absdiff(gray1, gray2)
    blur = cv2.GaussianBlur(diff, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def main():
    default_t1 = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260217T054121_TCI_10m.jp2")
    default_t2 = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")
    default_output_png = os.path.join(PROJECT_ROOT, "data", "processed", "test_verification_output.png")

    parser = argparse.ArgumentParser(description="End-to-end memory-protected test of the AI engine pipeline.")
    parser.add_argument("--t1", type=str, default=default_t1, help="Path to T1 Sentinel-2 JP2 file")
    parser.add_argument("--t2", type=str, default=default_t2, help="Path to T2 Sentinel-2 JP2 file")
    parser.add_argument("--col-off", type=int, default=4500, help="Column offset for spatial window (default: 4500)")
    parser.add_argument("--row-off", type=int, default=4500, help="Row offset for spatial window (default: 4500)")
    parser.add_argument("--patch-size", type=int, default=512, help="Window width and height in pixels (default: 512)")
    parser.add_argument("--threshold", type=float, default=0.15, help="SFAS Cosine Distance threshold (default: 0.15)")
    parser.add_argument("--min-area", type=int, default=50, help="Minimum contour area in pixels for tiler (default: 50)")
    parser.add_argument("--output-png", type=str, default=default_output_png, help="Path to save verification figure")
    parser.add_argument("--force", action="store_true", help="Force contour extraction even if gate suppresses")
    args = parser.parse_args()

    t1_path = resolve_path(args.t1)
    t2_path = resolve_path(args.t2)
    output_png = os.path.abspath(args.output_png)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    if not os.path.exists(t1_path):
        print(f"[ERROR] T1 file not found at: {t1_path}")
        sys.exit(1)
    if not os.path.exists(t2_path):
        print(f"[ERROR] T2 file not found at: {t2_path}")
        sys.exit(1)

    t1_meta = parse_granule_metadata(t1_path)
    t2_meta = parse_granule_metadata(t2_path)

    # 1. Memory Protected Spatial Window
    window = Window(args.col_off, args.row_off, args.patch_size, args.patch_size)
    print(f"\n[*] Extracting aligned {args.patch_size}x{args.patch_size} window at col={args.col_off}, row={args.row_off}...")
    
    t_load_start = time.perf_counter()
    patch_t1, bounds_t1 = extract_patch_and_bounds(t1_path, window)
    patch_t2, bounds_t2 = extract_patch_and_bounds(t2_path, window)
    load_time_ms = (time.perf_counter() - t_load_start) * 1000

    pil_t1 = Image.fromarray(patch_t1)
    pil_t2 = Image.fromarray(patch_t2)

    # 2. Embedding Generation
    print("[*] Initializing Foundation Model Embedder (GPU/FP16 & CPU/ONNX)...")
    t_init_start = time.perf_counter()
    embedder = Embedder()
    init_time_ms = (time.perf_counter() - t_init_start) * 1000

    print("[*] Propagating patches through Embedder...")
    t_embed_start = time.perf_counter()
    v1 = embedder.embed_image(pil_t1)
    v2 = embedder.embed_image(pil_t2)
    embedding_time_ms = (time.perf_counter() - t_embed_start) * 1000

    # 3. SFAS Gating
    print("[*] Evaluating Semantic False-Alarm Suppression (SFAS) Gate...")
    t_gate_start = time.perf_counter()
    gate_eval = evaluate_sfas_change(v1, v2, threshold=args.threshold)
    gating_time_ms = (time.perf_counter() - t_gate_start) * 1000

    # Cosine distance = 1 - cosine similarity
    cos_dist = float(cosine(v1, v2))
    cos_sim = 1.0 - cos_dist
    is_change = gate_eval.get("is_change", False)
    gate_status = "TACTICAL_CHANGE" if is_change else "SUPPRESSED"

    # 4. Spatial Differencing & Bounding Box Extraction
    contours_time_ms = 0.0
    features = []
    if is_change or args.force:
        print("[*] Gate approved (or forced). Running Tiler spatial differencing...")
        t_tiler_start = time.perf_counter()
        features = extract_change_polygons(t1_path, t2_path, min_area=args.min_area, window=window)
        contours_time_ms = (time.perf_counter() - t_tiler_start) * 1000
    else:
        print("[*] Gate SUPPRESSED change. Skipping contour extraction (use --force to override).")

    # Difference mask for visualization
    diff_mask = compute_difference_mask(patch_t1, patch_t2)

    # Top anomaly coordinates
    top_feature = None
    if features:
        features_sorted = sorted(features, key=lambda f: f["properties"].get("area_pixels", 0), reverse=True)
        top_feature = features_sorted[0]

    # Total pipeline latency (loading + embedding + gating + contouring)
    total_pipeline_latency_ms = load_time_ms + embedding_time_ms + gating_time_ms + contours_time_ms

    # 5. Print Structured Terminal Report
    print("\n" + "=" * 80)
    print("                VAYU-CHRONICLE AI ENGINE PIPELINE VERIFICATION")
    print("=" * 80)
    print("\n[1] SENSOR & ACQUISITION METADATA")
    print(f"    - T1 Sensor:          {t1_meta['sensor']}")
    print(f"    - T1 Acquisition:     {t1_meta['timestamp']} ({t1_meta['filename']})")
    print(f"    - T2 Sensor:          {t2_meta['sensor']}")
    print(f"    - T2 Acquisition:     {t2_meta['timestamp']} ({t2_meta['filename']})")
    print(f"    - Granule Tile ID:    {t1_meta['granule']} (Delhi NCR AOI)")

    print("\n[2] SPATIAL PATCH & GEOGRAPHIC COORDINATES (Memory Protection Active)")
    print(f"    - Window Offset:      col_off={args.col_off}, row_off={args.row_off}")
    print(f"    - Patch Dimensions:   {args.patch_size} x {args.patch_size} px (10m GSD -> ~{args.patch_size*10/1000:.1f} x {args.patch_size*10/1000:.1f} km)")
    print(f"    - Native CRS:         {bounds_t1['crs']}")
    print(f"    - Target CRS:         EPSG:4326 (WGS84 Decimal Degrees)")
    print(f"    - Bounding Latitude:  [{bounds_t1['min_lat']:.6f} N, {bounds_t1['max_lat']:.6f} N]")
    print(f"    - Bounding Longitude: [{bounds_t1['min_lon']:.6f} E, {bounds_t1['max_lon']:.6f} E]")
    print(f"    - Top-Left Corner:    Lat {bounds_t1['top_left'][0]:.6f} N, Lon {bounds_t1['top_left'][1]:.6f} E")
    print(f"    - Bottom-Right:       Lat {bounds_t1['bottom_right'][0]:.6f} N, Lon {bounds_t1['bottom_right'][1]:.6f} E")

    print("\n[3] SFAS GATE METRICS (Semantic False-Alarm Suppression)")
    print(f"    - Embedding Size:     {len(v1)}-dim normalized L2 feature vector")
    print(f"    - Cosine Distance:    {cos_dist:.6f} (1 - Cosine Similarity)")
    print(f"    - Cosine Similarity:  {cos_sim:.6f}")
    print(f"    - Decision Threshold: {args.threshold:.2f}")
    print(f"    - SFAS Gate Status:   {gate_status} (flag: '{gate_eval.get('flag', 'N/A')}')")
    if not is_change:
        print(f"    - Suppression Reason: {gate_eval.get('reason', 'Phenological/Seasonal shift')}")

    print("\n[4] DETECTION & GEOSPATIAL ANOMALY METRICS")
    print(f"    - Total BBoxes Found: {len(features)}")
    if top_feature:
        props = top_feature["properties"]
        geom = top_feature["geometry"]
        print(f"    - Top Anomaly Area:   {props.get('area_pixels', 0):.1f} px ({props.get('bbox_width', 0)}w x {props.get('bbox_height', 0)}h)")
        print(f"    - Top GeoJSON Type:   {geom.get('type')}")
        coords = geom.get("coordinates", [[]])[0]
        print(f"    - Top GeoJSON Poly:   {coords[:3]} ... ({len(coords)} vertices)")
    else:
        print("    - Top Anomaly:        None (No significant contours above minimum area)")

    print("\n[5] LATENCY BREAKDOWN (Zero-OOM Execution)")
    print(f"    - Window Read & Prep: {load_time_ms:8.2f} ms")
    print(f"    - Model Embedding:    {embedding_time_ms:8.2f} ms ({embedding_time_ms/2:.2f} ms / patch)")
    print(f"    - SFAS Gate Decision: {gating_time_ms:8.2f} ms")
    print(f"    - Spatial Differencing: {contours_time_ms:6.2f} ms")
    print(f"    ------------------------------------")
    print(f"    - Total Pipeline Time: {total_pipeline_latency_ms:7.2f} ms")
    print("=" * 80 + "\n")

    # 6. Save 3-Panel Visual Output
    print(f"[*] Generating 3-panel visualization figure...")
    fig, axs = plt.subplots(1, 3, figsize=(18, 6), dpi=150)

    # Panel 1: T1
    axs[0].imshow(patch_t1)
    axs[0].set_title(f"T1: {t1_meta['timestamp']}\n({t1_meta['granule']})", fontsize=11, fontweight="bold")
    axs[0].axis("off")

    # Panel 2: T2
    axs[1].imshow(patch_t2)
    axs[1].set_title(f"T2: {t2_meta['timestamp']}\n({t2_meta['granule']})", fontsize=11, fontweight="bold")
    axs[1].axis("off")

    # Panel 3: Difference Mask + Bounding Boxes
    axs[2].imshow(diff_mask, cmap="gray")
    axs[2].set_title(
        f"Difference Mask & Detected BBoxes\nGate: {gate_status} (Dist: {cos_dist:.4f}, Contours: {len(features)})",
        fontsize=11,
        fontweight="bold"
    )
    axs[2].axis("off")

    # Draw red bounding boxes on panel 3
    for feat in features:
        props = feat.get("properties", {})
        if "bbox_x" in props and "bbox_y" in props:
            bx = props["bbox_x"]
            by = props["bbox_y"]
            bw = props["bbox_width"]
            bh = props["bbox_height"]
        else:
            # Fallback to geometry coordinates
            poly = feat["geometry"]["coordinates"][0]
            lons = [p[0] for p in poly]
            lats = [p[1] for p in poly]
            if bounds_t1["crs"] and bounds_t1["crs"].to_string() != "EPSG:4326":
                src_xs, src_ys = reproject_coords("EPSG:4326", bounds_t1["crs"], lons, lats)
            else:
                src_xs, src_ys = lons, lats
            pixels = [rasterio.transform.rowcol(bounds_t1["patch_transform"], x, y) for x, y in zip(src_xs, src_ys)]
            xs = [p[1] for p in pixels]
            ys = [p[0] for p in pixels]
            bx, by, bw, bh = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)

        rect = patches.Rectangle(
            (bx, by), bw, bh,
            linewidth=1.8, edgecolor="red", facecolor="none", linestyle="-"
        )
        axs[2].add_patch(rect)

    plt.tight_layout()
    fig.savefig(output_png, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"[SUCCESS] Verification image successfully saved to:\n  -> {output_png}\n")

if __name__ == "__main__":
    main()
