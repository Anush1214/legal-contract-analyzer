# RAG Pipeline Specifications (V1, V2, V3)

This document specifies the technical architecture, execution flows, and configuration parameters of the three retrieval-augmented generation pipelines implemented in the system.

---

## 1. Version 1: Fixed Dense RAG Baseline

### 1.1 Architecture
```
User Query
    │
    ▼
Query Embedding (gemini-embedding-001, 1536 dim)
    │
    ▼
ChromaDB Cosine Retrieval (Top-K)
    │
    ▼
Relevance Threshold Check (Similarity >= RAG_MIN_RELEVANCE_SCORE)
    ├── Below Threshold ──> Calibrated Abstention Response
    │
    └── Above Threshold
            │
            ▼
        Evidence Object Normalization
            │
            ▼
        External Legal Context Aggregation (Statutes & Benchmarks)
            │
            ▼
        Grounded Prompt Assembly (XML Boundary Delimiters)
            │
            ▼
        Gemini 3.6 Flash Inference
            │
            ▼
        Grounded Answer + Citations
```

### 1.2 Configuration Parameters
- `RAG_VERSION=v1`
- `RAG_TOP_K=4` (Tested across $k \in \{2, 4, 6, 8\}$)
- `RAG_MIN_RELEVANCE_SCORE=0.40`
- `EMBEDDING_MODEL=gemini-embedding-001`
- `EMBEDDING_DIM=1536`

### 1.3 Threshold & Calibrated Abstention
If no retrieved clause meets `RAG_MIN_RELEVANCE_SCORE` or the vector index is empty, the system abstains:
> *"I could not find sufficiently relevant clauses in 'Contract' to answer this question reliably. System Diagnostic: Top retrieval similarity score (0.284) fell below minimum confidence threshold (0.400)."*

This prevents the LLM from hallucinating answers based on out-of-context boilerplate text.

---

## 2. Version 2: Hybrid Retrieval + Cross-Encoder Reranking

### 2.1 Architecture
```
User Query
    │
    ├─────────────────────────────┬─────────────────────────────┐
    ▼                                                           ▼
Dense Retrieval (ChromaDB)                                  BM25 Lexical Retrieval
(DENSE_CANDIDATES = 10)                                     (BM25_CANDIDATES = 10)
    │                                                           │
    └─────────────────────────────┬─────────────────────────────┘
                                  ▼
                    Reciprocal Rank Fusion (RRF, k=60)
                                  │
                                  ▼
                    Candidate Pool (10 - 20 Clauses)
                                  │
                                  ▼
                    Cross-Encoder Joint Reranker
                 (ms-marco-MiniLM-L-6-v2 on CPU)
                                  │
                                  ▼
                         Final Top-K Clauses
                                  │
                                  ▼
                        Grounded Synthesis
```

### 2.2 Configuration Parameters
- `RAG_VERSION=v2`
- `BM25_CANDIDATES=10`
- `DENSE_CANDIDATES=10`
- `FINAL_TOP_K=4`
- `RRF_K=60`
- `RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2`
- `RERANKER_DEVICE=cpu`

---

## 3. Version 3: Controlled Agentic RAG

### 3.1 Architecture
```
User Query
    │
    ▼
Research Agent (Gemini 3.6 Flash with Function Calling)
    │
    ▼
Whitelisted Tool Invocation Loop (Max Steps = 5)
    ├── search_contract (V2 Hybrid Retrieval)
    ├── get_clause (Verbatim clause content & metadata)
    ├── search_statutes (Indian Contract Act 1872, UK UCTA 1977, US UCC)
    ├── search_cases (CourtListener case law & judicial opinions)
    └── compare_contracts (Side-by-side comparative analysis)
    │
    ▼
Explicit Evidence State Accumulation
    │
    ▼
Evidence Sufficiency Policy Check
    ├── Zero Contract Evidence ──> Agent Abstention
    │
    └── Evidence Present
            │
            ▼
        Synthesis Prompt
            │
            ▼
        Post-Generation Citation & Hallucination Verifier
            │
            ▼
        Verified Response with Audit Trace
```

### 3.2 Configuration Parameters
- `RAG_VERSION=v3`
- `MAX_AGENT_STEPS=5`
- `LLM_MODEL=gemini-3.6-flash`
