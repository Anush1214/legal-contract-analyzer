# Empirical Information Retrieval Evaluation & Benchmark Report

This document reports the empirical evaluation results comparing the three retrieval architectures and their component ablations on the curated synthetic legal benchmark.

---

## 1. Benchmark Dataset Design

The evaluation dataset (`evaluation/datasets/queries.json`) contains 12 expert-modeled queries labeled across 6 core legal domains:
- **Termination & Liquidated Damages** (early exit penalties, acceleration clauses, cure periods)
- **Non-Compete & Restrictive Covenants** (post-termination non-competes, non-solicitation, geographic scope)
- **Limitation of Liability** (aggregate liability caps, consequential damage exclusions)
- **Intellectual Property** (work product ownership, machine learning data ingestion rights)
- **Evergreen Renewals** (notice windows, automatic term extension)
- **Indemnification** (unilateral vs. reciprocal indemnification, IP infringement defense)

Each query has explicit ground-truth clause IDs mapped to `Enterprise_SaaS_Vendor_Agreement.pdf` and `Standard_Consulting_Services_Agreement.pdf`.

---

## 2. Empirical Benchmark Results

The following table reflects actual experimental execution on identical queries using `scripts/run_evaluation.py`:

| System Architecture | Recall@4 | Recall@8 | Precision@4 | MRR | nDCG@4 | Avg Latency (ms) | Avg Tool Calls |
|---|---|---|---|---|---|---|---|
| **V1_Dense** (Dense RAG Baseline) | **1.0000** | **1.0000** | 0.2500 | **1.0000** | **1.0000** | 1,331.8 ms | 0.0 |
| **V2A_BM25** (Lexical Alone) | **1.0000** | **1.0000** | 0.2500 | 0.8750 | 0.9077 | **0.2 ms** | 0.0 |
| **V2B_Hybrid_NoRerank** (Dense + BM25 RRF) | **1.0000** | **1.0000** | 0.2500 | **1.0000** | **1.0000** | 1,203.0 ms | 0.0 |
| **V2C_Hybrid_Reranked** (Hybrid + Cross-Encoder) | **1.0000** | **1.0000** | 0.2500 | **1.0000** | **1.0000** | 2,834.3 ms | 0.0 |
| **V3_Controlled_Agent** (Multi-Step Agentic) | **1.0000** | **1.0000** | 0.2500 | **1.0000** | **1.0000** | 27,177.0 ms | **2.8** |

---

## 3. In-Depth Component Analysis & Findings

### 3.1 BM25 Lexical Retrieval (`V2A_BM25`)
- **Latency Advantage**: BM25 inverted index queries execute in **0.2 milliseconds**, orders of magnitude faster than dense vector embedding calls (~1,300 ms).
- **Ranking Discrepancy**: While BM25 achieved 1.0000 Recall@4 (all ground-truth clauses were within the top 4), its **MRR dropped to 0.8750** and **nDCG@4 to 0.9077**.
- **Error Analysis Root Cause**:
  - In Query `q002` (*"Are there any post-termination non-compete restrictions, and what is their duration and geographic scope?"*), Clause 1 scored higher than Clause 9 in BM25 because Clause 1 repeated general commercial words (*"services"*, *"agreement"*), ranking the true non-compete clause at rank 2 ($MRR = 0.50$).
  - Similar ranking calibration errors occurred on Query `q009` and Query `q012`.

### 3.2 Cross-Encoder Reranking (`V2C_Hybrid_Reranked`)
- **Resolution of Ranking Errors**: When fused with Dense candidates and passed to the Cross-Encoder (`ms-marco-MiniLM-L-6-v2`), the joint attention mechanism correctly elevated Clause 9, Clause 7, and Clause 6 to Rank 1 ($MRR = 1.0000$, $nDCG@4 = 1.0000$).
- **Latency Tradeoff**: Cross-attention over candidate pairs added ~1,500 ms of latency (total latency: 2,834.3 ms vs 1,203.0 ms for unfused hybrid).

### 3.3 Controlled Agentic RAG (`V3_Controlled_Agent`)
- **Multi-Source Synergy**: On complex queries requiring statutory enforceability, the agent averaged **2.8 tool calls per query** (`search_contract` $\rightarrow$ `get_clause` $\rightarrow$ `search_statutes` $\rightarrow$ `search_cases`).
- **Cost of Agency**: Average latency increased to **27,177 ms** (~27 seconds) due to sequential round-trips to Gemini and CourtListener.
- **Rate Limit Resilience**: When Gemini free-tier daily quotas were reached, the system gracefully transitioned into analytical offline agent mode without throwing unhandled exceptions.
