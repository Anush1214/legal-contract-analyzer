# Current Architecture Audit & Technical Assessment

## 1. Executive Summary

This document presents an exhaustive code audit of the existing **Legal Contract Analyzer** repository (`https://github.com/Anush1214/legal-contract-analyzer.git`). The objective is to establish ground truth regarding the system's current architecture, request flows, file responsibilities, known bugs, dependencies, security vulnerabilities, and structural limitations prior to implementing the three progressively sophisticated retrieval architectures:
- **Version 1 (V1)**: Fixed Dense RAG Baseline
- **Version 2 (V2)**: Hybrid Retrieval (BM25 + Dense) + Cross-Encoder Reranking
- **Version 3 (V3)**: Controlled Agentic RAG with Citation Verification

---

## 2. Current Architecture Overview

The system is currently structured as a monolithic single-tier FastAPI backend coupled with a static HTML/CSS/JavaScript client served directly via FastAPI `StaticFiles`.

```
┌──────────────────────────────────────────────────────────┐
│                   Frontend (Vanilla JS)                  │
│   (app.js, index.html, styles.css - ChatGPT dark theme)   │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTP REST (JSON)
                             ▼
┌──────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
│                      (backend/main.py)                   │
└──────┬─────────────────────┼──────────────────────┬──────┘
       │                     │                      │
       ▼                     ▼                      ▼
┌──────────────┐      ┌──────────────┐       ┌──────────────┐
│ ClauseParser │      │ VectorStore  │       │ LegalEngine  │
│(pdfplumber + │      │  (ChromaDB   │       │(Gemini REST  │
│ regex split) │      │  Persistent) │       │  + Fallback) │
└──────────────┘      └──────────────┘       └──────┬───────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │ LegalSources │
                                             │ (Hardcoded + │
                                             │CourtListener)│
                                             └──────────────┘
```

### Core Ingestion & Storage
- **PDF Extraction**: `pdfplumber` extracts raw text and approximates page boundaries.
- **Clause Segmentation**: Regex pattern `(?=(?:\d+\.\d*|Section\s+\d+|Article\s+\d+|CLAUSE\s+\d+)[\s\.])` splits text into clauses. Clauses < 80 characters are discarded.
- **Clause Categorization**: Deterministic substring search matches text against 10 fixed legal categories (e.g., "Termination & Term", "Limitation of Liability").
- **Vector Storage**: ChromaDB persistent client (`chroma_db/`) creates or connects to collection `"contracts"` with cosine distance space (`"hnsw:space": "cosine"`).

### Inference & Legal Knowledge
- **LLM Synthesis**: Direct HTTP `requests.post` to Google Generative Language REST endpoint (`https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent`) with temperature 0.2.
- **Legal Precedents**:
  - Hardcoded Python lists for Indian Contract Act 1872 (§27, §73-74, §28, §124-125) and DPDP Act 2023.
  - Live REST API queries to `courtlistener.com` (fallback to hardcoded US doctrine).
  - Hardcoded SEC EDGAR commercial benchmarks dictionary.
  - Hardcoded UK UCTA 1977 and *Cavendish* doctrine dictionary.
  - `check_opensanctions` utility (present in `legal_sources.py` but unused anywhere in the application).

---

## 3. Current Request Flows

### 3.1. Contract Upload Flow (`POST /api/contracts/upload`)
1. Receives `UploadFile` (validates only that filename ends with `.pdf`).
2. Reads entire file asynchronously into `pdf_bytes`.
3. Calls `index_contract(pdf_bytes, file.filename)`:
   - `extract_clauses()` parses PDF via `pdfplumber`, applies regex splitting, classifies categories, and maps approximate page numbers.
   - Deletes any pre-existing clauses with metadata `{"contract": contract_name}` from ChromaDB.
   - Calls `get_batch_embeddings(texts)`.
   - Adds documents, embeddings, IDs (`{contract_name}_clause_{i}`), and metadata to ChromaDB collection.
4. Returns JSON `{ message, contract, total_clauses }`.

### 3.2. RAG Contract Analysis Flow (`POST /api/analyze`)
1. Client posts `{ question: str, contract_name: Optional[str] }`.
2. `query_clauses(question, contract_name, n_results=4)`:
   - Calls `get_embedding(question)`.
   - Executes `contract_collection.query(...)` with `where={"contract": contract_name}`.
3. If no documents returned, returns immediate empty fallback response.
4. Formats retrieved clauses into raw text block.
5. Calls `aggregate_legal_research(question, top_clause_text)` which runs substring keyword matching against hardcoded Indian/UK/SEC dictionaries and optionally calls CourtListener API.
6. Assembles combined prompt with contract clauses and external research.
7. Calls `_call_gemini_llm(prompt)` via synchronous `requests.post`.
8. If LLM call fails or returns empty, executes heuristic string template synthesis.
9. Returns `{ answer, clauses_referenced, legal_precedents }`.

### 3.3. Contract Risk Scan Flow (`POST /api/scan-risks`)
1. Client posts `{ contract_name: str }`.
2. Fetches all clauses for the contract from ChromaDB via `get_contract_clauses()`.
3. Builds digest of all clauses into a single prompt asking Gemini for JSON output (`risk_score`, `overall_status`, `summary`, `flagged_clauses`).
4. Attempts to strip markdown code blocks and parse JSON.
5. **Fallback**: If LLM fails or JSON is invalid, applies rule-based keyword scan (`"sole discretion"`, `"unilateral"`, `"without cause"`, `"100%"`, `"liquidated damages"`, `"non-compete"`, `"$50"`, etc.) and calculates score `min(100, (high_count * 25) + (med_count * 10))`.
6. Returns risk breakdown to frontend.

### 3.4. Contract Comparison Flow (`POST /api/compare`)
1. Client posts `{ contract_a: str, contract_b: str, topic: Optional[str] }`.
2. Loads all clauses for both contracts from ChromaDB.
3. Iterates over 5 fixed category names (`Termination & Term`, `Limitation of Liability`, `Indemnification`, `Non-Compete & Restrictive`, `Fees & Payment`).
4. Finds the **first** clause in contract A and contract B matching the exact category string.
5. Assembles comparison prompt for Gemini.
6. Returns JSON with executive comparison and pairwise clause text.

### 3.5. Single Clause Explanation Flow (`POST /api/contracts/explain-clause`)
1. Client posts `{ contract_name: str, clause_number: int, clause_text: str }`.
2. Aggregates legal research for the first 120 characters of the clause.
3. Prompts Gemini for plain-English explanation.
4. Returns explanation, severity rating, and statutory flags.

### 3.6. Configuration & Samples (`GET/POST /api/config`, `POST /api/load-samples`)
1. `/api/config`: Reads masked Gemini API key and active model strings. Allows updating the in-memory/environment key via POST.
2. `/api/load-samples`: Generates two sample PDFs (`Enterprise_SaaS_Vendor_Agreement.pdf` and `Standard_Consulting_Services_Agreement.pdf`) using ReportLab if missing, then indexes both into ChromaDB.

---

## 4. Current File Responsibilities

| File Path | Lines | Primary Responsibility |
|---|---|---|
| `backend/config.py` | 28 | Base directories (`uploads`, `sample_data`, `chroma_db`), environment variables (`GEMINI_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`), and getter/setter helpers. |
| `backend/clause_parser.py` | 95 | PDF ingestion via `pdfplumber`, regex clause splitting, title extraction, and heuristic keyword category detection. |
| `backend/vector_store.py` | 173 | ChromaDB client initialization, embedding generation wrapper, SHA-256 fallback embedding, contract indexing, querying, and deletion. |
| `backend/legal_sources.py` | 210 | Statutory reference database (Indian Law, UK Law, SEC EDGAR benchmarks), CourtListener search, OpenSanctions stub. |
| `backend/legal_engine.py` | 340 | Gemini REST inference wrapper, prompt assembly, heuristic fallback logic for Q&A, full-contract risk scanner, clause explainer, and comparison engine. |
| `backend/sample_contracts.py` | 135 | ReportLab programmatic generation of two multi-clause commercial agreements (Enterprise SaaS & Consulting Services). |
| `backend/main.py` | 151 | FastAPI application configuration, CORS middleware, Pydantic models, REST route definitions, and frontend static file serving. |
| `frontend/index.html` | 422 | Single-page UI with sidebar, model dropdown, active contract pill, Chat view, Clause Explorer view, Risk Scanner view, Compare view, and modals. |
| `frontend/app.js` | 771 | Client-side state management, DOM event listeners, API fetch handlers, chat streaming placeholder, and basic markdown formatting. |
| `frontend/styles.css` | ~600 | Dark theme stylesheet inspired by ChatGPT with CSS variables, flex/grid layouts, badges, cards, and modal styling. |

---

## 5. Critical Issues, Bugs & Architectural Limitations Identified

### 5.1. Critical Bug: Silent Fallback to SHA-256 Hash Vectorizer
- **Symptom**: In `backend/vector_store.py`:
  ```python
  from google import genai
  client = genai.Client(api_key=api_key)
  result = client.models.embed_content(
      model=EMBEDDING_MODEL, # configured as "text-embedding-004"
      contents=text[:4000]
  )
  ```
- **Finding**: Running this call against the Google GenAI API returns `ClientError: 404 NOT_FOUND: models/text-embedding-004 is not found for API version v1beta, or is not supported for embedContent`.
- **Consequence**: The `except Exception:` block caught this 404 error silently on every single indexing and query request! The entire application has been running exclusively on the deterministic SHA-256 word-hash fallback vectorizer (`_generate_fallback_embedding`), which produces pseudo-lexical hash projections rather than real pretrained semantic embeddings. The user was never notified that degraded retrieval mode was active.
- **Fix Required**: Update to currently supported embedding model (`gemini-embedding-001` with `output_dimensionality=1536`), make dimension configurable, remove silent `except Exception: pass`, log degraded fallback mode explicitly, and expose retrieval mode in system diagnostics.

### 5.2. LLM Model Selection & API Inconsistency
- In `backend/config.py` and `backend/legal_engine.py`, `LLM_MODEL` is set to `gemini-3.7-flash` and invoked via raw HTTP `requests.post` to `https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent`.
- Meanwhile, `vector_store.py` imports `from google import genai`.
- Direct API probing during audit revealed:
  - `gemini-2.5-flash` returns `ClientError: 404 NOT_FOUND` ("This model is no longer available to new users. Please update your code to use models/gemini-3.6-flash...").
  - `gemini-3.6-flash` is fully operational and supports structured tool calls.
- **Fix Required**: Standardize on the official `google-genai` SDK across all modules rather than mixing raw `requests.post` and SDK calls; set default to `gemini-3.6-flash` (or current supported model) with graceful fallback.

### 5.3. ChromaDB Cosine Distance vs. Similarity Confusion
- ChromaDB returns `distances` where distance $d \in [0, 2]$ for cosine distance ($d = 1 - \cos(\theta)$).
- In `backend/vector_store.py` and `legal_engine.py`, distances are not inspected, normalized, or returned to the caller.
- There is no minimum similarity threshold: even completely irrelevant clauses (e.g. cosine distance > 0.8) are stuffed into the prompt, forcing the LLM to hallucinate relevance or answer from out-of-context text.

### 5.4. Hardcoded & Fragile Contract Comparison
- In `backend/legal_engine.py:compare_contracts`, the matching logic is:
  ```python
  match_a = next((c for c in clauses_a if c["category"] == cat), None)
  match_b = next((c for c in clauses_b if c["category"] == cat), None)
  ```
- If a contract has 3 termination clauses or an unclassified liability clause, only the first exact category match is compared. If category strings differ slightly, the clause is completely ignored. There is zero semantic alignment.

### 5.5. Unsubstantiated & Fabricated Benchmark Claims in README
- The existing `README.md` contains claims such as:
  - *"Clause Boundary Detection Precision: 98.4% (Evaluated on 150 standard commercial contracts)"*
  - *"Red-Flag Recall: 96.2%"*
  - *"Statutory Cross-Referencing Accuracy: 94.8%"*
  - *"JSON Schema Conformance Rate: 99.7% across 500+ requests"*
- None of these 150 contracts or 500 benchmark runs exist in the repository. The evaluation data, ground truth labels, and scoring scripts are completely absent.
- In accordance with the project's primary objective and research ethics, these claims must be replaced with a real, verifiable, reproducible benchmark framework, with unevaluated metrics marked as N/A until executed.

### 5.6. Security Vulnerabilities
1. **Wildcard CORS**: `allow_origins=["*"]` with `allow_credentials=True` in `backend/main.py` is insecure and contradicts standard CORS policies.
2. **File Upload Validation**: Only checks `.pdf` extension suffix (`if not file.filename.lower().endswith(".pdf")`). Malicious files with `.pdf` extension or corrupted payloads are not checked for PDF magic header (`%PDF-`).
3. **No File Size Enforcement**: Files are read into RAM without size caps (`await file.read()`), exposing the server to memory exhaustion DoS.
4. **Path Traversal**: Uploaded filenames are used directly without sanitization (`Path(filename).name`).
5. **Prompt Injection Risk**: Raw contract text and untrusted user queries are concatenated into system prompts without role boundaries or sanitization.
6. **API Key State Modification**: `POST /api/config` updates the server-wide environment variable without any authorization check.

### 5.7. Performance & Concurrency Bottlenecks
- `analyze_contract`, `flag_risky_clauses`, and `compare_contracts` perform blocking network requests (`requests.post`) inside FastAPI route handlers. Under concurrent traffic, worker threads are starved.
- ChromaDB client is initialized as a module-level global singleton without connection pooling or lock safeguards.

### 5.8. Stale and Missing Dependencies
- `requirements.txt` includes `openai>=1.30.0` and `tiktoken>=0.7.0`, neither of which is imported or used anywhere in the codebase.
- Critical dependencies required for research architectures are missing:
  - `rank_bm25` (for BM25 lexical retrieval)
  - `sentence-transformers` (for Cross-Encoder reranking)
  - `pytest` (for automated test suites)

---

## 6. Required Architectural Transformations

To achieve the research objectives, the codebase will be refactored into three interchangeable retrieval paradigms sharing a unified evaluation protocol:

```
                      ┌──────────────────────────────┐
                      │   POST /api/analyze (Router) │
                      └──────────────┬───────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
   │   VERSION 1   │         │   VERSION 2   │         │   VERSION 3   │
   │Fixed Dense RAG│         │  Hybrid +     │         │  Controlled   │
   │   Baseline    │         │  Reranking    │         │  Agentic RAG  │
   └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
           │                         │                         │
     ChromaDB HNSW             BM25 + Dense               Gemini Tools
     Cosine Similarity       Candidate Fusion           (search_contract,
     Normalized Score        (Reciprocal Rank)           search_statutes,
     Threshold Abstain               │                   search_cases,
           │                 Cross-Encoder               get_clause,
           │                   Reranker                  compare)
           │                         │                         │
           ▼                         ▼                         ▼
   Evidence Assembly         Evidence Assembly         Stateful Evidence
           │                         │                 Accumulator
           │                         │                         │
           ▼                         ▼                         ▼
   Grounded Prompt           Grounded Prompt           Citation Verifier
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     ▼
                            Grounded Answer /
                          Calibrated Abstention
```

### Transition Roadmap:
1. **Foundation (V0)**:
   - Modernize embedding engine to use valid `gemini-embedding-001` (1536 dim) with explicit fallback detection and logging.
   - Clean up dependencies in `requirements.txt`.
   - Implement `scripts/reindex_contracts.py` to ensure vector consistency.
2. **Modular Retrieval Interfaces**:
   - Create `backend/retrieval/` (`base.py`, `dense.py`, `bm25.py`, `hybrid.py`, `fusion.py`, `reranker.py`) with a standardized `RetrievalResult` dataclass.
3. **Version 1 (V1)**:
   - Establish clean fixed dense retrieval baseline with normalized similarity scores, configurable `RAG_TOP_K`, `RAG_MIN_RELEVANCE_SCORE`, and controlled abstention.
4. **Version 2 (V2)**:
   - Implement legal-aware BM25 tokenizer and persistent BM25 index.
   - Implement Reciprocal Rank Fusion (RRF) combining dense and lexical candidate pools.
   - Implement local Cross-Encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) outputting joint `rerank_score` alongside `retrieval_score`.
5. **Version 3 (V3)**:
   - Implement controlled agentic orchestration in `backend/agent/` using Gemini function calling (`tools.py`, `orchestrator.py`, `state.py`, `verifier.py`).
   - Implement citation verification checking cited clause numbers, source text correspondence, and jurisdiction validity.
6. **Evaluation Framework**:
   - Create synthetic labeled legal benchmark dataset (`evaluation/datasets/queries.json`).
   - Implement automated metrics (Recall@K, Precision@K, MRR, nDCG, latency, token consumption).
   - Provide ablation support (Dense only, BM25 only, Hybrid without reranking, Hybrid + Reranker, Agentic).
   - Build automated evaluation runner (`scripts/run_evaluation.py`) producing reproducible results.
7. **Frontend & Observability**:
   - Add developer/research controls to switch between V1, V2, and V3 in the UI.
   - Display retrieval metadata (method, candidate scores, reranker scores, agent trace, latency).
   - Add research comparison dashboard displaying genuine benchmark metrics without fabricated numbers.
