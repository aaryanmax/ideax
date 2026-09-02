# 🛠️ Project IdeaX: Team Engineering & Collaboration Guide

> **Internal Repository:** `git@github.com:aaryanmax/ideax.git`  
> **Target Path on Lead Machine:** `Projects/ideax/`  
> **Platform Target:** Windows 10/11 (PowerShell) & Local Air-Gapped Python Environment

---

## 1. Initial One-Time Setup Protocol (Every Member)

Run these steps in order using an **Administrator PowerShell** on Windows.

### Step 1.1: Enable Windows Long Paths (GIS Prerequisite)
Deep satellite raster directory structures will fail on Windows unless long paths are enabled:
```powershell
git config --system core.longpaths true
```

### Step 1.2: Clone the Repository via SSH
Navigate to your development root and clone the project:
```powershell
cd C:\Projects
git clone git@github.com:aaryanmax/ideax.git
cd ideax
```

### Step 1.3: Configure Git User & Safety Rules
Ensure Git commits match your identity:
```powershell
git config user.name "Your Name"
git config user.email "your.college.or.github@email.com"

# Normalize line endings to prevent cross-platform file dirtying
git config core.autocrlf false
git config core.eol lf
```

### Step 1.4: Set Up Local Virtual Environment (Python)
If script execution is blocked on Windows, allow local scripts once:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Initialize backend environment
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

---

## 2. Strict Branching Protocol

Direct pushes to `main` and `dev` are strictly disabled. All work must follow a structured three-tier branching model:

```text
       main  ──────────────────────────────────────● (Stable Release / Evaluator Demo Tag)
               ▲
               │ (Pull Request approved by Lead A)
        dev  ──┴──────────●──────────────●───────── (Integration & QA Testing)
                           ▲              ▲
                           │              │ (PR merge after review)
   feature/k-kaggle  ──────┘              │
   feature/p-tactical-ui ─────────────────┘
```

* **`main`**: Reserved solely for tested, production-grade milestones demonstrated to evaluators (e.g., `v0.1.0-internal`, `v1.0-sih2026`).
* **`dev`**: Shared integration branch where members combine and test their decoupled features.
* **`feature/<member-initial>-<module-name>`**: Dedicated working branch for an individual task.

### Branch Naming Conventions:
* `feature/a-gate-orchestrator` — Core Foundation Models & SFAS Gate (Member **A**)
* `feature/k-kaggle-tiler` — Satellite Ingestion & Kaggle GPU Pipeline (Member **K**)
* `feature/y-faiss-search` — FAISS HNSW Vector Engine & Core Backend (Member **Y**)
* `feature/km-commit-log` — Geospatial Commits & SQLite Audit (Member **KM**)
* `feature/d-testbed-benchmarks` — Data Testbed & Hardware Benchmarking (Member **D**)
* `feature/p-tactical-ui` — Tactical Web Dashboard & Interactive Canvas (Member **P**)

---

## 3. Standard Daily Git Workflow

### Starting a New Task
Always branch off the latest `dev` to prevent merge conflicts:
```powershell
git checkout dev
git pull origin dev
git checkout -b feature/<your-initials>-<task-name>
```

### Staging and Committing Changes
Use **Conventional Commits** so the project audit trail is clear and professional:
```powershell
# 1. Check changed files
git status

# 2. Stage specific code files (NEVER use 'git add .' without verifying!)
git add backend/app/engine/vector_index.py

# 3. Commit with structured tags
git commit -m "feat(backend): implement in-memory HNSW index loader"
```

#### Commit Prefix Standards:
* `feat`: A newly built feature, algorithm, or endpoint
* `fix`: A bug fix or spatial logic correction
* `perf`: Latency optimization (e.g. sub-50ms search) or memory footprint reduction
* `docs`: Documentation, architecture diagrams, or README updates
* `refactor`: Code cleanup without functional or structural changes
* `test`: Adding synthetic tile tests or API test suites

### Pushing and Opening a PR
```powershell
# Push your branch to the remote repository
git push -u origin feature/<your-initials>-<task-name>
```
1. Go to [https://github.com/aaryanmax/ideax](https://github.com/aaryanmax/ideax) and create a **Pull Request**.
2. Target the **`dev`** branch (DO NOT target `main`).
3. Tag **Lead A** for review and merge verification.

---

## 4. Large Asset & GIS Data Policy (Zero-Corruption Rule)

Satellite GeoTIFFs, neural foundation weights, and FAISS indices are heavy binary files that can break repository limits. **Never track large binaries directly in Git.**

### 🚫 Strictly Prohibited from Commits:
* `*.tif`, `*.tiff`, `*.geotiff`, `*.jp2` *(Raw satellite imagery & multi-spectral bands)*
* `*.pt`, `*.pth`, `*.bin`, `*.safetensors`, `*.onnx` *(Model checkpoint weights)*
* `*.index`, `*.faiss` *(Vector database binary indices)*
* `node_modules/`, `venv/`, `.env`, `*.log` *(Dependencies, environments, and secrets)*

> [!WARNING]
> Do NOT use Git LFS on the standard GitHub tier without prior coordination, as bandwidth quotas will easily lock the repository during hackathon evaluation.

### Standard Storage & Ingestion Pipeline:
1. **Kaggle Execution**: Member **K** executes the tiling & embedding pipeline on Kaggle (T4 GPU).
2. **Index & Metadata Export**: The produced lightweight `.faiss` index (~50MB) and downsampled reference tiles are exported to the designated team drive.
3. **Local Deployment**: Member **Y** and Lead **A** place these files locally in `data/indices/` and `data/processed/`.
4. **Git Safeguard**: All asset directories are pre-configured in `.gitignore` to prevent accidental commits.

---

## 5. Emergency Troubleshooting Commands (Windows)

### Fix "Virtual environment activation script is blocked"
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\venv\Scripts\Activate.ps1
```

### Undo a Commit Done by Mistake (Keeps your work uncommitted)
```powershell
git reset --soft HEAD~1
```

### Discard All Local Unstaged Edits (Restores working tree to last commit)
```powershell
git restore .
```

### Abort a Stuck or Broken Git Merge
```powershell
git merge --abort
```

### Sync Feature Branch with Latest Updates from `dev`
Keep your branch up-to-date with merged work from the team:
```powershell
git checkout dev
git pull origin dev
git checkout feature/<your-initials>-<task-name>
git merge dev
```

---

## 💡 Evaluation & Technical Strategy Reference

For deeper insights into how evaluators assess technical depth, edge constraints, and operational feasibility across SIH hackathon tracks:
* 📺 **[SIH 2026 Problem Statement Strategy Guide](https://www.youtube.com/watch?v=dlPHrD0p_uE)**  
  *Breaks down evaluator criteria for defence/geospatial problem statements: air-gap feasibility, latency under edge compute, false-alarm mitigation metrics, and demonstrable operational auditability.*
