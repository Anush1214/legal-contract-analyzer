from typing import List, Dict, Any, Optional
from collections import defaultdict
from backend.config import RRF_K, HYBRID_DENSE_WEIGHT, HYBRID_BM25_WEIGHT
from backend.retrieval.base import RetrievalResult

def reciprocal_rank_fusion(
    ranked_lists: List[List[RetrievalResult]],
    k: int = RRF_K,
    top_k: int = 10
) -> List[RetrievalResult]:
    """
    Reciprocal Rank Fusion (RRF):
    RRF_score(d) = sum_{list L} [ 1 / (k + rank_L(d)) ]

    Why RRF over raw score addition:
    Dense cosine similarity and BM25 term frequencies live on different distributions.
    Adding uncalibrated scores introduces scale bias where BM25 blows up on repetitive words
    or dense retrieval saturates. RRF relies strictly on ordinal ranking, guaranteeing robust,
    scale-invariant candidate fusion.
    """
    rrf_scores: Dict[str, float] = defaultdict(float)
    doc_map: Dict[str, RetrievalResult] = {}
    methods_present: Dict[str, set] = defaultdict(set)

    for r_list in ranked_lists:
        for rank_idx, item in enumerate(r_list):
            doc_id = item.clause_id
            doc_map[doc_id] = item
            methods_present[doc_id].add(item.retrieval_method)
            # 1-indexed rank
            rank = rank_idx + 1
            rrf_scores[doc_id] += 1.0 / (k + rank)

    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results: List[RetrievalResult] = []
    for doc_id, score in sorted_docs[:top_k]:
        base_item = doc_map[doc_id]
        methods_str = "+".join(sorted(list(methods_present[doc_id])))
        results.append(
            RetrievalResult(
                contract_name=base_item.contract_name,
                clause_id=base_item.clause_id,
                clause_number=base_item.clause_number,
                title=base_item.title,
                category=base_item.category,
                text=base_item.text,
                page=base_item.page,
                retrieval_score=score,
                retrieval_method=f"hybrid_rrf({methods_str})",
                metadata={
                    **base_item.metadata,
                    "rrf_score": score,
                    "contributing_retrievers": list(methods_present[doc_id])
                }
            )
        )

    return results

def weighted_score_fusion(
    dense_results: List[RetrievalResult],
    bm25_results: List[RetrievalResult],
    dense_weight: float = HYBRID_DENSE_WEIGHT,
    bm25_weight: float = HYBRID_BM25_WEIGHT,
    top_k: int = 10
) -> List[RetrievalResult]:
    """
    Weighted combination of normalized dense and BM25 scores:
    Combined_score(d) = (w_dense * S_dense + w_bm25 * S_bm25) / (w_dense + w_bm25)
    Useful for ablation experiments comparing score fusion against rank fusion.
    """
    scores: Dict[str, float] = defaultdict(float)
    doc_map: Dict[str, RetrievalResult] = {}
    contributing: Dict[str, List[str]] = defaultdict(list)

    total_weight = dense_weight + bm25_weight or 1.0

    for item in dense_results:
        doc_id = item.clause_id
        doc_map[doc_id] = item
        scores[doc_id] += (item.retrieval_score * dense_weight) / total_weight
        contributing[doc_id].append("dense")

    for item in bm25_results:
        doc_id = item.clause_id
        if doc_id not in doc_map:
            doc_map[doc_id] = item
        scores[doc_id] += (item.retrieval_score * bm25_weight) / total_weight
        contributing[doc_id].append("bm25")

    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results: List[RetrievalResult] = []
    for doc_id, score in sorted_docs[:top_k]:
        base_item = doc_map[doc_id]
        results.append(
            RetrievalResult(
                contract_name=base_item.contract_name,
                clause_id=base_item.clause_id,
                clause_number=base_item.clause_number,
                title=base_item.title,
                category=base_item.category,
                text=base_item.text,
                page=base_item.page,
                retrieval_score=score,
                retrieval_method="hybrid_weighted",
                metadata={
                    **base_item.metadata,
                    "weighted_score": score,
                    "contributing_retrievers": contributing[doc_id]
                }
            )
        )
    return results
