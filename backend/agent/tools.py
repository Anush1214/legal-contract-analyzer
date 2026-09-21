import logging
from typing import Dict, Any, List, Optional

from backend.retrieval.hybrid import HybridRetriever
from backend.retrieval.dense import DenseRetriever
from backend.legal_sources import (
    search_indian_law,
    search_courtlistener,
    search_uk_law,
    search_sec_edgar_benchmarks
)

logger = logging.getLogger("agent.tools")

# Module-level instances
_dense = DenseRetriever()
_hybrid = HybridRetriever(dense_retriever=_dense)

def search_contract(query: str, contract_name: Optional[str] = None, top_k: int = 4) -> Dict[str, Any]:
    """
    Search contract clauses using Version 2 Hybrid Retrieval (BM25 + Dense + Cross-Encoder Reranking).
    Use this to find specific contract obligations, definitions, liabilities, or termination clauses.
    """
    if not query or not query.strip():
        return {"error": "Query cannot be empty.", "clauses": []}

    try:
        results = _hybrid.retrieve(query=query, contract_name=contract_name, top_k=top_k, use_reranker=True)
        return {
            "query": query,
            "contract_name": contract_name,
            "count": len(results),
            "clauses": [
                {
                    "clause_id": r.clause_id,
                    "clause_number": r.clause_number,
                    "title": r.title,
                    "category": r.category,
                    "text": r.text,
                    "page": r.page,
                    "retrieval_score": r.retrieval_score,
                    "rerank_score": r.rerank_score,
                    "contract": r.contract_name
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"search_contract tool error: {e}")
        return {"error": str(e), "clauses": []}

def get_clause(contract_name: str, clause_id: str) -> Dict[str, Any]:
    """
    Retrieve full verbatim clause content and metadata by clause ID or clause number.
    Use this when you have identified a specific clause number and need its complete unclipped text.
    """
    if not contract_name:
        return {"error": "contract_name is required."}

    all_clauses = _dense.get_all_clauses(contract_name)
    if not all_clauses:
        return {"error": f"No clauses found for contract '{contract_name}'."}

    # Match by doc ID or integer clause number
    target = None
    for c in all_clauses:
        if c.get("clause_id") == clause_id:
            target = c
            break
        # Check if clause_id is string of int
        if str(c.get("clause_number")) == str(clause_id).replace("clause_", "").replace("Section ", "").replace("Clause ", ""):
            target = c
            break

    if target:
        return {
            "found": True,
            "contract": contract_name,
            "clause_id": target.get("clause_id", f"{contract_name}_clause_{target.get('clause_number')}"),
            "clause_number": target.get("clause_number"),
            "title": target.get("title"),
            "category": target.get("category"),
            "text": target.get("text"),
            "page": target.get("page")
        }
    return {"found": False, "message": f"Clause '{clause_id}' not found in '{contract_name}'."}

def search_statutes(query: str, jurisdiction: Optional[str] = "all") -> Dict[str, Any]:
    """
    Search applicable statutory provisions and legal frameworks across Indian Law (Indian Contract Act, 1872),
    UK Law (Unfair Contract Terms Act 1977), and US Commercial Law (UCC § 2-719, Restatement).
    """
    if not query:
        return {"error": "Query cannot be empty.", "results": []}

    j_lower = (jurisdiction or "all").lower()
    results = []

    if j_lower in ["india", "indian", "all"]:
        for item in search_indian_law(query):
            results.append({
                "source": item["source"],
                "jurisdiction": item["jurisdiction"],
                "topic": item["topic"],
                "summary": item["summary"]
            })

    if j_lower in ["uk", "united kingdom", "all"]:
        for item in search_uk_law(query):
            results.append({
                "source": item["source"],
                "jurisdiction": item["jurisdiction"],
                "summary": item["summary"]
            })

    # Search SEC EDGAR market standards
    for cat in ["Termination & Term", "Limitation of Liability", "Non-Compete & Restrictive", "Indemnification"]:
        if any(w in query.lower() for w in cat.lower().split()):
            bench = search_sec_edgar_benchmarks(cat)
            if bench:
                results.append({
                    "source": bench["source"],
                    "jurisdiction": "Commercial Market Standard (SEC EDGAR)",
                    "summary": bench["industry_standard"]
                })

    return {
        "query": query,
        "jurisdiction": jurisdiction,
        "count": len(results),
        "results": results
    }

def search_cases(query: str, jurisdiction: Optional[str] = "us") -> Dict[str, Any]:
    """
    Search case law precedents from CourtListener (US Federal/Appellate courts) and landmark judicial doctrines.
    Use this to verify enforceability, reasonableness tests, and judicial scrutiny standards.
    """
    if not query:
        return {"error": "Query cannot be empty.", "cases": []}

    try:
        cases = search_courtlistener(query, max_results=3)
        return {
            "query": query,
            "count": len(cases),
            "cases": cases
        }
    except Exception as e:
        logger.error(f"search_cases tool error: {e}")
        return {"error": str(e), "cases": []}

def compare_contracts_tool(contract_a: str, contract_b: str, topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Compare clauses between two contracts side-by-side, optionally focusing on a specific topic.
    """
    if not contract_a or not contract_b:
        return {"error": "Both contract_a and contract_b are required."}

    clauses_a = _dense.get_all_clauses(contract_a)
    clauses_b = _dense.get_all_clauses(contract_b)

    results_a = [c for c in clauses_a if not topic or topic.lower() in c["text"].lower() or topic.lower() in c.get("category", "").lower()]
    results_b = [c for c in clauses_b if not topic or topic.lower() in c["text"].lower() or topic.lower() in c.get("category", "").lower()]

    return {
        "contract_a": contract_a,
        "contract_b": contract_b,
        "topic": topic,
        "contract_a_matches": [{"clause_number": c["clause_number"], "title": c["title"], "text": c["text"][:250]} for c in results_a[:3]],
        "contract_b_matches": [{"clause_number": c["clause_number"], "title": c["title"], "text": c["text"][:250]} for c in results_b[:3]]
    }
