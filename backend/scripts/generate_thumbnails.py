import os
import sys
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from PIL import Image
import cv2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

def main():
    metadata_path = os.path.join(PROJECT_ROOT, "data", "processed", "test_metadata.json")
    jp2_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")
    thumbnails_dir = os.path.join(PROJECT_ROOT, "data", "processed", "thumbnails")

    if not os.path.exists(metadata_path):
        print(f"[ERROR] Metadata not found at {metadata_path}")
        sys.exit(1)
    if not os.path.exists(jp2_path):
        print(f"[ERROR] JP2 raster not found at {jp2_path}")
        sys.exit(1)

    os.makedirs(thumbnails_dir, exist_ok=True)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    patch_size = 512
    start_col, start_row = 4000, 4000

    print(f"[*] Generating RGB web thumbnails from {os.path.basename(jp2_path)}...")

    with rasterio.open(jp2_path) as src:
        for k, rec in metadata.items():
            patch_id = rec.get("patch_id", f"patch_{k}")
            try:
                idx = int(k)
            except ValueError:
                idx = int(patch_id.replace("patch_", "")) if "patch_" in patch_id else 0

            grid_x = idx % 5
            grid_y = idx // 5
            col = start_col + grid_x * patch_size
            row = start_row + grid_y * patch_size

            # Ensure within raster bounds
            if col + patch_size > src.width or row + patch_size > src.height:
                print(f"[!] Skipping {patch_id}: outside raster bounds ({col}, {row})")
                continue

            window = Window(col, row, patch_size, patch_size)
            # Read bands 1, 2, 3 (Red, Green, Blue)
            arr = src.read([1, 2, 3], window=window)
            arr = np.transpose(arr, (1, 2, 0))

            if arr.dtype != np.uint8:
                arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

            thumb_filename = f"{patch_id}.png"
            thumb_path = os.path.join(thumbnails_dir, thumb_filename)

            img = Image.fromarray(arr)
            img.save(thumb_path, format="PNG")

            thumb_url = f"/static/tiles/thumbnails/{thumb_filename}"
            rec["thumbnail_url"] = thumb_url
            rec["col_off"] = col
            rec["row_off"] = row
            print(f"  [+] Created {thumb_filename} (col={col}, row={row}) -> {thumb_url}")

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    print(f"[SUCCESS] Updated {len(metadata)} patches with thumbnails in {metadata_path}")

if __name__ == "__main__":
    main()
