"""
Pydantic schemas for semantic search, change detection, and clustering.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

class TileMetadata(BaseModel):
    tile_id: str
    embedding_index: Optional[int] = None
    
    class Config:
        extra = 'allow'

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    sensor_filter: Optional[str] = None

class SearchResult(BaseModel):
    tile_id: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    query: str
    top_k: int
    n_results: int
    results: List[Any]
    execution_time_ms: float

class ChangeDetectionRequest(BaseModel):
    tile_id_t1: str
    tile_id_t2: str

class ClusterRequest(BaseModel):
    tile_id: str
    top_k: int = 5

class ChangeRequest(BaseModel):
    col_off: int
    row_off: int
    width: int = 512
    height: int = 512
    force: bool = False

class ChangeResponse(BaseModel):
    status: str

class AuditCommitRequest(BaseModel):
    record_id: Optional[int] = None
    patch_id: Optional[str] = None
    new_status: str  # "APPROVED" or "REJECTED"
    confidence: Optional[float] = None
    analyst_id: Optional[str] = "OFFICER_DELHI_01"
    rationale: Optional[str] = None
    latitude: Optional[float] = 28.5
    longitude: Optional[float] = 76.5

class AuditRecordOut(BaseModel):
    id: int
    query_string: Optional[str] = None
    latitude: float
    longitude: float
    timestamp: Optional[Any] = None
    sensor_type: Optional[str] = "Sentinel-2"
    status: Optional[str] = "PENDING"
    confidence_score: Optional[float] = None
    hash_value: Optional[str] = None
    reviewed_at: Optional[Any] = None
    patch_id: Optional[str] = None
    t1_timestamp: Optional[Any] = None
    t2_timestamp: Optional[Any] = None
    t1_image_path: Optional[str] = None
    t2_image_path: Optional[str] = None
    geojson_polygon: Optional[str] = None
    sfas_confidence: Optional[float] = None
    analyst_id: Optional[str] = None
    analyst_rationale: Optional[str] = None
    extra_metadata: Optional[str] = None

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    total: int
    records: List[AuditRecordOut]

class SimilarSearchRequest(BaseModel):
    patch_id: str
    top_k: int = 6
    cluster_results: bool = True
    eps_km: float = 15.0
    min_samples: int = 2

class DiscoveryClusterGroup(BaseModel):
    cluster_id: int
    callsign: str
    patch_count: int
    centroid: List[float]

class DiscoveryResponse(BaseModel):
    source_patch_id: str
    total_matches: int
    features: List[Dict[str, Any]]
    clusters: List[DiscoveryClusterGroup]
    tactical_summary: str