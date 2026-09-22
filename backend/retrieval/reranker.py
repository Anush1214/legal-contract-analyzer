import logging
from typing import List, Optional, Dict, Any
from backend.config import RERANKER_MODEL, RERANKER_DEVICE
from backend.retrieval.base import RetrievalResult

logger = logging.getLogger("retrieval.reranker")
_MODEL_CACHE: Dict[str, Any] = {}

class CrossEncoderReranker:
    """
    Second-stage Cross-Encoder reranker.
    Jointly evaluates (query, candidate_clause) to produce a precise cross-attention relevance score.
    Preserves both retrieval_score and rerank_score to enable research inspection and error analysis.
    """

    def __init__(self, model_name: str = RERANKER_MODEL, device: str = RERANKER_DEVICE):
        self.model_name = model_name
        self.device = device
        self._load_failed = False

    def _get_model(self):
        cache_key = f"{self.model_name}::{self.device}"
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

        if not self._load_failed:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading Cross-Encoder model '{self.model_name}' on device '{self.device}'...")
                try:
                    # Attempt instant load from local HuggingFace cache (0.2s, no network call)
                    model = CrossEncoder(self.model_name, device=self.device, local_files_only=True)
                except Exception:
                    # Fallback to remote download if not cached
                    model = CrossEncoder(self.model_name, device=self.device, local_files_only=False)
                _MODEL_CACHE[cache_key] = model
                logger.info("Cross-Encoder loaded and cached successfully.")
                return model
            except Exception as e:
                logger.warning(f"Could not load Cross-Encoder '{self.model_name}': {e}. Reranking will fallback to retrieval order.")
                self._load_failed = True
        return None

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Rerank candidate clauses using Cross-Encoder joint scoring.
        Returns candidates sorted by rerank_score descending.
        """
        if not candidates:
            return []

        model = self._get_model()
        if model is None:
            # Graceful fallback: return candidates in existing order
            return candidates[:top_k] if top_k else candidates

        try:
            # Pair query with each candidate text
            pairs = [[query, c.text] for c in candidates]
            scores = model.predict(pairs)

            # Assign rerank_score
            for c, score in zip(candidates, scores):
                c.rerank_score = float(score)
                c.metadata["reranker_model"] = self.model_name

            # Sort by rerank_score descending
            reranked = sorted(candidates, key=lambda x: (x.rerank_score if x.rerank_score is not None else -999.0), reverse=True)
            return reranked[:top_k] if top_k else reranked
        except Exception as e:
            logger.error(f"Cross-Encoder inference error: {e}. Falling back to retrieval rank.")
            return candidates[:top_k] if top_k else candidates
