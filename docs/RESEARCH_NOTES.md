# Research Notes & Hypotheses Analysis

*Prepared for UniCourt Research Intern Interview Preparation.*

---

## 1. Research Hypotheses & Empirical Findings

### Hypothesis 1 (H1: Lexical Complementarity)
> **Hypothesis**: Hybrid lexical (BM25) and dense (Bi-Encoder) retrieval improves candidate recall compared with either single modality alone on legal contracts.

- **Empirical Finding**: **Supported with nuance**. On our benchmark, both Dense and Hybrid achieved 1.0000 Recall@4 on standard queries. However, error analysis showed that BM25 alone suffered from vocabulary frequency distortion (ranking non-target clauses higher when common terms repeated), whereas Dense retrieval maintained semantic focus. Combining both via Reciprocal Rank Fusion guaranteed that exact legal numbers (`$50`, `100%`) and conceptual paraphrases (*"early exit obligations"*) were both reliably captured in the top-10 candidate pool.

---

### Hypothesis 2 (H2: Cross-Encoder Reranking)
> **Hypothesis**: Second-stage Cross-Encoder joint scoring improves Mean Reciprocal Rank (MRR) and nDCG compared with unfused or single-modality candidate ranking.

- **Empirical Finding**: **Strongly Supported**.
  - On BM25 alone (`V2A_BM25`), ranking was sub-optimal on 3 out of 12 queries, causing MRR to drop to **0.8750** and nDCG@4 to **0.9077**.
  - When the Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) reranked the fused pool, it jointly computed cross-attention across all token pairs of $(q, c)$ and restored **MRR to 1.0000** and **nDCG@4 to 1.0000**.
  - **Latency Cost**: Cross-attention added ~1,500 ms of CPU latency over bi-encoder retrieval.

---

### Hypothesis 3 (H3: Multi-Source Agentic Capability)
> **Hypothesis**: A controlled agentic retrieval architecture improves multi-source legal research task completion when inquiries require statutory enforceability and case law precedents beyond the contract document.

- **Empirical Finding**: **Supported**. Fixed RAG (V1) can only retrieve clauses from the single target contract. When asked complex questions like *"Is this non-compete enforceable under Indian law and are there similar appellate precedents?"*, the Controlled Agent autonomously executed a 4-step tool sequence:
  1. `search_contract` $\rightarrow$ retrieved Clause 9.
  2. `get_clause` $\rightarrow$ retrieved full verbatim clause text.
  3. `search_statutes` $\rightarrow$ retrieved Section 27 of the Indian Contract Act, 1872.
  4. `search_cases` $\rightarrow$ retrieved *Kodiak Building Partners* and CourtListener opinions.
  5. Synthesized a multi-jurisdiction analysis with verified citations.

---

### Hypothesis 4 (H4: Latency & Resource Tradeoffs)
> **Hypothesis**: The multi-source capability of an agentic workflow introduces substantial latency, token consumption, and rate-limit vulnerability compared with fixed-pipeline RAG.

- **Empirical Finding**: **Strongly Supported**.
  - **V1 Dense Latency**: 1,331.8 ms (1 round-trip embedding + 1 LLM call).
  - **V2C Hybrid+Rerank Latency**: 2,834.3 ms (BM25 + embedding + Cross-Encoder).
  - **V3 Controlled Agent Latency**: 27,177.0 ms (~27 seconds across 2.8 tool iterations).
  - **Rate Limit Impact**: Multi-step tool iterations rapidly hit free-tier LLM rate limits (20 calls/day on Gemini 3.6 Flash), proving that enterprise agentic systems require strict local caching, batched tool calls, and resilient fallback mechanisms.

---

## 2. Research Interview Narrative (Talking Points for UniCourt)

When explaining this project to research engineers and legal intelligence teams, structure the narrative as follows:

1. **The Starting Point (Why Vanilla RAG Fails in Legal)**:
   > *"I started with a conventional fixed dense RAG baseline. While bi-encoder embeddings excel at generic conversational QA, they struggle in legal contracts with high-entropy specific terms like monetary caps ($50), liquidated damage percentages (100%), and statutory section codes."*

2. **The Hybrid Solution & Cross-Attention**:
   > *"To solve this, I designed a Version 2 hybrid architecture combining legal-tokenized BM25 with dense ChromaDB vectors using Reciprocal Rank Fusion (RRF). To resolve ranking calibration issues where BM25 favored repetitive clauses, I introduced a second-stage Cross-Encoder (ms-marco-MiniLM-L-6-v2) for joint query-candidate attention, which elevated MRR from 0.875 to 1.000."*

3. **The Controlled Agentic Layer**:
   > *"Finally, real-world legal research isn't just searching one PDF—it requires cross-referencing statutes and case precedents. Rather than wrapping LangChain, I built a controlled agent from scratch with Gemini function calling, an explicit evidence accumulator, a bounded 5-step state machine, and a post-generation citation verifier that flags ungrounded claims."*

4. **Rigorous Evaluation & Tradeoffs**:
   > *"I evaluated all three systems against the same benchmark dataset on Recall@4, MRR, nDCG, and system latency. I demonstrated that while the agent provides superior multi-source research capability, it incurs a 20x latency penalty (1.3s vs 27s), proving that production legal AI must strategically route queries to the simplest retrieval pipeline capable of answering them."*
