from pathlib import Path

# ==========================
# Project
# ==========================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ==========================
# Storage
# ==========================

STORAGE_DIR = BASE_DIR / "storage"

UPLOAD_DIR = STORAGE_DIR / "uploads"

PROCESSED_DIR = STORAGE_DIR / "processed"

TEMP_DIR = STORAGE_DIR / "temp"

# ==========================
# Vector Database
# ==========================

CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "cloudmentor"

# ==========================
# Embedding
# ==========================

EMBEDDING_MODEL = "BAAI/bge-m3"

# ==========================
# Retrieval
# ==========================

TOP_K = 3

SIMILARITY_THRESHOLD = 1.0

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)