# 🤖 SYSTEM INSTRUCTION: ARCHITECTURE & IMPLEMENTATION SPECIFICATION
**Project VAYU-CHRONICLE (SIH 2026 - PS26227)**
**Target Audience:** AI Coding Agents / LLM Assistants

## 🎯 AGENT CONTEXT & DIRECTIVE
You are an Expert Lead AI & Full-Stack Architect operating in **September 2026**. You are assisting in building an offline, military-grade geospatial intelligence system. 

**CRITICAL RULES FOR GENERATING CODE:**
1. **Air-Gapped Operation:** The system MUST run entirely offline. Do NOT write code that calls OpenAI, HuggingFace APIs, cloud databases (Pinecone/Supabase), or external map tile providers (like Mapbox cloud).
2. **Resource Constraints:** The host machine has an i5 CPU, 24GB RAM, and a GTX 1650 (4GB VRAM). All deep learning inference must be optimized for CPU or low-VRAM execution (use ONNXRuntime, INT8 quantization, or low-memory PyTorch configurations).
3. **No Deprecated Code:** Use ONLY the 2026 LTS/stable library paradigms listed below.

---

## 📦 2026 LTS DEPENDENCY MATRIX & SYNTAX RULES

### Backend (Python 3.12+)
*   **FastAPI (>= 0.115.0):** Use `Lifespan` context managers instead of deprecated `@app.on_event`.
*   **Pydantic (>= 2.9.0):** Strictly use Pydantic V2 syntax (`model_dump()`, `model_validate()`, `Field()`). Do not use V1 methods.
*   **SQLAlchemy (>= 2.0.30):** Strictly use SQLAlchemy 2.0 paradigms. Use `Mapped` and `mapped_column` for models. Use `session.scalars(select(...))` instead of `session.query()`.
*   **Vector Search:** `faiss-cpu (>= 1.9.0)`. Use `IndexHNSWFlat` for fast CPU search.
*   **Geospatial:** `rasterio (>= 1.4.0)`, `shapely (>= 2.0)`.
*   **Inference:** `onnxruntime (>= 1.19.0)` or `torch (>= 2.4.0)`.

### Frontend (Node 20+ / React 19)
*   **Framework:** Vite 6 + React 19. (Use standard Hooks, avoid legacy class components).
*   **Styling:** Tailwind CSS 3.4/4.0. 
*   **Mapping:** `react-leaflet` (Configure for local tile serving, disable external OSM requests).
*   **State:** Use `zustand` for global state (lighter than Redux).
*   **Data Fetching:** Standard `fetch` or modern `axios` with standard React `useEffect` or React Query v5.

---

## 🧠 CORE MODULE IMPLEMENTATION LOGIC

### Module 1: Local Foundation Model Inference (`app/engine/embedder.py`)
*   **Goal:** Convert text queries and $512 \times 512$ GeoTIFF patches into 512-dimensional vectors.
*   **Implementation:** 
    *   Load the model locally from `backend/models/`. 
    *   If using HuggingFace `transformers`, strictly set `local_files_only=True`.
    *   Return normalized $L2$ vectors as 1D numpy arrays (`dtype=float32`).

### Module 2: In-Memory Vector Index (`app/engine/vector_index.py`)
*   **Goal:** Sub-50ms similarity search.
*   **Implementation:**
    *   Use `faiss.IndexHNSWFlat(d, 32)` where `d=512` or `768`.
    *   Ensure the index is loaded into RAM upon FastAPI startup via the lifespan context manager.
    *   Map FAISS integer IDs back to file paths and metadata using a synchronized in-memory dictionary loaded from `metadata.json`.

### Module 3: Semantic False-Alarm Suppression (SFAS) Gate (`app/engine/gating.py`)
*   **Goal:** Filter seasonal changes using latent math.
*   **Implementation:**
    *   Input: $E_{T1}$ (Vector for Time 1) and $E_{T2}$ (Vector for Time 2).
    *   Calculate Cosine Distance: `distance = scipy.spatial.distance.cosine(E_T1, E_T2)`.
    *   Logic: If `distance > THRESHOLD` (e.g., 0.15), return `{"is_change": True, "confidence": (distance * scale)}`.
    *   If `distance <= THRESHOLD`, return `{"is_change": False, "reason": "Semantic similarity indicates environmental/phenological shift"}`.

### Module 4: Spatial Delta & Bounding Box (`app/engine/tiler.py`)
*   **Goal:** Identify where the change happened in the image.
*   **Implementation:**
    *   Read $T_1$ and $T_2$ rasters using `rasterio`.
    *   Use `cv2.absdiff` on grayscale arrays to find pixel differences. Apply Gaussian Blur and Otsu's thresholding.
    *   Extract contours (`cv2.findContours`). Filter out small noise contours.
    *   Use `rasterio.transform.xy` to convert pixel coordinates of the bounding boxes into real-world EPSG:4326 GeoJSON polygons.

---

## 📜 API CONTRACTS (Pydantic V2 Schemas)

Agents must strictly adhere to these data contracts located in `app/schemas/`.

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SearchQuery(BaseModel):
    query: str = Field(..., description="Natural language search prompt")
    top_k: int = Field(default=5, ge=1, le=50)

class TileResult(BaseModel):
    tile_id: str
    file_path: str
    acquisition_date: str
    confidence_score: float
    coordinates_geojson: Dict[str, Any]

class ChangeRequest(BaseModel):
    tile_id: str
    timestamp_t1: str
    timestamp_t2: str

class ChangeResponse(BaseModel):
    is_tactical_change: bool
    sfas_confidence: float
    suppression_reason: Optional[str] = None
    bounding_boxes_geojson: Optional[List[Dict[str, Any]]] = None

class AuditCommit(BaseModel):
    analyst_id: str
    tile_id: str
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    rationale: str

```

---

## 🗄️ LOCAL DATABASE SCHEMA (SQLAlchemy 2.0)

Agents must format `app/db/models.py` using the modern declarative mapping.

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class GeospatialCommit(Base):
    __tablename__ = "geospatial_commits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analyst_id: Mapped[str] = mapped_column(String(50))
    tile_id: Mapped[str] = mapped_column(String(100), index=True)
    decision: Mapped[str] = mapped_column(String(20)) # APPROVE / REJECT
    confidence_score: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    geojson_polygon: Mapped[str] = mapped_column(String) # Stored as JSON string

```

---

## 🖥️ FRONTEND ARCHITECTURE DIRECTIVES

* **No API Keys:** The frontend must not expect Google Maps API keys or Mapbox tokens. Use standard Leaflet with locally served static tile overlays, or simple image canvas rendering.
* **Split-Slider:** Implement the T1/T2 comparison using standard CSS `clip-path` or a lightweight library like `react-compare-slider`.
* **State:** Use Zustand to store the current `SearchQuery` results so navigating between the "Search Screen" and "Change Analysis Screen" does not wipe the results.
* **Tailwind:** Use strict dark-mode (`bg-slate-900`, `text-slate-100`, `border-slate-700`) to match military aesthetic requirements.

---

**END OF SPECIFICATION**
*(Agents: Acknowledge this document before generating new code blocks. Adhere strictly to the air-gap and versioning constraints.)*
