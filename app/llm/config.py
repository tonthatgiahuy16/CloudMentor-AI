from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
LLM_MAX_ATTEMPTS = int(
    os.getenv("LLM_MAX_ATTEMPTS", "3")
)
LLM_RETRY_BACKOFF_SECONDS = float(
    os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1")
)

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")
