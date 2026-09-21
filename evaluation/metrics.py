import math
from typing import List, Set, Any

def recall_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
    """
    Calculate Recall@K:
    Proportion of relevant items retrieved in top-k results.
    Recall@K = |Retrieved[:k] ∩ GroundTruth| / |GroundTruth|
    """
    if not ground_truth_ids:
        return 0.0

    k_items = set(retrieved_ids[:k])
    gt_set = set(ground_truth_ids)
    hits = len(k_items.intersection(gt_set))
    return hits / len(gt_set)

def precision_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
    """
    Calculate Precision@K:
    Proportion of top-k retrieved items that are relevant.
    Precision@K = |Retrieved[:k] ∩ GroundTruth| / k
    """
    if k <= 0:
        return 0.0

    k_items = set(retrieved_ids[:k])
    gt_set = set(ground_truth_ids)
    hits = len(k_items.intersection(gt_set))
    return hits / k

def reciprocal_rank(retrieved_ids: List[str], ground_truth_ids: List[str]) -> float:
    """
    Calculate Reciprocal Rank (RR):
    1 / rank of the first relevant item retrieved, or 0.0 if not found.
    """
    gt_set = set(ground_truth_ids)
    for idx, item_id in enumerate(retrieved_ids):
        if item_id in gt_set:
            return 1.0 / (idx + 1)
    return 0.0

def ndcg_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain at K (nDCG@K) for binary relevance.
    DCG@K = sum_{i=1}^k [ rel_i / log2(i + 1) ]
    IDCG@K = sum_{i=1}^{min(k, |GT|)} [ 1 / log2(i + 1) ]
    """
    if not ground_truth_ids or k <= 0:
        return 0.0

    gt_set = set(ground_truth_ids)
    dcg = 0.0
    for i in range(min(k, len(retrieved_ids))):
        rel = 1.0 if retrieved_ids[i] in gt_set else 0.0
        if rel > 0:
            dcg += rel / math.log2(i + 2)

    idcg = 0.0
    ideal_count = min(k, len(gt_set))
    for i in range(ideal_count):
        idcg += 1.0 / math.log2(i + 2)

    return (dcg / idcg) if idcg > 0.0 else 0.0
