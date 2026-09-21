import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.config import (
    get_gemini_api_key,
    set_gemini_api_key,
    LLM_MODEL,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    RAG_VERSION,
    RAG_TOP_K,
    RAG_MIN_RELEVANCE_SCORE,
    EVALUATION_DIR
)
from backend.retrieval.embedding_service import get_embedding_status
from backend.vector_store import (
    index_contract,
    list_indexed_contracts,
    get_contract_clauses,
    delete_contract
)
from backend.legal_engine import (
    analyze_contract,
    flag_risky_clauses,
    explain_single_clause,
    compare_contracts
)
from backend.sample_contracts import ensure_sample_contracts

app = FastAPI(
    title="Legal Contract Analyzer API",
    description="Research-Grade Legal Document Intelligence Platform comparing Dense, Hybrid, and Controlled Agentic RAG.",
    version="2.0.0"
)

# CORS Configuration: restrict wildcard origins with credentials
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Maximum file upload size: 25 Megabytes
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# Pydantic Request Models
class AnalyzeRequest(BaseModel):
    question: str
    contract_name: Optional[str] = None
    version: Optional[str] = Field(default=None, description="Retrieval architecture: 'v1' (Dense), 'v2' (Hybrid+Rerank), or 'v3' (Agentic)")
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class ScanRisksRequest(BaseModel):
    contract_name: str

class CompareRequest(BaseModel):
    contract_a: str
    contract_b: str
    topic: Optional[str] = None

class ExplainClauseRequest(BaseModel):
    contract_name: str
    clause_number: int
    clause_text: str

class ConfigUpdateRequest(BaseModel):
    gemini_api_key: str

# API Routes
@app.get("/api/config")
def get_system_config():
    embed_status = get_embedding_status()
    key = get_gemini_api_key()
    has_key = bool(key and len(key) > 8 and not key.startswith("demo_"))
    return {
        "has_gemini_key": has_key,
        "masked_key": f"{key[:7]}...{key[-4:]}" if has_key else "Not Configured",
        "embedding_model": embed_status["embedding_model"],
        "embedding_dimension": embed_status["embedding_dimension"],
        "retrieval_mode": embed_status["mode"],
        "is_live_api": embed_status["is_live_api"],
        "llm_model": LLM_MODEL,
        "default_rag_version": RAG_VERSION,
        "supported_versions": ["v1", "v2", "v3"]
    }

@app.post("/api/config")
def update_system_config(req: ConfigUpdateRequest):
    clean_key = req.gemini_api_key.strip()
    if not clean_key or len(clean_key) < 8:
        raise HTTPException(status_code=400, detail="Invalid API key format.")
    set_gemini_api_key(clean_key)
    return get_system_config()

@app.get("/api/contracts")
def get_contracts():
    return {"contracts": list_indexed_contracts()}

@app.post("/api/contracts/upload")
async def upload_contract(file: UploadFile = File(...)):
    # 1. Filename sanitization to prevent path traversal
    safe_filename = Path(file.filename).name
    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    # 2. File size and header validation
    try:
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(pdf_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds maximum allowed size of 25MB.")

        # Validate PDF magic bytes: %PDF-
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Invalid file format: Missing PDF magic header.")

        # Execute indexing in thread pool to prevent blocking event loop
        result = await run_in_threadpool(index_contract, pdf_bytes, safe_filename)
        return {
            "message": f"Successfully indexed '{safe_filename}'",
            "contract": result["contract"],
            "total_clauses": result["total_clauses"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contracts/{contract_name}/clauses")
def get_clauses_for_contract(contract_name: str):
    clauses = get_contract_clauses(contract_name)
    if not clauses:
        raise HTTPException(status_code=404, detail="Contract not found or has no indexed clauses.")
    return {"contract": contract_name, "clauses": clauses}

@app.post("/api/contracts/explain-clause")
async def explain_clause(req: ExplainClauseRequest):
    return await run_in_threadpool(explain_single_clause, req.clause_text, req.clause_number, req.contract_name)

@app.post("/api/analyze")
async def run_analysis(req: AnalyzeRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    kwargs = {}
    if req.top_k is not None:
        kwargs["top_k"] = req.top_k
    if req.min_score is not None:
        kwargs["min_score"] = req.min_score

    result = await run_in_threadpool(
        analyze_contract,
        req.question,
        req.contract_name,
        req.version,
        **kwargs
    )
    return result

@app.post("/api/scan-risks")
async def run_risk_scan(req: ScanRisksRequest):
    return await run_in_threadpool(flag_risky_clauses, req.contract_name)

@app.post("/api/compare")
async def run_contract_comparison(req: CompareRequest):
    return await run_in_threadpool(compare_contracts, req.contract_a, req.contract_b, req.topic)

@app.post("/api/load-samples")
async def load_sample_contracts():
    try:
        sample_files = await run_in_threadpool(ensure_sample_contracts)
        results = []
        for p in sample_files:
            with open(p, "rb") as f:
                bytes_data = f.read()
                res = await run_in_threadpool(index_contract, bytes_data, p.name)
                results.append({"name": p.name, "clauses": res["total_clauses"]})
        return {
            "message": "Sample contracts loaded and indexed successfully!",
            "contracts": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/contracts/{contract_name}")
def remove_contract(contract_name: str):
    success = delete_contract(contract_name)
    return {"success": success, "contract": contract_name}

@app.get("/api/benchmark/results")
def get_benchmark_results():
    """Returns genuine benchmark results if executed, or N/A message."""
    json_path = EVALUATION_DIR / "results" / "benchmark_results.json"
    if not json_path.exists():
        return {
            "has_results": False,
            "message": "Benchmark not yet evaluated. Run 'python scripts/run_evaluation.py' to generate metrics.",
            "results": None
        }

    import json
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "has_results": True,
        "timestamp": data.get("timestamp"),
        "summary": data.get("summary"),
        "full_results": data.get("full_results")
    }

# Serve static frontend files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
