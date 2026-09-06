import os
import sys
from rasterio.windows import Window

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.engine.scl_mask import analyze_scl_window, get_scl_path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
t1_tci = os.path.join(project_root, "data", "processed", "T43RFM_20260217T054121_TCI_10m.jp2")

scl_path = get_scl_path(t1_tci, "10m")
print(f"SCL Path (10m req): {scl_path}")

window = Window(4500, 4500, 512, 512)
if scl_path:
    result = analyze_scl_window(scl_path, window, "10m")
    print(f"Result (10m): {result}")
    
    result_20m = analyze_scl_window(scl_path, window, "20m")
    print(f"Result (20m): {result_20m}")
    
    scl_60m_path = get_scl_path(t1_tci, "60m")
    print(f"SCL Path (60m req): {scl_60m_path}")
    if scl_60m_path:
        result_60m = analyze_scl_window(scl_60m_path, window, "60m")
        print(f"Result (60m): {result_60m}")
