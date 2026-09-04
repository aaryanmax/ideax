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