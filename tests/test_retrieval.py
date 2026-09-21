import pytest
from backend.retrieval.base import RetrievalResult
from backend.retrieval.bm25 import BM25Retriever, tokenize_legal_text
from backend.retrieval.fusion import reciprocal_rank_fusion, weighted_score_fusion
from backend.retrieval.reranker import CrossEncoderReranker

def test_tokenize_legal_text():
    tokens = tokenize_legal_text("Section §27 void non-compete with $50 cap and 100% damages")
    assert "section_27" in tokens
    assert "usd_50" in tokens
    assert "100_percent" in tokens
    assert "non-compete" in tokens
    # Stopword 'with' should be removed
    assert "with" not in tokens

def test_bm25_retriever_indexing_and_search():
    retriever = BM25Retriever()
    clauses = [
        {"clause_number": 1, "title": "Scope", "text": "Vendor agrees to provide SaaS software platform services."},
        {"clause_number": 2, "title": "Termination", "text": "Customer shall pay 100% liquidated damages upon early termination."},
        {"clause_number": 3, "title": "Liability", "text": "Vendor liability shall not exceed fifty dollars $50."}
    ]
    retriever.index_clauses("TestContract.pdf", clauses)

    # Search for liquidated damages
    results = retriever.retrieve("liquidated damages early termination", "TestContract.pdf", top_k=2)
    assert len(results) > 0
    assert results[0].clause_number == 2
    assert results[0].retrieval_method == "bm25"
    assert results[0].retrieval_score > 0.0

def test_reciprocal_rank_fusion():
    r1 = [
        RetrievalResult("DocA", "c1", 1, "T1", "Cat1", "text 1", 1, 0.9, "dense"),
        RetrievalResult("DocA", "c2", 2, "T2", "Cat2", "text 2", 1, 0.8, "dense")
    ]
    r2 = [
        RetrievalResult("DocA", "c2", 2, "T2", "Cat2", "text 2", 1, 0.95, "bm25"),
        RetrievalResult("DocA", "c3", 3, "T3", "Cat3", "text 3", 1, 0.70, "bm25")
    ]

    fused = reciprocal_rank_fusion([r1, r2], k=60, top_k=3)
    assert len(fused) == 3
    # c2 is rank 2 in r1 and rank 1 in r2; it should receive the highest fused RRF score
    assert fused[0].clause_id == "c2"
    assert "rrf_score" in fused[0].metadata

def test_weighted_score_fusion():
    r1 = [RetrievalResult("DocA", "c1", 1, "T1", "Cat1", "text 1", 1, 0.8, "dense")]
    r2 = [RetrievalResult("DocA", "c1", 1, "T1", "Cat1", "text 1", 1, 0.6, "bm25")]

    fused = weighted_score_fusion(r1, r2, dense_weight=0.5, bm25_weight=0.5, top_k=1)
    assert len(fused) == 1
    assert abs(fused[0].retrieval_score - 0.7) < 0.01

def test_reranker_fallback_on_empty():
    reranker = CrossEncoderReranker()
    results = reranker.rerank("test query", [])
    assert results == []
