# 🛰️ Project IdeaX (VAYU-CHRONICLE)

> **Autonomous Semantic Retrieval & Multi-Temporal Change Intelligence Engine**  
> *Targeting SIH 2026 Problem Statement: PS26227 (Ministry of Defence — Indian Army / DGIS)*

---

## 📌 Mission Overview

Standard Earth Observation archives require intelligence analysts to know spatial coordinates and acquisition dates before manual inspection. **Project IdeaX** converts raw satellite archives into a queryable semantic vector space operating strictly within **air-gapped, zero-cloud environments**.

```text
Natural Language / Tile Query
│
▼
[ Local Embedding Tower ]
│
▼
[ Offline HNSW FAISS Index ] ──── (Sub-50ms Search) ────► Ranked Candidates
│
▼
[ Bitemporal Spatial Engine ]
│
▼
[ Semantic False-Alarm Gate ] ── (Rejects Phenology/Shadows) ──► Verified Changes
│
▼
[ Geospatial Commit Stream ] ─── (Immutable Audit Trail) ────► Tactical Output
```

---

## 🛡️ Team Roster & Ownership Matrix

To ensure zero cross-blocking and deliver maximum throughput by September 7th, each member owns a completely decoupled module with clear difficulty tiers and deliverables:

| Tier & Role | Member | Primary Focus | Scope & Deliverables (Internal Round — Sept 7) |
| :--- | :---: | :--- | :--- |
| ![Tier 1](https://img.shields.io/badge/Tier%201-Maximum%20Difficulty-0A84FF?style=flat-square)<br>**Tier 1: Maximum Difficulty** | **A** | **Core Foundation Models, SFAS Gate & System Synthesis** | • Local foundation model inference & quantization (RemoteCLIP / OpenCLIP)<br>• Mathematical Semantic False-Alarm Suppression (SFAS) Gate<br>• Bitemporal change delta calculation & anomaly bounding<br>• End-to-end pipeline wiring, memory budget tuning & air-gap validation |
| ![Tier 2](https://img.shields.io/badge/Tier%202-High%20Difficulty-FF9F0A?style=flat-square)<br>**Tier 2: High Difficulty** | **Y** | **FAISS HNSW Vector Engine & Core Backend** | • In-memory FAISS HNSW query loader & sub-50ms cosine search<br>• Production FastAPI REST architecture (`/search`, `/change`, `/cluster`)<br>• Unsupervised embedding clustering logic (HDBSCAN/KNN)<br>• API data serialization and local IPC routing |
| ![Tier 3](https://img.shields.io/badge/Tier%203-Moderate%20Difficulty-30D158?style=flat-square)<br>**Tier 3: Moderate Difficulty** | **K** | **Satellite Ingestion & Kaggle GPU Pipeline** | • Cloud-Optimized GeoTIFF (COG) windowed tiling via `rasterio`<br>• Kaggle batch embedding pipeline (generating 768-dim vectors)<br>• Georeference, EPSG, and timestamp metadata serialization<br>• FAISS binary index compilation (`.index` and `.json` artifacts) |
| ![Tier 3](https://img.shields.io/badge/Tier%203-Moderate%20Difficulty-64D2FF?style=flat-square)<br>**Tier 3: Moderate Difficulty** | **KM** | **Geospatial Commits, SQLite Audit & Intelligence Brief** | • Git-style "Geospatial Commit" state logic (Pending, Approved, Rejected)<br>• Local SQLite schema for tamper-resistant provenance and audit trails<br>• Automated intelligence report generation logic (JSON export)<br>• Pitch deck technical co-lead |
| ![Tier 4](https://img.shields.io/badge/Tier%204-Beginner%20%2F%20Research-BF5AF2?style=flat-square)<br>**Tier 4: Beginner / Research** | **D** | **Data Testbed, Benchmarking & Pitch Presentation** | • Curating Sentinel-2/Landsat before-and-after tile pairs for testbed<br>• Documenting ground-truth edge cases (seasonal snow, clouds, construction)<br>• Hardware benchmarking (latency, RAM/VRAM footprint metrics)<br>• Leading preparation of the 10-slide high-impact pitch deck |
| ![Tier 4](https://img.shields.io/badge/Tier%204-Beginner%20%2F%20Frontend-FF375F?style=flat-square)<br>**Tier 4: Beginner / Frontend** | **P** | **Tactical Web Dashboard & Interactive Canvas** | • Dark-theme tactical UI (Vite + React + Tailwind CSS)<br>• Interactive before-and-after split-slider comparison component<br>• Search bar, query input, and ranked candidate tile gallery<br>• Displaying confidence chips, false-alarm badges, and commit cards |

---

## ⚡ Architectural Highlights

1. **Air-Gap Native:** Operates with 0 external API calls, running model weights locally using standard CPU and local memory configurations.
2. **Semantic False-Alarm Suppression (SFAS):** Filters out superficial pixel differences caused by seasonal foliage, cloud shadows, and orbital sun angles by calculating latent semantic cosine distance.
3. **Decoupled Heavy Compute:** Uses a batch-indexed Kaggle workflow for heavy vector generation, feeding an ultra-compact in-memory FAISS index (~50MB) on the demonstration laptop.
4. **Verifiable Provenance:** Every approved target is committed to an immutable local audit log, recording the sensor type, timestamp, EPSG coordinates, and analyst ID.

---

## 🚀 Local Development Setup (Windows)

### Prerequisites
* Python 3.10+ (Installed with PATH enabled)
* Node.js v18+ & npm
* Git for Windows

### 1. Repository Setup
```powershell
# Enable long paths for Windows GIS compatibility
git config --system core.longpaths true

# Clone the repository via HTTPS or SSH
git clone https://github.com/aaryanmax/ideax.git
# or: git clone git@github.com:aaryanmax/ideax.git

cd ideax
```

### 2. Backend Initialization
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
python run_server.py
# Server initializes at http://127.0.0.1:8000
```

### 3. Frontend Initialization
```powershell
cd ..\frontend
npm install
npm run dev
# Dashboard available at http://localhost:5173
```

---

## 📝 Future Work & TODOs

- **Multi-Temporal Sweep (`/analyze/sweep`)**: Implement an endpoint that iterates over all available scenes in `data/raw` to estimate the "earliest observation of change", rather than relying on hardcoded T1/T2 pairs.
