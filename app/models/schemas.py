"""
Pydantic schemas — the contract between K (data producer), Y (search/backend),
and P (frontend). Everyone codes to these shapes.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TileMetadata(BaseModel):
    """
    One satellite tile + its provenance.
    This is what K writes to metadata.json for EVERY tile.
    """
    tile_id: str = Field(..., description="Unique ID like 'T35UQD_20240315_S2L2A'")
    latitude: float = Field(..., description="Center lat, WGS84")
    longitude: float = Field(..., description="Center lon, WGS84")
    bbox_geojson: Optional[dict] = Field(
        None, description="GeoJSON Polygon of tile bounds"
    )
    acquisition_date: str = Field(
        ..., description="ISO 8601 date, e.g. '2024-03-15'"
    )
    sensor: str = Field(..., description="'Sentinel-2 L2A', 'Sentinel-1 SAR', etc.")
    cloud_cover_pct: Optional[float] = Field(
        None, description="Sentinel-2 only; % cloud cover"
    )
    image_path: str = Field(..., description="Relative path to .tif on disk")
    embedding_index: int = Field(
        ..., description="Row number in FAISS index (0-indexed)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tile_id": "T35UQD_20240315_S2L2A",
                "latitude": 28.5,
                "longitude": 77.2,
                "bbox_geojson": {...},
                "acquisition_date": "2024-03-15",
                "sensor": "Sentinel-2 L2A",
                "cloud_cover_pct": 5.2,
                "image_path": "data/testbed/tiles/T35UQD_20240315.tif",
                "embedding_index": 42,
            }
        }


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    date_range_start: Optional[str] = Field(None, description="ISO 8601 date filter")
    date_range_end: Optional[str] = Field(None, description="ISO 8601 date filter")
    sensor_filter: Optional[str] = Field(
        None, description="e.g. 'Sentinel-2 L2A' to filter by sensor"
    )


class SearchResult(BaseModel):
    tile_id: str
    score: float = Field(..., description="Cosine similarity [0, 1]")
    metadata: TileMetadata


class SearchResponse(BaseModel):
    query: str
    top_k: int
    n_results: int
    results: list[SearchResult]
    execution_time_ms: float


class ChangeDetectionRequest(BaseModel):
    tile_id_t1: str = Field(..., description="Earlier timestamp tile")
    tile_id_t2: str = Field(..., description="Later timestamp tile")
    confidence_threshold: Optional[float] = Field(
        0.5, description="Suppress changes below this confidence"
    )


class ClusterRequest(BaseModel):
    tile_id: str = Field(..., description="Seed tile for similarity search")
    radius_km: Optional[float] = Field(
        50, description="Geographic search radius"
    )
    top_k: int = Field(10, description="Cluster size limit")