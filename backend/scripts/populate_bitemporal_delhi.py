import os
import sys
import json
import numpy as np
import rasterio
import rasterio.warp
from rasterio.windows import Window
from PIL import Image
import cv2
import faiss
import torch
from transformers import CLIPProcessor, CLIPVisionModelWithProjection

# Set paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

T1_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260217T054121_TCI_10m.jp2")
T2_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")
THUMBNAILS_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "thumbnails")
INDEX_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "test_delhi.index")
EMBEDDINGS_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "test_embeddings.npy")
METADATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "test_metadata.json")

def main():
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model on {device}...")
    try:
        # Load RemoteCLIP / base CLIP for 512-dim
        model_id = "openai/clip-vit-base-patch32"
        processor = CLIPProcessor.from_pretrained(model_id)
        model = CLIPVisionModelWithProjection.from_pretrained(model_id).to(device)
        model.eval()
    except Exception as e:
        print(f"Failed to load CLIP model: {e}")
        processor, model = None, None

    patch_size = 512
    # Sample 25 patches (5x5 grid), offsets step by 1500 pixels starting at 2000
    offsets = list(range(2000, 2000 + 5 * 1500, 1500))
    
    metadata = {}
    embeddings = []
    
    # faiss HNSW Flat
    d = 512
    index = faiss.IndexHNSWFlat(d, 32)
    
    with rasterio.open(T1_PATH) as src1, rasterio.open(T2_PATH) as src2:
        patch_idx = 0
        for row_off in offsets:
            for col_off in offsets:
                patch_id = f"patch_{patch_idx}"
                window = Window(col_off, row_off, patch_size, patch_size)
                
                # T1 Read
                arr1 = src1.read([1, 2, 3], window=window)
                arr1 = np.transpose(arr1, (1, 2, 0))
                if arr1.dtype != np.uint8:
                    arr1 = cv2.normalize(arr1, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                
                # T2 Read
                arr2 = src2.read([1, 2, 3], window=window)
                arr2 = np.transpose(arr2, (1, 2, 0))
                if arr2.dtype != np.uint8:
                    arr2 = cv2.normalize(arr2, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                
                img1 = Image.fromarray(arr1)
                img2 = Image.fromarray(arr2)
                
                t1_thumb_path = f"{patch_id}_t1.png"
                t2_thumb_path = f"{patch_id}_t2.png"
                
                img1.save(os.path.join(THUMBNAILS_DIR, t1_thumb_path), format="PNG")
                img2.save(os.path.join(THUMBNAILS_DIR, t2_thumb_path), format="PNG")
                
                # Generate embedding for T2
                if model is not None:
                    inputs = processor(images=img2, return_tensors="pt").to(device)
                    with torch.no_grad():
                        outputs = model(pixel_values=inputs.pixel_values)
                        image_features = outputs.image_embeds
                        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                        emb = image_features.cpu().numpy()[0]
                else:
                    # dummy fallback if airgapped
                    emb = np.random.randn(d).astype(np.float32)
                    emb = emb / np.linalg.norm(emb)
                
                embeddings.append(emb)
                
                # Compute coordinates
                # Center coordinates
                center_x, center_y = src1.transform * (col_off + patch_size / 2, row_off + patch_size / 2)
                lon_lat = rasterio.warp.transform(src1.crs, 'EPSG:4326', [center_x], [center_y])
                center_lon, center_lat = lon_lat[0][0], lon_lat[1][0]
                
                left, bottom, right, top = rasterio.windows.bounds(window, src1.transform)
                poly_lons, poly_lats = rasterio.warp.transform(src1.crs, 'EPSG:4326', 
                                                               [left, right, right, left, left], 
                                                               [bottom, bottom, top, top, bottom])
                coords = [[[lon, lat] for lon, lat in zip(poly_lons, poly_lats)]]
                
                metadata[patch_id] = {
                    "patch_id": patch_id,
                    "col_off": col_off,
                    "row_off": row_off,
                    "width": patch_size,
                    "height": patch_size,
                    "center": [center_lat, center_lon],
                    "t1_date": "2026-02-17",
                    "t2_date": "2026-08-31",
                    "t1_thumbnail": f"/static/tiles/thumbnails/{t1_thumb_path}",
                    "t2_thumbnail": f"/static/tiles/thumbnails/{t2_thumb_path}",
                    "file_path": f"data/processed/T43RFM_20260831T052641_TCI_10m.jp2",
                    "coordinates": coords
                }
                
                print(f"Processed {patch_id}")
                patch_idx += 1
                
    embeddings_np = np.array(embeddings, dtype=np.float32)
    index.add(embeddings_np)
    
    faiss.write_index(index, INDEX_PATH)
    np.save(EMBEDDINGS_PATH, embeddings_np)
    
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Successfully indexed {patch_idx} patches.")

if __name__ == "__main__":
    main()
