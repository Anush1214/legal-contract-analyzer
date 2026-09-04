import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_db")
UPLOAD_DIR = BASE_DIR / "uploads"
SAMPLE_DIR = BASE_DIR / "sample_data"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.7-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

def get_gemini_api_key() -> str:
    return GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

def set_gemini_api_key(key: str) -> None:
    global GEMINI_API_KEY
    GEMINI_API_KEY = key.strip()
    os.environ["GEMINI_API_KEY"] = key.strip()
