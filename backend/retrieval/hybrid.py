import logging
from typing import List, Dict, Any, Optional
from backend.config import (
    BM25_CANDIDATES,
    DENSE_CANDIDATES,
    FINAL_TOP_K,
    RRF_K
)
from backend.retrieval.base import BaseRetriever, RetrievalResult
from backend.retrieval.dense import DenseRetriever
from backend.retrieval.bm25 import BM25Retriever
from backend.retrieval.fusion import reciprocal_rank_fusion
from backend.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger("retrieval.hybrid")

class HybridRetriever(BaseRetriever):
    """
    Version 2 Retrieval Architecture:
    Combines BM25 lexical search and Dense semantic search, fuses candidates via
    Reciprocal Rank Fusion (RRF), and applies Cross-Encoder joint reranking.
    """

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        reranker: Optional[CrossEncoderReranker] = None
    ):
        self.dense = dense_retriever or DenseRetriever()
        self.bm25 = bm25_retriever or BM25Retriever()
        self.reranker = reranker or CrossEncoderReranker()

    def index_clauses(self, contract_name: str, clauses: List[Dict[str, Any]]) -> None:
        """Index clauses into both dense store and BM25 in-memory index."""
        self.dense.index_clauses(contract_name, clauses)
        self.bm25.index_clauses(contract_name, clauses)

    def retrieve(
        self,
        query: str,
        contract_name: Optional[str] = None,
        top_k: int = FINAL_TOP_K,
        use_reranker: bool = True
    ) -> List[RetrievalResult]:
        """
        Execute Hybrid Retrieval pipeline:
        1. Fetch dense candidates (top DENSE_CANDIDATES).
        2. Fetch BM25 candidates (top BM25_CANDIDATES).
        3. Fuse candidate lists using Reciprocal Rank Fusion (RRF).
        4. Apply Cross-Encoder joint scoring if use_reranker is True.
        """
        dense_candidates = self.dense.retrieve(
            query=query,
            contract_name=contract_name,
            top_k=DENSE_CANDIDATES
        )

        bm25_candidates = self.bm25.retrieve(
            query=query,
            contract_name=contract_name,
            top_k=BM25_CANDIDATES
        )

        if not dense_candidates and not bm25_candidates:
            return []

        # If only one source returned results
        if not dense_candidates:
            fused_candidates = bm25_candidates
        elif not bm25_candidates:
            fused_candidates = dense_candidates
        else:
            pool_size = max(DENSE_CANDIDATES, BM25_CANDIDATES, top_k * 2)
            fused_candidates = reciprocal_rank_fusion(
                ranked_lists=[dense_candidates, bm25_candidates],
                k=RRF_K,
                top_k=pool_size
            )

        if use_reranker and fused_candidates:
            return self.reranker.rerank(query=query, candidates=fused_candidates, top_k=top_k)

        return fused_candidates[:top_k]

    def delete_contract(self, contract_name: str) -> bool:
        """Delete contract from both dense and BM25 stores."""
        dense_res = self.dense.delete_contract(contract_name)
        bm25_res = self.bm25.delete_contract(contract_name)
        return dense_res or bm25_res
