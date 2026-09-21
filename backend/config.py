import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_db")
UPLOAD_DIR = BASE_DIR / "uploads"
SAMPLE_DIR = BASE_DIR / "sample_data"
EVALUATION_DIR = BASE_DIR / "evaluation"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# LLM & Embedding Settings
# -------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))

# -------------------------------------------------------------------------
# RAG Pipeline Configuration (V1 / V2 / V3)
# -------------------------------------------------------------------------
RAG_VERSION = os.getenv("RAG_VERSION", "v1").lower()
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MIN_RELEVANCE_SCORE = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.40"))

# V2 Hybrid Retrieval & Candidate Pool Configuration
BM25_CANDIDATES = int(os.getenv("BM25_CANDIDATES", "10"))
DENSE_CANDIDATES = int(os.getenv("DENSE_CANDIDATES", "10"))
FINAL_TOP_K = int(os.getenv("FINAL_TOP_K", "4"))
RRF_K = int(os.getenv("RRF_K", "60"))
HYBRID_DENSE_WEIGHT = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.5"))
HYBRID_BM25_WEIGHT = float(os.getenv("HYBRID_BM25_WEIGHT", "0.5"))

# V2 Cross-Encoder Reranker Settings
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")

# V3 Controlled Agent Settings
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "5"))

# -------------------------------------------------------------------------
# Helpers for Dynamic Key Configuration
# -------------------------------------------------------------------------
def get_gemini_api_key() -> str:
    return GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

def set_gemini_api_key(key: str) -> None:
    global GEMINI_API_KEY
    GEMINI_API_KEY = key.strip()
    os.environ["GEMINI_API_KEY"] = key.strip()
