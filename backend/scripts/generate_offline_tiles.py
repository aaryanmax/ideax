"""
Offline Tactical Tile Generator for VAYU-CHRONICLE
Pre-stages dark tactical raster tiles for Delhi NCR (Zoom 11, 12, 13)
Outputs to both backend/data/map_tiles and frontend/public/map_tiles
"""
import os
import math
from PIL import Image, ImageDraw

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

def generate_tactical_tile(x, y, z):
    """Draw a 256x256 military-grade tactical dark tile."""
    img = Image.new("RGBA", (256, 256), color=(8, 12, 20, 255))
    draw = ImageDraw.Draw(img)

    # Subtle inner grid lines
    grid_color = (22, 34, 52, 255)
    for i in range(32, 256, 32):
        draw.line([(i, 0), (i, 256)], fill=grid_color, width=1)
        draw.line([(0, i), (256, i)], fill=grid_color, width=1)

    # Major center crosshair
    accent_color = (36, 56, 84, 255)
    draw.line([(128, 118), (128, 138)], fill=accent_color, width=1)
    draw.line([(118, 128), (138, 128)], fill=accent_color, width=1)

    # Corner reticles
    reticle_color = (52, 211, 153, 160) # Emerald accent
    reticle_len = 6
    # Top-Left
    draw.line([(4, 4), (4 + reticle_len, 4)], fill=reticle_color, width=1)
    draw.line([(4, 4), (4, 4 + reticle_len)], fill=reticle_color, width=1)
    # Top-Right
    draw.line([(251, 4), (251 - reticle_len, 4)], fill=reticle_color, width=1)
    draw.line([(251, 4), (251, 4 + reticle_len)], fill=reticle_color, width=1)
    # Bottom-Left
    draw.line([(4, 251), (4 + reticle_len, 251)], fill=reticle_color, width=1)
    draw.line([(4, 251), (4, 251 - reticle_len)], fill=reticle_color, width=1)
    # Bottom-Right
    draw.line([(251, 251), (251 - reticle_len, 251)], fill=reticle_color, width=1)
    draw.line([(251, 251), (251, 251 - reticle_len)], fill=reticle_color, width=1)

    # Coordinate calculation
    lat, lon = num2deg(x, y, z)
    coord_str = f"{lat:.2f}N {lon:.2f}E"
    tile_str = f"Z{z} [{x},{y}]"

    # Draw small label text
    text_color = (100, 130, 165, 180)
    draw.text((8, 8), tile_str, fill=text_color)
    draw.text((8, 240), coord_str, fill=text_color)

    # Outer border
    border_color = (18, 28, 44, 255)
    draw.rectangle([(0, 0), (255, 255)], outline=border_color, width=1)

    return img

def stage_tiles():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(base_dir)
    out_dirs = [
        os.path.join(root_dir, "data", "map_tiles"),
        os.path.join(root_dir, "frontend", "public", "map_tiles")
    ]

    # Delhi NCR tactical focus region
    lat_max, lat_min = 28.85, 28.25
    lon_min, lon_max = 76.20, 76.95

    zoom_levels = [11, 12, 13]
    total_staged = 0

    for z in zoom_levels:
        x_min, y_min = deg2num(lat_max, lon_min, z)
        x_max, y_max = deg2num(lat_min, lon_max, z)

        x_start, x_end = min(x_min, x_max), max(x_min, x_max)
        y_start, y_end = min(y_min, y_max), max(y_min, y_max)

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                tile_img = generate_tactical_tile(x, y, z)
                for target_base in out_dirs:
                    tile_dir = os.path.join(target_base, str(z), str(x))
                    os.makedirs(tile_dir, exist_ok=True)
                    tile_path = os.path.join(tile_dir, f"{y}.png")
                    tile_img.save(tile_path, "PNG", optimize=True)
                total_staged += 1

    print(f"Successfully staged {total_staged} tiles across zoom levels {zoom_levels} to {out_dirs}")

if __name__ == "__main__":
    stage_tiles()
