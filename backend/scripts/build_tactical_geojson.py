"""
Generates high-precision GeoJSON vector dataset for Delhi NCR & Tactical Surveillance Sectors.
"""
import json
import os

features = [
    # 1. Delhi NCT Outer Perimeter (Administrative Boundary)
    {
        "type": "Feature",
        "properties": {
            "name": "National Capital Territory of Delhi (NCT)",
            "code": "NCT-DELHI",
            "category": "administrative",
            "tier": 1,
            "description": "Delhi Capital Region Sovereign Jurisdiction Perimeter"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [76.842, 28.530],
                [76.835, 28.580],
                [76.865, 28.645],
                [76.920, 28.710],
                [76.995, 28.780],
                [77.060, 28.840],
                [77.135, 28.880],
                [77.195, 28.865],
                [77.240, 28.815],
                [77.295, 28.760],
                [77.335, 28.715],
                [77.345, 28.640],
                [77.320, 28.570],
                [77.330, 28.515],
                [77.290, 28.455],
                [77.220, 28.410],
                [77.150, 28.435],
                [77.100, 28.490],
                [77.025, 28.510],
                [76.940, 28.500],
                [76.842, 28.530]
            ]]
        }
    },

    # 2. NCR Strategic Districts
    {
        "type": "Feature",
        "properties": {
            "name": "Gurugram Tactical Sector",
            "code": "HR-GURUGRAM",
            "category": "district",
            "tier": 2,
            "description": "South-Western Industrial & Cyber Corridor / NH-48 Gateway"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [76.880, 28.510],
                [77.025, 28.510],
                [77.100, 28.490],
                [77.115, 28.400],
                [77.100, 28.310],
                [76.980, 28.270],
                [76.870, 28.320],
                [76.800, 28.390],
                [76.820, 28.460],
                [76.880, 28.510]
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Faridabad Tactical Sector",
            "code": "HR-FARIDABAD",
            "category": "district",
            "tier": 2,
            "description": "South-Eastern Industrial Manufacturing Belt"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [77.220, 28.410],
                [77.290, 28.455],
                [77.350, 28.450],
                [77.400, 28.380],
                [77.380, 28.270],
                [77.280, 28.240],
                [77.200, 28.290],
                [77.180, 28.360],
                [77.220, 28.410]
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Noida / Greater Noida Sector",
            "code": "UP-GB-NAGAR",
            "category": "district",
            "tier": 2,
            "description": "Eastern Electronics, IT & Yamuna Expressway Logistics Hub"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [77.320, 28.570],
                [77.380, 28.610],
                [77.480, 28.580],
                [77.560, 28.490],
                [77.550, 28.380],
                [77.450, 28.340],
                [77.350, 28.410],
                [77.330, 28.515],
                [77.320, 28.570]
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Ghaziabad Sector",
            "code": "UP-GHAZIABAD",
            "category": "district",
            "tier": 2,
            "description": "North-Eastern Transit Hub / Hindon AFB Tactical Sector"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [77.335, 28.715],
                [77.420, 28.750],
                [77.530, 28.720],
                [77.520, 28.630],
                [77.420, 28.610],
                [77.345, 28.640],
                [77.335, 28.715]
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Jhajjar Tactical Sector (T43RFM Ground Swath)",
            "code": "HR-JHAJJAR",
            "category": "district",
            "tier": 2,
            "description": "Western Tactical Terrain / Primary Testbed Sector for Sentinel-2 AI Index"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [76.842, 28.530],
                [76.750, 28.520],
                [76.620, 28.470],
                [76.510, 28.540],
                [76.480, 28.650],
                [76.580, 28.730],
                [76.720, 28.730],
                [76.835, 28.580],
                [76.842, 28.530]
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Sonipat Tactical Sector",
            "code": "HR-SONIPAT",
            "category": "district",
            "tier": 2,
            "description": "Northern Agrarian & Logistics Corridor / GT Road Spine"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [76.995, 28.780],
                [76.920, 28.880],
                [76.880, 29.020],
                [77.020, 29.080],
                [77.160, 29.020],
                [77.195, 28.865],
                [77.135, 28.880],
                [77.060, 28.840],
                [76.995, 28.780]
            ]]
        }
    },

    # 3. Waterway Corridors
    {
        "type": "Feature",
        "properties": {
            "name": "Yamuna River Corridor",
            "code": "RIVER-YAMUNA",
            "category": "waterway",
            "tier": 1,
            "description": "Primary Drainage Basin & Tactical Barrier flowing North-to-South"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.190, 28.880],
                [77.210, 28.810],
                [77.225, 28.735],
                [77.240, 28.690],
                [77.252, 28.650],
                [77.265, 28.610],
                [77.285, 28.560],
                [77.310, 28.500],
                [77.340, 28.430],
                [77.380, 28.350],
                [77.440, 28.250]
            ]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Najafgarh Drain / Sahibi River Channel",
            "code": "CANAL-NAJAFGARH",
            "category": "waterway",
            "tier": 2,
            "description": "Western Drainage Channel into Yamuna Confluence at Wazirabad"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [76.880, 28.470],
                [76.930, 28.520],
                [76.990, 28.580],
                [77.080, 28.640],
                [77.150, 28.690],
                [77.215, 28.715]
            ]
        }
    },

    # 4. Strategic Transport Arteries & Expressways
    {
        "type": "Feature",
        "properties": {
            "name": "Western Peripheral Expressway (KMP)",
            "code": "EXPR-KMP",
            "category": "expressway",
            "tier": 1,
            "description": "Kundli-Manesar-Palwal 135.6km Strategic Heavy Transit Ring"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.080, 28.980],
                [76.940, 28.910],
                [76.810, 28.820],
                [76.710, 28.720],
                [76.670, 28.600],
                [76.720, 28.450],
                [76.850, 28.350],
                [76.940, 28.280],
                [77.100, 28.210],
                [77.280, 28.180]
            ]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Eastern Peripheral Expressway (KGP)",
            "code": "EXPR-KGP",
            "category": "expressway",
            "tier": 1,
            "description": "Kundli-Ghaziabad-Palwal 135km Strategic Heavy Transit Ring"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.100, 28.980],
                [77.250, 28.940],
                [77.400, 28.860],
                [77.520, 28.730],
                [77.560, 28.580],
                [77.550, 28.420],
                [77.450, 28.270],
                [77.300, 28.180]
            ]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "NH-48 Delhi-Gurugram Expressway",
            "code": "EXPR-NH48",
            "category": "expressway",
            "tier": 1,
            "description": "Primary Strategic Multi-Lane Artery to Western Command & Gujarat"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.150, 28.590],
                [77.100, 28.540],
                [77.040, 28.490],
                [76.980, 28.420],
                [76.900, 28.360],
                [76.820, 28.300]
            ]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Delhi Ring Road Core Circuit",
            "code": "RING-ROAD-CORE",
            "category": "expressway",
            "tier": 2,
            "description": "Inner Tactical Transit Loop around New Delhi Administrative District"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.180, 28.660],
                [77.230, 28.660],
                [77.250, 28.610],
                [77.230, 28.560],
                [77.170, 28.560],
                [77.150, 28.610],
                [77.180, 28.660]
            ]
        }
    },

    # 5. Surveillance Operational AOI Swath
    {
        "type": "Feature",
        "properties": {
            "name": "Delhi NCR Tactical Surveillance Footprint (S2-T43RFM)",
            "code": "AOI-DELHI-T43RFM",
            "category": "surveillance_aoi",
            "tier": 1,
            "description": "Primary Surveillance Sector indexed for AI change detection (lat 28.17-28.72, lon 76.25-76.87)"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [76.228, 28.170],
                [76.870, 28.170],
                [76.870, 28.742],
                [76.228, 28.742],
                [76.228, 28.170]
            ]]
        }
    },

    # 6. Mumbai Littoral Coastal Sector (Secondary Surveillance Sector)
    {
        "type": "Feature",
        "properties": {
            "name": "Mumbai Littoral Surveillance Sector (Offshore EEZ)",
            "code": "AOI-MUMBAI-LITTORAL",
            "category": "surveillance_aoi",
            "tier": 1,
            "description": "Western Naval Command Littoral Surveillance Area (lat 18.6-19.6, lon 72.5-73.4)"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [72.500, 18.600],
                [73.400, 18.600],
                [73.400, 19.600],
                [72.500, 19.600],
                [72.500, 18.600]
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Mumbai Island & Coastal Contour",
            "code": "MUMBAI-COASTLINE",
            "category": "waterway",
            "tier": 2,
            "description": "Arabian Sea Littoral Coastal Line & Harbor Entrance"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [72.780, 18.900],
                [72.820, 18.950],
                [72.830, 19.050],
                [72.825, 28.720], # wait, lat in Mumbai is ~19
                [72.820, 19.120],
                [72.810, 19.220],
                [72.830, 19.300]
            ]
        }
    }
]

# Fix Mumbai coastline coordinate typo
for f in features:
    if f["properties"]["code"] == "MUMBAI-COASTLINE":
        f["geometry"]["coordinates"] = [
            [72.800, 18.890],
            [72.815, 18.920],
            [72.830, 18.960],
            [72.840, 19.010],
            [72.825, 19.060],
            [72.815, 19.130],
            [72.800, 19.200],
            [72.810, 19.280],
            [72.820, 19.350]
        ]

geojson_data = {
    "type": "FeatureCollection",
    "metadata": {
        "title": "VAYU-CHRONICLE Tactical Vector GIS Dataset",
        "format": "GeoJSON",
        "crs": "urn:ogc:def:crs:OGC:1.3:CRS84",
        "air_gapped_compatible": True
    },
    "features": features
}

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(base_dir)
out_file = os.path.join(root_dir, "frontend", "src", "data", "delhi_ncr_tactical_boundaries.json")

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f, indent=2)

print(f"Successfully generated {out_file} with {len(features)} tactical features.")
