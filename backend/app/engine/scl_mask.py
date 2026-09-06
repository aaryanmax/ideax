import os
import numpy as np
import rasterio
from rasterio.windows import Window
from typing import Dict, Any, Optional

SCL_CLASSES = {
    0: {"label": "No Data", "suppression": None},
    1: {"label": "Saturated or Defective", "suppression": None},
    2: {"label": "Dark Area Pixels", "suppression": None},
    3: {"label": "Cloud Shadows", "suppression": "Suppressed: Cloud Shadow Occlusion"},
    4: {"label": "Vegetation", "suppression": None},
    5: {"label": "Bare Soils", "suppression": None},
    6: {"label": "Water", "suppression": None},
    7: {"label": "Unclassified", "suppression": None},
    8: {"label": "Cloud (Medium Probability)", "suppression": "Suppressed: Cloud Occlusion"},
    9: {"label": "Cloud (High Probability)", "suppression": "Suppressed: Cloud Occlusion"},
    10: {"label": "Thin Cirrus", "suppression": "Suppressed: Thin Cirrus Haze"},
    11: {"label": "Snow or Ice", "suppression": "Suppressed: Seasonal Snow/Ice"},
}

def analyze_scl_window(scl_path: str, base_window: Window, resolution: str = "10m", threshold: float = 0.10) -> Dict[str, Any]:
    """
    Analyzes an SCL patch to determine if it should be suppressed.
    base_window is assumed to be in 10m coordinates.
    """
    if not os.path.exists(scl_path):
        return {"is_masked": False, "error": f"SCL path not found: {scl_path}"}
        
    col_off = base_window.col_off
    row_off = base_window.row_off
    width = base_window.width
    height = base_window.height
    
    if "20m" in scl_path:
        scale_factor = 2
    elif "60m" in scl_path:
        scale_factor = 6
    else:
        scale_factor = 1 
        
    scaled_window = Window(
        col_off // scale_factor,
        row_off // scale_factor,
        width // scale_factor,
        height // scale_factor
    )
    
    with rasterio.open(scl_path) as src:
        scl_patch = src.read(1, window=scaled_window)
        
    total_pixels = scl_patch.size
    if total_pixels == 0:
        return {"is_masked": False, "error": "Empty window"}
        
    unique, counts = np.unique(scl_patch, return_counts=True)
    class_counts = dict(zip(unique, counts))
    
    # Calculate flagged fraction
    flagged_classes = [3, 8, 9, 10, 11]
    flagged_pixels = sum(class_counts.get(c, 0) for c in flagged_classes)
    flagged_fraction = float(flagged_pixels) / float(total_pixels)
    
    is_masked = flagged_fraction >= threshold
    
    suppression_reason = None
    dominant_class = None
    recommendation = "Maintain current resolution."
    
    if is_masked:
        # Find dominant flagged class
        dominant_class = max(flagged_classes, key=lambda c: class_counts.get(c, 0))
        suppression_reason = SCL_CLASSES[dominant_class]["suppression"]
        
        if resolution == "10m":
             recommendation = "Cloud/Cirrus detected (>10%) at 10m; suggest switching to 20m SCL/SWIR verification or regional 60m atmospheric check."
        elif resolution == "20m":
             if dominant_class in [8, 9, 10]:
                 recommendation = "High cloud occlusion. Recommend regional 60m atmospheric check."
             else:
                 recommendation = "Occlusion confirmed at 20m."
    else:
        if resolution != "10m":
            recommendation = "Clear conditions detected. Suggest switching to 10m for detailed tactical analysis."
            
    return {
        "is_masked": is_masked,
        "dominant_class": int(dominant_class) if dominant_class is not None else None,
        "suppression_reason": suppression_reason,
        "flagged_fraction": float(flagged_fraction),
        "class_counts": {int(k): int(v) for k, v in class_counts.items()},
        "recommendation": recommendation,
        "resolution_used": resolution
    }

def get_scl_path(tci_path: str, resolution: str) -> Optional[str]:
    """
    Given a TCI path in data/processed, finds the corresponding raw SCL path.
    Example tci_path: data/processed/T43RFM_20260217T054121_TCI_10m.jp2
    """
    filename = os.path.basename(tci_path)
    parts = filename.split('_')
    if len(parts) < 3:
        return None
        
    tile_id = parts[0]
    timestamp = parts[1]
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    raw_dir = os.path.join(project_root, "data", "raw")
    
    scl_res = "20m" if resolution in ["10m", "20m"] else "60m"
    scl_filename = f"{tile_id}_{timestamp}_SCL_{scl_res}.jp2"
    
    for root, dirs, files in os.walk(raw_dir):
        if scl_filename in files:
            return os.path.join(root, scl_filename)
            
    return None
