import hashlib
import math
import logging
from typing import List, Dict, Any, Optional
from backend.config import get_gemini_api_key, EMBEDDING_MODEL, EMBEDDING_DIM

logger = logging.getLogger("retrieval.embedding")

# Module-level state tracking
_live_api_active: Optional[bool] = None
_last_error_message: Optional[str] = None

def _generate_lexical_hash_fallback(text: str, dim: int = 1536) -> List[float]:
    """
    DEGRADED FALLBACK ONLY:
    Deterministic SHA-256 hash projection across dimension bins.
    NOTICE: This is NOT a semantic embedding and does NOT capture contextual semantics.
    It is provided purely to prevent hard crashes during offline testing or when API keys are absent.
    """
    vec = [0.0] * dim
    words = text.lower().split()
    for i, word in enumerate(words):
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        weight = 1.0 / (1.0 + math.log(i + 1))
        vec[idx] += weight
        vec[(idx + 31) % dim] += 0.5 * weight

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]

def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector using Google GenAI API with configurable dimension.
    Falls back to deterministic hash projection if API is unconfigured or fails,
    with explicit logging so degraded mode is never hidden.
    """
    global _live_api_active, _last_error_message

    api_key = get_gemini_api_key()
    if api_key and not api_key.startswith("demo_"):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            config = types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text[:8000],
                config=config
            )
            if hasattr(result, "embeddings") and result.embeddings:
                values = result.embeddings[0].values
                if _live_api_active is not True:
                    logger.info(f"Google GenAI embedding operational: model={EMBEDDING_MODEL}, dim={len(values)}")
                    _live_api_active = True
                    _last_error_message = None
                return values
        except Exception as e:
            _last_error_message = str(e)
            if _live_api_active is not False:
                logger.warning(
                    f"Google GenAI embedding failed for model='{EMBEDDING_MODEL}'. "
                    f"ACTIVATING DEGRADED LEXICAL/HASH RETRIEVAL MODE. Reason: {e}"
                )
                _live_api_active = False
    else:
        if _live_api_active is not False:
            logger.info("No Gemini API key configured. Active in Degraded Lexical Hash Retrieval Mode.")
            _live_api_active = False

    return _generate_lexical_hash_fallback(text, dim=EMBEDDING_DIM)

def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Batch generate embeddings for multiple texts."""
    return [get_embedding(t) for t in texts]

def get_embedding_status() -> Dict[str, Any]:
    """Expose retrieval mode diagnostics for system transparency."""
    key = get_gemini_api_key()
    return {
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIM,
        "has_api_key": bool(key and len(key) > 8 and not key.startswith("demo_")),
        "is_live_api": bool(_live_api_active),
        "mode": "Live Pretrained Semantic Embedding (Google GenAI)" if _live_api_active else "Degraded Lexical Hash Fallback (Non-Semantic)",
        "last_error": _last_error_message
    }
