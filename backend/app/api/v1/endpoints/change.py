from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from PIL import Image
from rasterio.windows import Window
from scipy.spatial.distance import cosine

from app.engine.embedder import Embedder
from app.engine.gating import evaluate_sfas_change
from app.engine.tactical import TacticalClassifier
from app.engine.tiler import extract_change_polygons, extract_patch_and_bounds
from app.engine.scl_mask import analyze_scl_window, get_scl_path

router = APIRouter()

# Global setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

t1_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260217T054121_TCI_10m.jp2")
t2_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")

_embedder = None
_classifier = None

def get_ai_models():
    global _embedder, _classifier
    if _embedder is None:
        print("[*] Initializing AI Engine Gate and Classifier...")
        _embedder = Embedder()
        _classifier = TacticalClassifier(_embedder)
    return _embedder, _classifier

class ChangeRequest(BaseModel):
    col_off: int
    row_off: int
    width: int = 512
    height: int = 512
    force: bool = False
    resolution: Optional[str] = "10m"

@router.post("/change")
@router.post("")
def analyze_change(request: ChangeRequest):
    t1_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260217T054121_TCI_10m.jp2")
    t2_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")
    patch_id = getattr(request, "patch_id", None)
    
    if patch_id:
        from app.api.v1.endpoints.search import engine_manager
        import glob
        dataset_name = None
        for name, engine in engine_manager.engines.items():
            if isinstance(engine.metadata, dict):
                if patch_id in engine.metadata or any(v.get("patch_id") == patch_id for v in engine.metadata.values()):
                    dataset_name = name
                    break
                    
        if dataset_name and dataset_name.lower() != "delhi":
            raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
            matched_folders = [f for f in os.listdir(raw_dir) if f.lower() == dataset_name.lower()]
            if matched_folders:
                state_dir = os.path.join(raw_dir, matched_folders[0])
                t1_files = glob.glob(os.path.join(state_dir, "**", "*T1*", "**", "*TCI_10m.jp2"), recursive=True)
                t2_files = glob.glob(os.path.join(state_dir, "**", "*T2*", "**", "*TCI_10m.jp2"), recursive=True)
                if not t1_files:
                    t1_files = glob.glob(os.path.join(state_dir, "**", "*T1*.jp2"), recursive=True)
                if not t2_files:
                    t2_files = glob.glob(os.path.join(state_dir, "**", "*T2*.jp2"), recursive=True)
                    
                if t1_files: t1_path = t1_files[0]
                if t2_files: t2_path = t2_files[0]

    if not os.path.exists(t1_path) or not os.path.exists(t2_path):
        raise HTTPException(status_code=500, detail="T1 or T2 JP2 files not found in data/processed/")

    window = Window(request.col_off, request.row_off, request.width, request.height)
    processing_log = []

    # ── Step 1: Patch Extraction ──────────────────────────────────────────────
    try:
        patch_t1, _ = extract_patch_and_bounds(t1_path, window)
        patch_t2, bounds_t2 = extract_patch_and_bounds(t2_path, window)
        processing_log.append({
            "step": 1, "name": "Patch Extraction", "status": "ok",
            "detail": f"{request.width}×{request.height}px window @ col={request.col_off}, row={request.row_off}",
            "value": {
                "t1_scene": os.path.basename(t1_path),
                "t2_scene": os.path.basename(t2_path),
                "window": {"col_off": request.col_off, "row_off": request.row_off,
                            "width": request.width, "height": request.height}
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting patches: {str(e)}")

    pil_t1 = Image.fromarray(patch_t1)
    pil_t2 = Image.fromarray(patch_t2)

    embedder, classifier = get_ai_models()

    # ── Step 2: CLIP Embedding ────────────────────────────────────────────────
    v1 = embedder.embed_image(pil_t1)
    v2 = embedder.embed_image(pil_t2)
    processing_log.append({
        "step": 2, "name": "CLIP Embedding (T1 & T2)", "status": "ok",
        "detail": f"Embedded both patches via CLIP ViT-L/14 → {v1.shape[0]}-dim vectors (L2-normalised)",
        "value": {"model": "clip-vit-large-patch14", "embedding_dim": int(v1.shape[0])}
    })

    # ── Step 3a: SCL Quality Gate — T1 ───────────────────────────────────────
    scl_t1_path = get_scl_path(t1_path, request.resolution)
    scl_result_t1 = analyze_scl_window(scl_t1_path, window, request.resolution) if scl_t1_path else None
    if scl_result_t1:
        pct = round(scl_result_t1.get("flagged_fraction", 0) * 100, 1)
        dominated = scl_result_t1.get("suppression_reason") or "CLEAR"
        processing_log.append({
            "step": 3, "name": "SCL Quality Gate — T1", "status": "suppressed" if scl_result_t1.get("is_masked") else "ok",
            "detail": f"{pct}% flagged pixels at {request.resolution} resolution → {dominated}",
            "value": scl_result_t1
        })
    else:
        processing_log.append({
            "step": 3, "name": "SCL Quality Gate — T1", "status": "warn",
            "detail": "No SCL band found for T1 — quality check skipped", "value": None
        })

    # ── Step 3b: SCL Quality Gate — T2 ───────────────────────────────────────
    scl_t2_path = get_scl_path(t2_path, request.resolution)
    scl_result_t2 = analyze_scl_window(scl_t2_path, window, request.resolution) if scl_t2_path else None
    if scl_result_t2:
        pct = round(scl_result_t2.get("flagged_fraction", 0) * 100, 1)
        dominated = scl_result_t2.get("suppression_reason") or "CLEAR"
        processing_log.append({
            "step": "3b", "name": "SCL Quality Gate — T2", "status": "suppressed" if scl_result_t2.get("is_masked") else "ok",
            "detail": f"{pct}% flagged pixels at {request.resolution} resolution → {dominated}",
            "value": scl_result_t2
        })
    else:
        processing_log.append({
            "step": "3b", "name": "SCL Quality Gate — T2", "status": "warn",
            "detail": "No SCL band found for T2 — quality check skipped", "value": None
        })

    # ── Step 4: SFAS Semantic Gate ────────────────────────────────────────────
    gate_eval = evaluate_sfas_change(v1, v2, threshold=0.15, scl_result_t1=scl_result_t1, scl_result_t2=scl_result_t2)
    cos_dist = float(cosine(v1, v2))
    is_change = gate_eval.get("is_change", False)
    gate_status = "TACTICAL_CHANGE" if is_change else "SUPPRESSED"
    processing_log.append({
        "step": 4, "name": "SFAS Semantic Gate",
        "status": "ok" if is_change else "suppressed",
        "detail": (
            f"Cosine distance = {cos_dist:.4f} (τ = 0.15) → {'CHANGE CONFIRMED' if is_change else 'SUPPRESSED — ' + gate_eval.get('reason', 'semantic similarity too high')}"
        ),
        "value": {"cosine_distance": cos_dist, "threshold": 0.15, "is_change": is_change,
                  "flag": gate_eval.get("flag")}
    })

    # ── Step 5: Pixel Differencing (Tiler) ───────────────────────────────────
    features = []
    if is_change or request.force:
        features = extract_change_polygons(t1_path, t2_path, min_area=50, window=window)
        processing_log.append({
            "step": 5, "name": "Pixel Differencing & Contour Extraction",
            "status": "ok" if features else "warn",
            "detail": f"Otsu threshold on grayscale diff → {len(features)} contour(s) detected (min_area=50px)",
            "value": {"contours_found": len(features), "forced": request.force}
        })
    else:
        processing_log.append({
            "step": 5, "name": "Pixel Differencing & Contour Extraction",
            "status": "suppressed",
            "detail": "Skipped — SFAS gate suppressed this tile as no meaningful change",
            "value": {"contours_found": 0, "forced": False}
        })

    # ── Step 6: Tactical Classification ──────────────────────────────────────
    classification_result = None
    spotrep = None

    if features:
        features_sorted = sorted(features, key=lambda f: f["properties"].get("area_pixels", 0), reverse=True)
        top_feature = features_sorted[0]

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
            processing_log.append({
                "step": 6, "name": "Zero-Shot Tactical Classification",
                "status": "ok",
                "detail": f"Top match: \"{cls_label}\" ({conf:.1f}% confidence, τ=0.07 softmax temperature)",
                "value": {
                    "top_class": cls_label,
                    "confidence": round(classification_result["confidence"], 4),
                    "distribution": classification_result.get("distribution", {})
                }
            })

            # ── Step 7: SPOTREP Generation ────────────────────────────────────
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

            scl_metrics = "CLEAR"
            if scl_result_t2:
                pct = round(scl_result_t2.get("flagged_fraction", 0) * 100, 1)
                dominated = scl_result_t2.get("suppression_reason") or "CLEAR"
                scl_metrics = f"{pct}% FLAGS ({dominated})"
            
            import time
            dist_str = " | ".join([f"{k[:10]}: {v*100:.1f}%" for k, v in classification_result.get("distribution", {}).items()][:3])
            
            spotrep = (
                f"====================================================\n"
                f" TACTICAL SPOTREP (DGIS-STANDARD) - AUTOMATED ANALYSIS \n"
                f"====================================================\n"
                f"DTG             : {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"COORDINATES     : {centroid_lat:.6f} N, {centroid_lon:.6f} E\n"
                f"----------------------------------------------------\n"
                f"STEP 1: SCL QUALITY GATE\n"
                f"        T2 SCENE    : {scl_metrics}\n"
                f"STEP 2: SFAS SEMANTIC GATE\n"
                f"        COS DIST    : {cos_dist:.4f} (τ = 0.15)\n"
                f"        GATE STATUS : {'CONFIRMED CHANGE' if is_change else 'SUPPRESSED'}\n"
                f"STEP 3: PIXEL DIFFERENCING\n"
                f"        CONTOURS    : {len(features)} DETECTED (MIN_AREA=50px)\n"
                f"STEP 4: ZERO-SHOT TACTICAL CLASSIFICATION\n"
                f"        TOP MATCH   : {cls_label.upper()} ({conf:.1f}% CONFIDENCE)\n"
                f"        DISTRIBUTION: {dist_str}\n"
                f"----------------------------------------------------\n"
                f"RECOMMEND ACTION: {action}\n"
                f"===================================================="
            )
            processing_log.append({
                "step": 7, "name": "SPOTREP Generation",
                "status": "ok",
                "detail": f"Recommend action: {action} @ ({centroid_lat:.4f}, {centroid_lon:.4f})",
                "value": {"action": action, "centroid_lat": centroid_lat, "centroid_lon": centroid_lon}
            })
        else:
            processing_log.append({
                "step": 6, "name": "Zero-Shot Tactical Classification", "status": "warn",
                "detail": "Crop region was empty — classification skipped", "value": None
            })
    else:
        processing_log.append({
            "step": 6, "name": "Zero-Shot Tactical Classification", "status": "suppressed",
            "detail": "No contours to classify — gate or tiler returned zero features", "value": None
        })

    return {
        "gate_status": gate_status,
        "cosine_distance": cos_dist,
        "gate_evaluation": gate_eval,
        "classification": classification_result,
        "spotrep": spotrep,
        "processing_log": processing_log,
        "detected_features": {
            "type": "FeatureCollection",
            "features": features
        }
    }
