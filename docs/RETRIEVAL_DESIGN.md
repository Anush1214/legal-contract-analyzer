# Information Retrieval Architecture & Design Rationale

This document details the retrieval paradigms implemented in the **Legal Contract Analyzer**, explaining the theoretical and empirical justifications for:
1. Dense Semantic Vector Retrieval (Bi-Encoder)
2. BM25 Lexical Term Matching
3. Reciprocal Rank Fusion (RRF)
4. Cross-Encoder Second-Stage Reranking

---

## 1. Dense Semantic Retrieval (Bi-Encoder)

### 1.1 Mathematical Formulation
Dense retrieval maps queries $q$ and contract clauses $c \in \mathcal{C}$ into a shared dense vector space $\mathbb{R}^D$ using a dual-encoder architecture:
$$v_q = \text{Embed}(q), \quad v_c = \text{Embed}(c)$$
where $D = 1536$ utilizing `gemini-embedding-001`.

Relevance is measured using cosine similarity:
$$\text{Sim}(q, c) = \frac{v_q \cdot v_c}{\|v_q\|_2 \|v_c\|_2}$$

In ChromaDB with an HNSW index over cosine space, Chroma returns cosine distance $d \in [0, 2]$:
$$d = 1 - \text{Sim}(q, c)$$
We convert distance to normalized similarity score $S_C \in [0, 1]$:
$$S_C = \max(0.0, 1.0 - d)$$

### 1.2 Strengths & Failure Modes in Legal Contexts
- **Strength (Semantic Abstraction)**: Dense retrieval excels at synonymy and paraphrasing. For example, a query asking about *"vendor liability caps"* successfully retrieves clauses titled *"Limitation of Damages"* even when exact terminology differs.
- **Failure Mode (Term Dilution)**: Bi-encoders project the entire clause into a fixed-dimensional vector. High-entropy specific terms such as monetary figures (`$50`), percentages (`100%`), or statutory citations (`Section 27`) can be smoothed out by generic boilerplate text surrounding them.

---

## 2. BM25 Lexical Retrieval

### 2.1 Mathematical Formulation
BM25 (Best Matching 25) calculates lexical term matching with term-frequency saturation and document-length normalization:
$$\text{BM25}(q, c) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, c) \cdot (k_1 + 1)}{f(t, c) + k_1 \cdot \left(1 - b + b \cdot \frac{|c|}{\text{avgdl}}\right)}$$
where:
- $f(t, c)$ is the frequency of token $t$ in clause $c$.
- $|c|$ is the token length of clause $c$, and $\text{avgdl}$ is the average clause length across the contract.
- $k_1 = 1.5$ (governing term-frequency saturation) and $b = 0.75$ (governing document-length penalization).

### 2.2 Legal-Aware Tokenization Strategy
Standard whitespace or naive regex tokenizers strip statutory marks and numerical suffixes. Our tokenizer (`tokenize_legal_text` in `backend/retrieval/bm25.py`):
1. Preserves statutory symbols: `§27` is preserved as `section_27`.
2. Preserves monetary bounds: `$50` is converted to `usd_50`.
3. Preserves percentages: `100%` is converted to `100_percent`.
4. Preserves compound legal operators: `non-compete`, `non-disclosure`, `hold-harmless`.
5. **Selective Stopword Removal**: Standard NLP libraries strip words like `not`, `without`, `unless`, `except`, and `sole`. In legal contracts, removing these words fundamentally inverts rights and obligations (e.g. *"Customer shall **not** terminate without cause"* becomes *"Customer shall terminate without cause"*). Our tokenizer strictly retains negation and scoping terms.

---

## 3. Candidate Fusion: Reciprocal Rank Fusion (RRF)

### 3.1 Why Not Simple Score Addition?
Dense cosine similarity produces scores in $[0, 1]$. BM25 scores produce uncalibrated positive floats $[0, \infty)$ dependent on query length and term rarity. Direct linear addition:
$$\text{Score}_{\text{raw}} = S_{\text{dense}} + S_{\text{BM25}}$$
creates severe scale imbalance. Long queries or queries with repeated keywords cause BM25 to overwhelm dense semantics, while short conceptual queries cause dense retrieval to dominate.

### 3.2 RRF Formulation
To eliminate distribution dependencies, we employ **Reciprocal Rank Fusion**:
$$\text{RRF\_Score}(c) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{1}{k + \text{rank}_m(c)}$$
where $\text{rank}_m(c)$ is the 1-indexed position of clause $c$ in retriever $m$, and $k$ is a smoothing constant set to $60$.

**Empirical Properties of RRF**:
- Scale-invariant: relies strictly on ordinal ranking.
- Favors consensus: a clause appearing in the top 3 of both retrievers receives an exponentially higher score than a clause appearing at rank 1 in only one retriever.
- Resistant to outliers: a very high raw BM25 score cannot overpower a consensus candidate.

---

## 4. Second-Stage Cross-Encoder Joint Reranking

### 4.1 Bi-Encoder vs. Cross-Encoder

```
Bi-Encoder (Fast Candidate Generation)
Query  ──────> [ Transformer ] ──> Vector (q)  ─┐ Cosine Sim
Clause ──────> [ Transformer ] ──> Vector (c)  ─┘ (Fast HNSW, < 15ms)

Cross-Encoder (Precise Joint Scoring)
[Query + Clause] ───> [ Full Cross-Attention Transformer ] ───> Logit Relevance Score
                      (Joint attention across all token pairs, ~50ms per pair)
```

| Dimension | Bi-Encoder (Dense) | Cross-Encoder (Reranker) |
|---|---|---|
| **Architecture** | Dual independent encoders | Single transformer with full cross-attention |
| **Token Interaction** | Independent embeddings; late dot-product | Query and clause tokens attend to each other at every layer |
| **Computational Complexity**| $\mathcal{O}(|q| + |c|)$ | $\mathcal{O}((|q| + |c|)^2)$ |
| **Indexing Feasibility** | Offline pre-computed vectors in vector store | Cannot pre-compute; must score query-candidate pairs online |
| **Role in Pipeline** | High-recall candidate pool generation ($K=20$) | High-precision reranking to final Top-$K$ ($K=4$) |

### 4.2 Cross-Encoder Model Selection
We use `cross-encoder/ms-marco-MiniLM-L-6-v2`:
- Optimized for passage ranking on CPU with 6-layer MiniLM architecture.
- Jointly scores each candidate clause against the user's legal question.
- Outputs an unbounded logit relevance score stored as `rerank_score`.
- Enables error analysis comparing `retrieval_score` against `rerank_score` to identify bi-encoder ranking failures.
