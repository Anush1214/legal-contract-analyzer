import math
import pytest
from evaluation.metrics import recall_at_k, precision_at_k, reciprocal_rank, ndcg_at_k

def test_recall_at_k():
    gt = ["c1", "c2"]
    # Top 2 has 1 hit
    assert recall_at_k(["c1", "c3"], gt, k=2) == 0.5
    # Top 2 has 2 hits
    assert recall_at_k(["c1", "c2", "c3"], gt, k=2) == 1.0
    # Top 1 has 1 hit
    assert recall_at_k(["c1", "c2"], gt, k=1) == 0.5
    # No hits
    assert recall_at_k(["c3", "c4"], gt, k=2) == 0.0

def test_precision_at_k():
    gt = ["c1"]
    assert precision_at_k(["c1", "c2", "c3", "c4"], gt, k=4) == 0.25
    assert precision_at_k(["c1"], gt, k=1) == 1.0
    assert precision_at_k(["c2"], gt, k=1) == 0.0

def test_reciprocal_rank():
    gt = ["c2"]
    assert reciprocal_rank(["c2", "c1"], gt) == 1.0
    assert reciprocal_rank(["c1", "c2"], gt) == 0.5
    assert reciprocal_rank(["c3", "c1", "c2"], gt) == 1.0 / 3.0
    assert reciprocal_rank(["c3", "c4"], gt) == 0.0

def test_ndcg_at_k():
    gt = ["c1"]
    # Perfect rank 1
    assert abs(ndcg_at_k(["c1", "c2", "c3", "c4"], gt, k=4) - 1.0) < 1e-5
    # Rank 2: DCG = 1 / log2(3) ≈ 0.6309
    assert ndcg_at_k(["c2", "c1", "c3"], gt, k=3) < 1.0
    assert ndcg_at_k(["c2", "c1", "c3"], gt, k=3) > 0.6
    # No hits
    assert ndcg_at_k(["c2", "c3"], gt, k=2) == 0.0
