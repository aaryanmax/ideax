import os
import glob
import shutil
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import rasterio
from rasterio.transform import rowcol

# If rasterio is not fully configured for all projections, we might fallback
try:
    from pyproj import Transformer
    has_pyproj = True
except ImportError:
    has_pyproj = False

from app.engine.ingestion import DataIngestor, latlon_to_utm

router = APIRouter()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

class ValidationRequest(BaseModel):
    lat: float
    lon: float
    dataset_path: str # Path relative to RAW_DATA_DIR or absolute

class IngestRequest(BaseModel):
    mode: str # "safe", "raw", "patch"
    dataset: str # "mumbai", "delhi", etc.
    lat: float = 0.0
    lon: float = 0.0
    t1: str = ""
    t2: str = ""
    input_path: str = "" # For patch mode
    site: str = "Unknown"
    label: str = ""

class ImportRequest(BaseModel):
    source_path: str
    target_folder: str

@router.get("/sources")
def list_sources():
    """Scans data/raw and detects structure types (SAFE, JP2, Patch)."""
    if not os.path.exists(RAW_DATA_DIR):
        return {"sources": []}
    
    sources = []
    # Just list top level and 1 level deep for potential member folders
    for root, dirs, files in os.walk(RAW_DATA_DIR):
        rel_path = os.path.relpath(root, RAW_DATA_DIR)
        if rel_path == ".":
            continue
            
        depth = rel_path.count(os.sep)
        if depth > 2: # Don't go too deep
            continue
            
        # Try to infer structure
        structure_type = "unknown"
        if any(d.endswith(".SAFE") for d in dirs):
            structure_type = "safe"
        elif any(f.endswith(".jp2") for f in files):
            structure_type = "raw_jp2"
        elif any(f.endswith(".png") and ("_t1" in f or "patch" in f) for f in files):
            structure_type = "patch_package"
            
        if structure_type != "unknown":
            sources.append({
                "path": os.path.join("data", "raw", rel_path).replace("\\", "/"),
                "name": rel_path.replace("\\", " / "),
                "type": structure_type
            })
            
    return {"sources": sources}

@router.post("/validate-bounds")
def validate_bounds(req: ValidationRequest):
    """Checks if the lat/lon is inside the bounds of the provided dataset."""
    full_path = req.dataset_path
    if not os.path.isabs(full_path):
        full_path = os.path.join(PROJECT_ROOT, req.dataset_path)
        
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Dataset path not found.")
        
    # Find a sample raster file to check bounds
    sample_file = None
    for root, _, files in os.walk(full_path):
        for f in files:
            if f.endswith(".jp2") or f.endswith(".tif"):
                sample_file = os.path.join(root, f)
                break
        if sample_file:
            break
            
    if not sample_file:
        return {"valid": False, "message": "No valid raster files found to check bounds."}
        
    try:
        with rasterio.open(sample_file) as src:
            crs = src.crs
            # Simple fallback check if we don't use pyproj
            zone = 43 # Default to Mumbai zone if we can't extract it easily
            if crs and crs.is_projected:
                # Assuming UTM
                srs_wkt = crs.to_wkt()
                if 'UTM zone 42' in srs_wkt: zone = 42
                elif 'UTM zone 43' in srs_wkt: zone = 43
                elif 'UTM zone 44' in srs_wkt: zone = 44
                elif 'UTM zone 45' in srs_wkt: zone = 45
                elif 'UTM zone 46' in srs_wkt: zone = 46
            
            easting, northing = latlon_to_utm(req.lat, req.lon, zone)
            row, col = rowcol(src.transform, easting, northing)
            
            width = src.width
            height = src.height
            
            if 0 <= row < height and 0 <= col < width:
                return {
                    "valid": True, 
                    "message": f"Coordinates fall inside tile bounds at pixel ({col}, {row}).",
                    "pixel": {"x": col, "y": row},
                    "dimensions": {"width": width, "height": height}
                }
            else:
                return {
                    "valid": False, 
                    "message": f"Coordinates out of bounds! Pixel would be ({col}, {row}) but image is {width}x{height}.",
                    "pixel": {"x": col, "y": row}
                }
    except Exception as e:
        return {"valid": False, "message": f"Error validating bounds: {str(e)}"}

@router.get("/ai-recommendations")
def get_ai_recommendations(path: str = ""):
    """Provides AI recommended next steps based on the selected path."""
    rec = {
        "status": "ready",
        "recommendations": [
            "Check spatial bounds for the selected site before full ingestion.",
            "If using Level-2A data, the SCL gate will automatically mask heavy clouds."
        ]
    }
    path_up = path.upper()
    if "MEMBER_K" in path_up or "BAUXITE" in path_up:
        rec["recommendations"].append("Detected Bauxite deposit data. Recommended coordinates: 19.506, 83.133.")
    elif "MEMBER_P" in path_up or "COAL" in path_up:
        rec["recommendations"].append("Detected Coal region raw data. Check UTM zone (44N) and use coords: 22.812, 82.801 or 17.258, 81.655.")
    elif "MEMBER_KM" in path_up or "JEWAR" in path_up:
        rec["recommendations"].append("Detected hybrid data. Use patch ingestion mode for patches.")
        
    return rec

@router.post("/ingest")
def run_ingestion(req: IngestRequest, background_tasks: BackgroundTasks):
    """Triggers the ingestion pipeline."""
    # In a real app we might run this in a background task, but for the demo we'll run it synchronously
    # so the frontend can wait for it and get the result immediately.
    ingestor = DataIngestor(dataset_name=req.dataset)
    
    try:
        if req.mode == "safe":
            t1_abs = os.path.join(PROJECT_ROOT, req.t1) if not os.path.isabs(req.t1) else req.t1
            t2_abs = os.path.join(PROJECT_ROOT, req.t2) if not os.path.isabs(req.t2) else req.t2
            res = ingestor.ingest_safe_pair(t1_abs, t2_abs, req.lat, req.lon, req.site, req.label)
        elif req.mode == "raw":
            t1_abs = os.path.join(PROJECT_ROOT, req.t1) if not os.path.isabs(req.t1) else req.t1
            t2_abs = os.path.join(PROJECT_ROOT, req.t2) if not os.path.isabs(req.t2) else req.t2
            res = ingestor.ingest_raw_pair(t1_abs, t2_abs, req.lat, req.lon, req.site, req.label)
        elif req.mode == "patch":
            inp_abs = os.path.join(PROJECT_ROOT, req.input_path) if not os.path.isabs(req.input_path) else req.input_path
            res = ingestor.ingest_patch_package(inp_abs)
        else:
            raise HTTPException(status_code=400, detail="Invalid mode")
            
        return {"status": "success", "message": "Ingestion completed.", "details": "Check catalog for new entries."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-source")
def import_source(req: ImportRequest):
    """Copies a folder from anywhere on the local filesystem into data/raw/."""
    source = req.source_path.strip('\"\'')
    if not os.path.exists(source):
        raise HTTPException(status_code=400, detail="Source path does not exist on the server.")
        
    dest_path = os.path.join(RAW_DATA_DIR, req.target_folder)
    os.makedirs(dest_path, exist_ok=True)
    
    base_name = os.path.basename(os.path.normpath(source))
    if not base_name: # Handle case where source might be 'C:\' or similar
        raise HTTPException(status_code=400, detail="Invalid source path format.")
        
    final_dest = os.path.join(dest_path, base_name)
    
    try:
        if os.path.isdir(source):
            shutil.copytree(source, final_dest, dirs_exist_ok=True)
        else:
            shutil.copy2(source, dest_path)
            
        return {"status": "success", "message": f"Successfully imported to {req.target_folder}/{base_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")

