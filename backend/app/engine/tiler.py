import cv2
import numpy as np
import rasterio
from rasterio.warp import transform as reproject_coords
from shapely.geometry import Polygon, mapping
from typing import List, Dict, Any, Optional
from rasterio.windows import Window

def extract_change_polygons(
    t1_path: str, 
    t2_path: str, 
    min_area: int = 50,
    window: Optional[Window] = None
) -> List[Dict[str, Any]]:
    """
    Identifies where changes happened between two GeoTIFFs/rasters using pixel differencing.
    Extracts the bounding box of the changed pixels and converts it into 
    EPSG:4326 GeoJSON polygons.
    
    Args:
        t1_path (str): File path to the Time 1 GeoTIFF.
        t2_path (str): File path to the Time 2 GeoTIFF.
        min_area (int): Minimum contour area in pixels to filter out noise.
        window (Optional[Window]): Optional rasterio Window to crop spatial subset without loading full raster.
        
    Returns:
        List[Dict[str, Any]]: A list of GeoJSON Feature dictionaries.
    """
    with rasterio.open(t1_path) as src1, rasterio.open(t2_path) as src2:
        if window is not None:
            img1 = src1.read(window=window)
            img2 = src2.read(window=window)
            transform = rasterio.windows.transform(window, src1.transform)
        else:
            img1 = src1.read()
            img2 = src2.read()
            transform = src1.transform
        crs = src1.crs
        
    # Transpose from (C, H, W) to (H, W, C)
    img1 = np.transpose(img1, (1, 2, 0))
    img2 = np.transpose(img2, (1, 2, 0))
    
    # Normalize and convert to uint8 if necessary for cv2 operations
    if img1.dtype != np.uint8:
        img1 = cv2.normalize(img1, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    if img2.dtype != np.uint8:
        img2 = cv2.normalize(img2, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
    # Convert to grayscale
    gray1 = cv2.cvtColor(img1[:, :, :3], cv2.COLOR_RGB2GRAY) if img1.shape[2] >= 3 else img1[:, :, 0]
    gray2 = cv2.cvtColor(img2[:, :, :3], cv2.COLOR_RGB2GRAY) if img2.shape[2] >= 3 else img2[:, :, 0]
    
    # Calculate absolute difference
    diff = cv2.absdiff(gray1, gray2)
    
    # Apply Gaussian Blur to reduce noise
    blur = cv2.GaussianBlur(diff, (5, 5), 0)
    
    # Apply Otsu's thresholding to find the change mask
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Find contours from the thresholded mask
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    features = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
            
        # Get bounding box in pixel coordinates
        x, y, w, h = cv2.boundingRect(contour)
        
        # 4 corners in pixel coordinates: Top-Left, Top-Right, Bottom-Right, Bottom-Left
        # x corresponds to col, y corresponds to row
        corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        
        # Convert pixel coordinates to spatial coordinates using rasterio transform
        spatial_coords = [rasterio.transform.xy(transform, row, col, offset='center') for col, row in corners]
        lons = [c[0] for c in spatial_coords]
        lats = [c[1] for c in spatial_coords]
        
        # Reproject to EPSG:4326 if the source CRS is different
        if crs and crs.to_string() != "EPSG:4326":
            try:
                lons, lats = reproject_coords(crs, "EPSG:4326", lons, lats)
            except Exception:
                pass  # Fallback to original coordinates if reprojection fails
                
        # Create Shapely Polygon
        poly_coords = list(zip(lons, lats))
        
        # Ensure polygon is closed for GeoJSON compliance
        if poly_coords[0] != poly_coords[-1]:
            poly_coords.append(poly_coords[0])
            
        polygon = Polygon(poly_coords)
        
        # Create standard GeoJSON Feature that Leaflet UI can render
        feature = {
            "type": "Feature",
            "geometry": mapping(polygon),
            "properties": {
                "area_pixels": float(area),
                "bbox_width": w,
                "bbox_height": h,
                "bbox_x": x,
                "bbox_y": y
            }
        }
        features.append(feature)
        
    return features
