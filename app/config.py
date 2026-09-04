import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# K's pipeline outputs (step04/step08)
DATA_DIR = PROJECT_ROOT / "data"

FAISS_INDEX_PATH = DATA_DIR / "satellite_tiles.index"
METADATA_PATH = DATA_DIR / "metadata.json"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
PATCHES_DIR = PROJECT_ROOT / "output_patches"

# Model config
EMBEDDING_DIM = 512
TOP_K_DEFAULT = 10

# API config
HOST = "127.0.0.1"
PORT = 8000

# Audit DB
DB_PATH = PROJECT_ROOT / "vayu_audit.db"