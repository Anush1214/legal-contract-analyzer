import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_config_endpoint():
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "embedding_model" in data
    assert "retrieval_mode" in data
    assert "supported_versions" in data
    assert "v1" in data["supported_versions"]
    assert "v2" in data["supported_versions"]
    assert "v3" in data["supported_versions"]

def test_upload_invalid_file_extension():
    res = client.post(
        "/api/contracts/upload",
        files={"file": ("test.txt", b"some plain text", "text/plain")}
    )
    assert res.status_code == 400
    assert "Only PDF files" in res.json()["detail"]

def test_upload_empty_file():
    res = client.post(
        "/api/contracts/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"]

def test_upload_missing_magic_bytes():
    res = client.post(
        "/api/contracts/upload",
        files={"file": ("fake.pdf", b"This is not a pdf file format", "application/pdf")}
    )
    assert res.status_code == 400
    assert "Missing PDF magic header" in res.json()["detail"]

def test_analyze_empty_question():
    res = client.post(
        "/api/analyze",
        json={"question": "   ", "contract_name": "Test.pdf"}
    )
    assert res.status_code == 400
    assert "Question cannot be empty" in res.json()["detail"]

def test_analyze_v1_pipeline():
    res = client.post(
        "/api/analyze",
        json={
            "question": "Can the customer terminate early?",
            "contract_name": "Enterprise_SaaS_Vendor_Agreement.pdf",
            "version": "v1"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "v1"
    assert "answer" in data
    assert "retrieval" in data
    assert data["retrieval"]["method"] == "dense"

def test_analyze_v2_pipeline():
    res = client.post(
        "/api/analyze",
        json={
            "question": "What is the limitation of liability cap?",
            "contract_name": "Enterprise_SaaS_Vendor_Agreement.pdf",
            "version": "v2"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "v2"
    assert "answer" in data
    assert "retrieval" in data
    assert "hybrid" in data["retrieval"]["method"]

def test_benchmark_results_endpoint():
    res = client.get("/api/benchmark/results")
    assert res.status_code == 200
    data = res.json()
    assert "has_results" in data
