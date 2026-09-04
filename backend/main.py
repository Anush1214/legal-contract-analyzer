import os
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import get_gemini_api_key, set_gemini_api_key, LLM_MODEL, EMBEDDING_MODEL, SAMPLE_DIR
from backend.vector_store import (
    index_contract,
    list_indexed_contracts,
    get_contract_clauses,
    delete_contract,
    contract_collection
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
    description="RAG-powered Legal Contract Analyzer using ChromaDB and Gemini 3.7 Flash",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Request Models
class AnalyzeRequest(BaseModel):
    question: str
    contract_name: Optional[str] = None

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
    key = get_gemini_api_key()
    has_key = bool(key and len(key) > 8 and not key.startswith("demo_"))
    return {
        "has_gemini_key": has_key,
        "masked_key": f"{key[:7]}...{key[-4:]}" if has_key else "Not Configured",
        "embedding_model": EMBEDDING_MODEL,
        "llm_model": LLM_MODEL,
        "mode": f"Live Google {LLM_MODEL} + ChromaDB RAG" if has_key else "Local Legal Heuristic Mode"
    }

@app.post("/api/config")
def update_system_config(req: ConfigUpdateRequest):
    set_gemini_api_key(req.gemini_api_key)
    return get_system_config()

@app.get("/api/contracts")
def get_contracts():
    return {"contracts": list_indexed_contracts()}

@app.post("/api/contracts/upload")
async def upload_contract(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            
        result = index_contract(pdf_bytes, file.filename)
        return {
            "message": f"Successfully indexed '{file.filename}'",
            "contract": result["contract"],
            "total_clauses": result["total_clauses"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contracts/{contract_name}/clauses")
def get_clauses_for_contract(contract_name: str):
    clauses = get_contract_clauses(contract_name)
    if not clauses:
        raise HTTPException(status_code=404, detail="Contract not found or has no indexed clauses.")
    return {"contract": contract_name, "clauses": clauses}

@app.post("/api/contracts/explain-clause")
def explain_clause(req: ExplainClauseRequest):
    return explain_single_clause(req.clause_text, req.clause_number, req.contract_name)

@app.post("/api/analyze")
def run_contract_analysis(req: AnalyzeRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return analyze_contract(req.question, req.contract_name)

@app.post("/api/scan-risks")
def run_risk_scan(req: ScanRisksRequest):
    return flag_risky_clauses(req.contract_name)

@app.post("/api/compare")
def run_contract_comparison(req: CompareRequest):
    return compare_contracts(req.contract_a, req.contract_b, req.topic)

@app.post("/api/load-samples")
def load_sample_contracts():
    try:
        sample_files = ensure_sample_contracts()
        results = []
        for p in sample_files:
            with open(p, "rb") as f:
                bytes_data = f.read()
                res = index_contract(bytes_data, p.name)
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

# Serve static frontend files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
