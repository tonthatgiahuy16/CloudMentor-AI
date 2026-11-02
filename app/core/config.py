from pathlib import Path
import os
from dotenv import load_dotenv
# ==========================
# Project
# ==========================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# ==========================
# Relational Database
# ==========================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")
# ==========================
# Storage
# ==========================

STORAGE_DIR = BASE_DIR / "storage"

UPLOAD_DIR = Path(
    os.getenv(
        "CLOUDMENTOR_UPLOAD_DIR",
        STORAGE_DIR / "uploads",
    )
)

PROCESSED_DIR = STORAGE_DIR / "processed"

TEMP_DIR = STORAGE_DIR / "temp"

# ==========================
# Vector Database
# ==========================

CHROMA_DIR = Path(
    os.getenv(
        "CHROMA_DIR",
        BASE_DIR / "chroma_db",
    )
)

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

# ==========================
# Public demo controls
# ==========================

DEMO_MODE = (
    os.getenv("DEMO_MODE", "false").strip().lower()
    == "true"
)

CORS_ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
)

CHAT_RATE_LIMIT_PER_MINUTE = int(
    os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "12")
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
