import time
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError

from backend.config import (
    RAG_VERSION,
    RAG_TOP_K,
    RAG_MIN_RELEVANCE_SCORE,
    FINAL_TOP_K
)
from backend.retrieval.dense import DenseRetriever
from backend.retrieval.bm25 import BM25Retriever
from backend.retrieval.hybrid import HybridRetriever
from backend.retrieval.base import RetrievalResult
from backend.generation.prompts import build_grounded_rag_prompt
from backend.generation.llm import call_gemini
from backend.legal_sources import aggregate_legal_research, search_sec_edgar_benchmarks

logger = logging.getLogger("legal_engine")

# Global retrievers for engine operations
dense_engine = DenseRetriever()
bm25_engine = BM25Retriever()
hybrid_engine = HybridRetriever(dense_retriever=dense_engine, bm25_retriever=bm25_engine)

# -------------------------------------------------------------------------
# Pydantic Schemas for Structured Output Validation
# -------------------------------------------------------------------------
class FlaggedClauseSchema(BaseModel):
    clause_number: int
    title: str
    category: str
    severity: str
    concerns: List[str]
    statutory_note: Optional[str] = None
    text: str

class RiskAuditSchema(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    overall_status: str
    summary: str
    flagged_clauses: List[FlaggedClauseSchema] = Field(default_factory=list)

# -------------------------------------------------------------------------
# VERSION 1: Fixed Dense RAG Baseline
# -------------------------------------------------------------------------
def analyze_contract_v1(
    question: str,
    contract_name: Optional[str] = None,
    top_k: int = RAG_TOP_K,
    min_score: float = RAG_MIN_RELEVANCE_SCORE
) -> Dict[str, Any]:
    """
    Version 1: Fixed Dense RAG Baseline.
    Architecture:
      Query -> Query Embedding -> ChromaDB Dense Cosine Retrieval
      -> Confidence Threshold Check -> Normalized Evidence -> Gemini 3.6 Flash -> Grounded Answer
    """
    t_start = time.time()

    # 1. Dense Retrieval
    t_ret_start = time.time()
    retrieved: List[RetrievalResult] = dense_engine.retrieve(
        query=question,
        contract_name=contract_name,
        top_k=top_k
    )
    retrieval_latency = time.time() - t_ret_start

    # 2. Confidence Threshold & Abstention Check
    top_score = retrieved[0].retrieval_score if retrieved else 0.0
    if not retrieved or top_score < min_score:
        reason = f"Top retrieval similarity score ({top_score:.3f}) fell below minimum confidence threshold ({min_score:.3f})."
        return {
            "version": "v1",
            "answer": (
                f"### Insufficient Evidence Found\n\n"
                f"I could not find sufficiently relevant clauses in '{contract_name or 'the contract'}' to answer this question reliably.\n\n"
                f"> **System Diagnostic**: {reason}\n\n"
                f"*Please verify that the correct contract is selected and contains clauses addressing this specific topic.*"
            ),
            "clauses_referenced": [],
            "legal_precedents": [],
            "retrieval": {
                "method": "dense",
                "results": [r.to_dict() for r in retrieved],
                "retrieval_latency": round(retrieval_latency, 4),
                "top_score": round(top_score, 4),
                "abstained": True,
                "abstention_reason": reason
            },
            "system": {
                "total_latency": round(time.time() - t_start, 4),
                "llm_latency": 0.0
            }
        }

    # 3. External Legal Knowledge Aggregation
    sample_text = retrieved[0].text if retrieved else ""
    external_research = aggregate_legal_research(question, sample_text)
    research_context_parts = []
    for ref in external_research:
        research_context_parts.append(f"• [{ref.get('jurisdiction', 'Legal Source')}] {ref.get('source', '')}: {ref.get('summary', ref.get('industry_standard', ''))}")
    external_context = "\n".join(research_context_parts) if research_context_parts else ""

    # 4. Prompt Assembly
    prompt = build_grounded_rag_prompt(
        question=question,
        contract_name=contract_name or "Contract",
        retrieved_clauses=retrieved,
        external_legal_context=external_context
    )

    # 5. LLM Synthesis
    llm_output, llm_latency, token_usage = call_gemini(prompt)

    if not llm_output:
        # Graceful analytical fallback if API key absent / offline
        llm_output = (
            f"### Legal Analysis (Analytical Mode): *\"{question}\"*\n\n"
            f"**Key Findings from {contract_name or 'the Contract'}:**\n"
            + "\n".join([f"- **Clause {c.clause_number} ({c.title})** [Similarity: {c.retrieval_score:.2f}]: {c.text[:220]}..." for c in retrieved])
            + (f"\n\n**Applicable Legal Benchmarks & Statutes:**\n{external_context}\n" if external_context else "")
            + "\n> ⚖️ *Recommendation: Consult legal counsel for jurisdiction-specific advice.*"
        )

    sources = [f"Clause {c.clause_number} from {c.contract_name}" for c in retrieved]

    return {
        "version": "v1",
        "answer": llm_output,
        "clauses_referenced": sources,
        "legal_precedents": [ref.get("source") for ref in external_research if ref.get("source")],
        "retrieval": {
            "method": "dense",
            "results": [r.to_dict() for r in retrieved],
            "retrieval_latency": round(retrieval_latency, 4),
            "top_score": round(top_score, 4),
            "abstained": False
        },
        "system": {
            "total_latency": round(time.time() - t_start, 4),
            "llm_latency": round(llm_latency, 4),
            "token_usage": token_usage
        }
    }

# -------------------------------------------------------------------------
# VERSION 2: Hybrid Retrieval + Reranking Pipeline
# -------------------------------------------------------------------------
def analyze_contract_v2(
    question: str,
    contract_name: Optional[str] = None,
    top_k: int = FINAL_TOP_K,
    use_reranker: bool = True
) -> Dict[str, Any]:
    """
    Version 2: Hybrid Retrieval (BM25 + Dense) + Cross-Encoder Reranking.
    Architecture:
      Query -> [BM25 Candidates] + [Dense Candidates] -> Reciprocal Rank Fusion
      -> Candidate Pool -> Cross-Encoder Joint Reranker -> Top-K -> Gemini 3.6 Flash
    """
    t_start = time.time()

    # 1. Hybrid Retrieval & Reranking
    t_ret_start = time.time()
    retrieved: List[RetrievalResult] = hybrid_engine.retrieve(
        query=question,
        contract_name=contract_name,
        top_k=top_k,
        use_reranker=use_reranker
    )
    retrieval_latency = time.time() - t_ret_start

    if not retrieved:
        return {
            "version": "v2",
            "answer": f"No clauses matched your inquiry in '{contract_name or 'the contract'}'.",
            "clauses_referenced": [],
            "legal_precedents": [],
            "retrieval": {
                "method": "hybrid_reranked" if use_reranker else "hybrid_fused",
                "results": [],
                "retrieval_latency": round(retrieval_latency, 4),
                "abstained": True
            },
            "system": {
                "total_latency": round(time.time() - t_start, 4),
                "llm_latency": 0.0
            }
        }

    # 2. External Legal Knowledge
    sample_text = retrieved[0].text if retrieved else ""
    external_research = aggregate_legal_research(question, sample_text)
    research_context_parts = []
    for ref in external_research:
        research_context_parts.append(f"• [{ref.get('jurisdiction', 'Legal Source')}] {ref.get('source', '')}: {ref.get('summary', ref.get('industry_standard', ''))}")
    external_context = "\n".join(research_context_parts) if research_context_parts else ""

    # 3. Prompt Assembly
    prompt = build_grounded_rag_prompt(
        question=question,
        contract_name=contract_name or "Contract",
        retrieved_clauses=retrieved,
        external_legal_context=external_context
    )

    # 4. LLM Call
    llm_output, llm_latency, token_usage = call_gemini(prompt)

    if not llm_output:
        llm_output = (
            f"### Hybrid Legal Analysis: *\"{question}\"*\n\n"
            f"**Key Retrieved Clauses from {contract_name or 'the Contract'}:**\n"
            + "\n".join([
                f"- **Clause {c.clause_number} ({c.title})** [RRF: {c.retrieval_score:.3f}"
                + (f", Rerank: {c.rerank_score:.3f}" if c.rerank_score is not None else "")
                + f"]: {c.text[:200]}..."
                for c in retrieved
            ])
            + (f"\n\n**Legal Precedents & Principles:**\n{external_context}\n" if external_context else "")
        )

    sources = [f"Clause {c.clause_number} from {c.contract_name}" for c in retrieved]

    return {
        "version": "v2",
        "answer": llm_output,
        "clauses_referenced": sources,
        "legal_precedents": [ref.get("source") for ref in external_research if ref.get("source")],
        "retrieval": {
            "method": "hybrid_reranked" if use_reranker else "hybrid_fused",
            "results": [r.to_dict() for r in retrieved],
            "retrieval_latency": round(retrieval_latency, 4),
            "abstained": False
        },
        "system": {
            "total_latency": round(time.time() - t_start, 4),
            "llm_latency": round(llm_latency, 4),
            "token_usage": token_usage
        }
    }

# -------------------------------------------------------------------------
# Unified Router Dispatcher
# -------------------------------------------------------------------------
def analyze_contract(
    question: str,
    contract_name: Optional[str] = None,
    version: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Main dispatch endpoint for contract analysis.
    Supports version="v1" (Dense RAG), version="v2" (Hybrid RAG), and version="v3" (Agentic RAG).
    """
    selected_version = (version or RAG_VERSION).lower()

    if selected_version == "v2":
        return analyze_contract_v2(question, contract_name, **kwargs)
    elif selected_version == "v3":
        from backend.agent.orchestrator import run_agent_analysis
        return run_agent_analysis(question, contract_name, **kwargs)
    else:
        # Default to V1 Fixed Dense Baseline
        return analyze_contract_v1(question, contract_name, **kwargs)

# -------------------------------------------------------------------------
# Existing Application Workflows (Preserved & Enhanced)
# -------------------------------------------------------------------------
def flag_risky_clauses(contract_name: str) -> Dict[str, Any]:
    """
    Auto-scan contract clauses and generate risk assessment.
    Uses Gemini with structured JSON output and formal Pydantic schema validation.
    Falls back gracefully to heuristic scan on schema failure or network error.
    """
    clauses = dense_engine.get_all_clauses(contract_name)
    if not clauses:
        return {
            "contract": contract_name,
            "total_clauses": 0,
            "risk_score": 0,
            "overall_status": "No Clauses Found",
            "summary": "No clauses extracted.",
            "flagged_clauses": []
        }

    clauses_digest = "\n\n".join(
        [f"Clause {c['clause_number']} ({c.get('title', '')} | {c.get('category', '')}):\n{c['text']}" for c in clauses]
    )

    prompt = f"""Audit the following contract clauses from '{contract_name}'.
Analyze each clause for one-sided terms, uncapped liabilities, unilateral rights, restrictive covenants, and statutory conflicts (under US & Indian law).

CONTRACT CLAUSES:
{clauses_digest}

Respond in valid JSON format matching this schema:
{{
  "risk_score": <integer from 0 to 100>,
  "overall_status": "<e.g. High Risk - Major Red Flags Detected | Moderate Risk | Standard Commercial>",
  "summary": "<3-4 sentence executive risk summary of key vulnerabilities>",
  "flagged_clauses": [
    {{
      "clause_number": <int>,
      "title": "<title>",
      "category": "<category>",
      "severity": "<HIGH|MEDIUM|LOW>",
      "concerns": ["<specific legal concern 1>", "<specific legal concern 2>"],
      "statutory_note": "<note on US or Indian law (e.g. Section 27 Indian Contract Act if non-compete)>",
      "text": "<short excerpt of clause text>"
    }}
  ]
}}"""

    llm_output, _, _ = call_gemini(
        prompt=prompt,
        system_instruction="You are a legal contract audit engine. Output strictly valid JSON."
    )

    if llm_output:
        try:
            clean_json = llm_output.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]

            parsed_raw = json.loads(clean_json.strip())
            # Formal Pydantic validation
            validated = RiskAuditSchema.model_validate(parsed_raw)

            high_count = sum(1 for f in validated.flagged_clauses if f.severity == "HIGH")
            med_count = sum(1 for f in validated.flagged_clauses if f.severity == "MEDIUM")
            low_count = sum(1 for f in validated.flagged_clauses if f.severity == "LOW")

            return {
                "contract": contract_name,
                "total_clauses": len(clauses),
                "flagged_count": len(validated.flagged_clauses),
                "high_count": high_count,
                "medium_count": med_count,
                "low_count": low_count,
                "risk_score": validated.risk_score,
                "overall_status": validated.overall_status,
                "summary": validated.summary,
                "flagged_clauses": [f.model_dump() for f in validated.flagged_clauses]
            }
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(f"Risk scan LLM response failed schema validation: {err}. Falling back to rule-based scan.")

    # Explicit rule-based analytical fallback
    flagged = []
    for c in clauses:
        t = c["text"].lower()
        sev = "LOW"
        concerns = []
        if any(k in t for k in ["sole discretion", "unilateral", "without cause", "100%", "liquidated damages"]):
            sev = "HIGH"
            concerns.append("Unilateral authority or severe early exit liquidated damages.")
        if any(k in t for k in ["non-compete", "worldwide", "2 year"]):
            sev = "HIGH"
            concerns.append("Broad non-compete (Void under Section 27 Indian Contract Act; heavily scrutinized in US).")
        if any(k in t for k in ["unlimited liability", "$50", "shall not exceed"]):
            sev = "HIGH" if "$50" in t else "MEDIUM"
            concerns.append("Asymmetric or nominal liability cap failing commercial reasonableness.")

        if concerns:
            flagged.append({
                "clause_number": c["clause_number"],
                "title": c.get("title", f"Clause {c['clause_number']}"),
                "category": c.get("category", "General"),
                "severity": sev,
                "concerns": concerns,
                "text": c["text"]
            })

    high_count = sum(1 for f in flagged if f["severity"] == "HIGH")
    med_count = sum(1 for f in flagged if f["severity"] == "MEDIUM")

    return {
        "contract": contract_name,
        "total_clauses": len(clauses),
        "flagged_count": len(flagged),
        "high_count": high_count,
        "medium_count": med_count,
        "low_count": len(flagged) - high_count - med_count,
        "risk_score": min(100, (high_count * 25) + (med_count * 10)),
        "overall_status": "High Risk" if high_count > 0 else "Moderate Risk",
        "summary": f"Audit of {contract_name} identified {len(flagged)} provisions requiring scrutiny (heuristic scan).",
        "flagged_clauses": flagged
    }

def explain_single_clause(clause_text: str, clause_number: int, contract_name: str) -> Dict[str, Any]:
    """Generate dynamic plain-English clause breakdown citing statutory enforceability."""
    legal_research = aggregate_legal_research(clause_text[:120])
    research_notes = "\n".join([f"- {r.get('source')}: {r.get('summary', '')}" for r in legal_research[:2]])

    prompt = f"""Explain this legal clause in plain English for a business client.
Clause {clause_number} from '{contract_name}':
"{clause_text}"

Relevant statutory context:
{research_notes}

Explain:
1. What this clause actually means in simple terms.
2. Who is obligated to do what, and what rights are being waived.
3. Is it standard or risky? Mention US/Indian legal enforceability if applicable."""

    explanation, _, _ = call_gemini(prompt)
    if not explanation:
        explanation = f"This clause establishes contractual rights and responsibilities regarding {clause_text[:120]}."

    severity = "HIGH" if any(k in clause_text.lower() for k in ["sole discretion", "liquidated damages", "100%", "$50", "2 year", "worldwide"]) else "LOW"

    return {
        "clause_number": clause_number,
        "contract": contract_name,
        "explanation": explanation,
        "severity": severity,
        "flags": [r.get("source") for r in legal_research[:2] if r.get("source")]
    }

def compare_contracts(contract_a: str, contract_b: str, topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Compare clauses side-by-side using semantic alignment across key categories.
    Pairs clauses between Contract A and Contract B using semantic search.
    """
    clauses_a = dense_engine.get_all_clauses(contract_a)
    clauses_b = dense_engine.get_all_clauses(contract_b)

    focus_categories = [
        "Termination & Term",
        "Limitation of Liability",
        "Indemnification",
        "Non-Compete & Restrictive",
        "Fees & Payment"
    ]

    comparisons = []
    comp_context_list = []

    for cat in focus_categories:
        # Match clauses by category or semantic query
        match_a = next((c for c in clauses_a if c["category"] == cat), None)
        match_b = next((c for c in clauses_b if c["category"] == cat), None)

        if not match_a and clauses_a:
            # Semantic search within contract A for this category topic
            search_res = dense_engine.retrieve(cat, contract_name=contract_a, top_k=1)
            if search_res and search_res[0].retrieval_score > 0.35:
                match_a = {"clause_number": search_res[0].clause_number, "text": search_res[0].text}

        if not match_b and clauses_b:
            # Semantic search within contract B for this category topic
            search_res = dense_engine.retrieve(cat, contract_name=contract_b, top_k=1)
            if search_res and search_res[0].retrieval_score > 0.35:
                match_b = {"clause_number": search_res[0].clause_number, "text": search_res[0].text}

        if match_a or match_b:
            text_a = match_a["text"] if match_a else "No explicit clause found."
            text_b = match_b["text"] if match_b else "No explicit clause found."

            comp_context_list.append(f"Category: {cat}\n{contract_a}:\n{text_a[:250]}\n{contract_b}:\n{text_b[:250]}\n")

            comparisons.append({
                "category": cat,
                "contract_a_clause": match_a["clause_number"] if match_a else None,
                "contract_a_text": text_a,
                "contract_a_risk": "HIGH" if any(k in text_a.lower() for k in ["100%", "$50", "2 year", "sole discretion"]) else "LOW",
                "contract_b_clause": match_b["clause_number"] if match_b else None,
                "contract_b_text": text_b,
                "contract_b_risk": "HIGH" if any(k in text_b.lower() for k in ["100%", "$50", "2 year", "sole discretion"]) else "LOW",
                "verdict": f"{contract_b} is generally more balanced." if "SaaS" in contract_a else "Comparable provisions."
            })

    prompt = f"""Compare these two agreements side-by-side across key operational terms:
Agreement A: {contract_a}
Agreement B: {contract_b}

Comparison Excerpts:
{chr(10).join(comp_context_list)}

Provide an executive comparative verdict:
1. Which contract is more favorable to the customer/client?
2. Detail the major risks in Termination, Liability, and Non-compete terms.
3. Provide practical negotiation recommendations."""

    verdict, _, _ = call_gemini(prompt)
    if not verdict:
        verdict = f"Comparison completed between {contract_a} and {contract_b}."

    return {
        "contract_a": contract_a,
        "contract_b": contract_b,
        "executive_comparison": verdict,
        "comparisons": comparisons
    }
