from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from PIL import Image
from rasterio.windows import Window
from scipy.spatial.distance import cosine

from app.engine.embedder import Embedder
from app.engine.gating import evaluate_sfas_change
from app.engine.tactical import TacticalClassifier
from app.engine.tiler import extract_change_polygons, extract_patch_and_bounds

router = APIRouter()

# Global setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

t1_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260217T054121_TCI_10m.jp2")
t2_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")

print("[*] Initializing AI Engine Gate and Classifier...")
embedder = Embedder()
classifier = TacticalClassifier(embedder)

class ChangeRequest(BaseModel):
    col_off: int
    row_off: int
    width: int = 512
    height: int = 512
    force: bool = False

@router.post("/change")
@router.post("")
def analyze_change(request: ChangeRequest):
    if not os.path.exists(t1_path) or not os.path.exists(t2_path):
        raise HTTPException(status_code=500, detail="T1 or T2 JP2 files not found in data/processed/")
        
    window = Window(request.col_off, request.row_off, request.width, request.height)
    
    # 1. Extract Patches
    try:
        patch_t1, _ = extract_patch_and_bounds(t1_path, window)
        patch_t2, bounds_t2 = extract_patch_and_bounds(t2_path, window)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting patches: {str(e)}")
        
    pil_t1 = Image.fromarray(patch_t1)
    pil_t2 = Image.fromarray(patch_t2)
    
    # 2. Embed
    v1 = embedder.embed_image(pil_t1)
    v2 = embedder.embed_image(pil_t2)
    
    # 3. SFAS Gate
    gate_eval = evaluate_sfas_change(v1, v2, threshold=0.15)
    cos_dist = float(cosine(v1, v2))
    is_change = gate_eval.get("is_change", False)
    gate_status = "TACTICAL_CHANGE" if is_change else "SUPPRESSED"
    
    # 4. Tiler spatial differencing
    features = []
    if is_change or request.force:
        features = extract_change_polygons(t1_path, t2_path, min_area=50, window=window)
        
    # 5. Tactical Classification on top feature
    classification_result = None
    spotrep = None
    
    if features:
        features_sorted = sorted(features, key=lambda f: f["properties"].get("area_pixels", 0), reverse=True)
        top_feature = features_sorted[0]
        
        # Crop bbox
        props = top_feature.get("properties", {})
        bx = props.get("bbox_x", 0)
        by = props.get("bbox_y", 0)
        bw = props.get("bbox_width", request.width)
        bh = props.get("bbox_height", request.height)
        
        bx, by = max(0, bx), max(0, by)
        crop_t2 = patch_t2[by:by+bh, bx:bx+bw]
        
        if crop_t2.shape[0] > 0 and crop_t2.shape[1] > 0:
            pil_crop = Image.fromarray(crop_t2)
            crop_emb = embedder.embed_image(pil_crop)
            classification_result = classifier.classify(crop_emb)
            
            cls_label = classification_result["classification"]
            conf = classification_result["confidence"] * 100
            
            # Formulate SPOTREP
            poly = top_feature["geometry"]["coordinates"][0]
            lons = [p[0] for p in poly]
            lats = [p[1] for p in poly]
            centroid_lon = sum(lons) / len(lons)
            centroid_lat = sum(lats) / len(lats)
            
            action = "MONITOR"
            if "vegetation" in cls_label.lower() or "crop" in cls_label.lower():
                action = "SUPPRESS_LOG_BENIGN"
            elif any(k in cls_label.lower() for k in ["bunker", "convoy", "cleared", "trench", "berm", "road"]):
                action = "IMMEDIATE_TASK_UAV_RECON"
                
            spotrep = (
                f"ACQUISITION DTG : 2026-08-31 05:26:41 UTC\n"
                f"COORDINATES     : {centroid_lat:.6f} N, {centroid_lon:.6f} E\n"
                f"CLASSIFICATION  : {cls_label.upper()} ({conf:.1f}% confidence)\n"
                f"RECOMMEND ACTION: {action}"
            )
            
    return {
        "gate_status": gate_status,
        "cosine_distance": cos_dist,
        "gate_evaluation": gate_eval,
        "classification": classification_result,
        "spotrep": spotrep,
        "detected_features": {
            "type": "FeatureCollection",
            "features": features
        }
    }
