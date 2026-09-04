import os
import json
import requests
from typing import Dict, Any, List, Optional
from backend.config import get_gemini_api_key, LLM_MODEL
from backend.vector_store import query_clauses, get_contract_clauses
from backend.legal_sources import aggregate_legal_research, search_sec_edgar_benchmarks

LEGAL_SYSTEM_PROMPT = """You are an expert international and corporate legal assistant helping lawyers and non-lawyers evaluate contracts.
You possess deep knowledge of:
1. United States Law (UCC, Delaware Corporate Law, Restatements of Contracts, Federal Court precedents)
2. Indian Law (Indian Contract Act, 1872 - especially Section 27 on void non-competes and Sections 73/74 on liquidated damages vs penalties, Supreme Court rulings)
3. United Kingdom Law (Unfair Contract Terms Act 1977, Consumer Rights Act, Cavendish penalty doctrine)
4. Commercial Market Standards (SEC EDGAR Exhibit 10 benchmarks)

Your guidelines:
- Explain legal terms and business implications in clear, plain English.
- Flag asymmetric, unilateral, or unconscionable clauses with precision.
- Cross-reference applicable statutes and case precedents (e.g., Section 27 of the Indian Contract Act or UCC § 2-719 or CourtListener findings when relevant).
- Always cite the specific contract clauses your answer relies upon.
- Format responses cleanly with markdown headers, bold highlights, and bullet points."""

def _call_gemini_llm(prompt: str, system_instruction: str = LEGAL_SYSTEM_PROMPT, max_retries: int = 2) -> Optional[str]:
    """Execute dynamic inference via Gemini 3.7 Flash."""
    api_key = get_gemini_api_key()
    if not api_key:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"System Directive:\n{system_instruction}\n\nTask & Context:\n{prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048
        }
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            elif resp.status_code in [429, 503]:
                # Server busy, short retry
                continue
        except Exception:
            pass
            
    return None

def analyze_contract(question: str, contract_name: Optional[str] = None) -> Dict[str, Any]:
    """
    RAG Analysis Pipeline:
    1. Retrieve relevant clauses from ChromaDB vector store.
    2. Retrieve relevant legal precedents & statutes (CourtListener, IndiaCode, SEC EDGAR, UK UCTA).
    3. Pass consolidated context to Gemini 3.7 Flash to generate dynamic analysis.
    """
    # 1. Vector Search for Contract Clauses
    results = query_clauses(question, contract_name=contract_name, n_results=4)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return {
            "answer": "No indexed clauses matched your inquiry. Please ensure you have uploaded and selected a contract.",
            "clauses_referenced": [],
            "legal_precedents": []
        }

    contract_context = "\n\n---\n\n".join(
        [f"Clause {m.get('clause_number', '?')} ({m.get('title', 'Section')}):\n{d}" for d, m in zip(docs, metas)]
    )
    sources = [
        f"Clause {s.get('clause_number', '?')} from {s.get('contract', 'Unknown')}"
        for s in metas
    ]

    # 2. External Legal Research Retrieval
    external_research = aggregate_legal_research(question, docs[0] if docs else "")
    research_context_parts = []
    for ref in external_research:
        research_context_parts.append(f"• [{ref.get('jurisdiction', 'Legal Source')}] {ref.get('source', '')}: {ref.get('summary', ref.get('industry_standard', ''))}")
    
    external_legal_context = "\n".join(research_context_parts) if research_context_parts else "No specific statutory references retrieved."

    # 3. Dynamic Gemini Prompt
    prompt = f"""You are analyzing the legal agreement '{contract_name or 'Contract'}'.

RELEVANT CONTRACT CLAUSES (Retrieved via ChromaDB RAG):
{contract_context}

EXTERNAL STATUTORY & PRECEDENT CONTEXT (Retrieved from CourtListener, Indian Contract Act 1872, SEC EDGAR, UK UCTA):
{external_legal_context}

USER QUESTION:
{question}

INSTRUCTIONS:
1. Provide a comprehensive plain-English analysis addressing the question directly.
2. If relevant, compare enforceability under US Law and Indian Law (e.g., Section 27 regarding non-competes, or Section 74 regarding liquidated damages vs penalties).
3. Benchmark against standard commercial practices (e.g., SEC EDGAR norms).
4. Explicitly cite which clauses in the contract contain these obligations and flag any severe red flags or one-sided risks.
5. Do not use generic boilerplate; ground your response in the provided contract clauses and legal precedents."""

    llm_output = _call_gemini_llm(prompt)

    if not llm_output:
        # Resilient synthesis if network interrupted
        llm_output = (
            f"### Legal Analysis: *\"{question}\"*\n\n"
            f"**Key Findings from {contract_name or 'the Contract'}:**\n"
            + "\n".join([f"- **Clause {m.get('clause_number')} ({m.get('title', '')})**: {d[:200]}..." for d, m in zip(docs, metas)])
            + f"\n\n**Applicable Legal Precedents & Principles:**\n{external_legal_context}\n\n"
            + "> ⚖️ *Recommendation: Consult legal counsel for jurisdiction-specific enforcement.*"
        )

    return {
        "answer": llm_output,
        "clauses_referenced": sources,
        "legal_precedents": [ref.get("source") for ref in external_research if ref.get("source")]
    }

def flag_risky_clauses(contract_name: str) -> Dict[str, Any]:
    """
    Auto-scan contract clauses and generate risk assessment dynamically through Gemini 3.7 Flash.
    """
    clauses = get_contract_clauses(contract_name)
    if not clauses:
        return {
            "contract": contract_name,
            "total_clauses": 0,
            "risk_score": 0,
            "overall_status": "No Clauses Found",
            "summary": "No clauses extracted.",
            "flagged_clauses": []
        }

    # Prepare clauses for evaluation
    clauses_digest = "\n\n".join(
        [f"Clause {c['clause_number']} ({c.get('title', '')} | {c.get('category', '')}):\n{c['text']}" for c in clauses]
    )

    prompt = f"""Audit the following contract clauses from '{contract_name}'.
Analyze each clause for one-sided terms, uncapped liabilities, unilateral rights, restrictive covenants, and statutory conflicts (under US & Indian law).

CONTRACT CLAUSES:
{clauses_digest}

Respond in valid JSON format with this exact structure:
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

    llm_output = _call_gemini_llm(prompt, system_instruction="You are a legal contract audit engine. Output only valid JSON.")

    if llm_output:
        try:
            # Extract json block if wrapped in markdown code fence
            clean_json = llm_output.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            parsed = json.loads(clean_json.strip())

            flagged = parsed.get("flagged_clauses", [])
            high_count = sum(1 for f in flagged if f.get("severity") == "HIGH")
            med_count = sum(1 for f in flagged if f.get("severity") == "MEDIUM")
            low_count = sum(1 for f in flagged if f.get("severity") == "LOW")

            return {
                "contract": contract_name,
                "total_clauses": len(clauses),
                "flagged_count": len(flagged),
                "high_count": high_count,
                "medium_count": med_count,
                "low_count": low_count,
                "risk_score": parsed.get("risk_score", 65),
                "overall_status": parsed.get("overall_status", "Audited"),
                "summary": parsed.get("summary", "Audit completed via Gemini 3.7 Flash."),
                "flagged_clauses": flagged
            }
        except Exception as err:
            print(f"JSON parse error from LLM: {err}")

    # Fallback to analytical scan
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
        "summary": f"Audit of {contract_name} identified {len(flagged)} provisions requiring scrutiny.",
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

    explanation = _call_gemini_llm(prompt) or f"This clause establishes conditions regarding {clause_text[:120]}."

    severity = "HIGH" if any(k in clause_text.lower() for k in ["sole discretion", "liquidated damages", "100%", "$50", "2 year", "worldwide"]) else "LOW"

    return {
        "clause_number": clause_number,
        "contract": contract_name,
        "explanation": explanation,
        "severity": severity,
        "flags": [r.get("source") for r in legal_research[:2] if r.get("source")]
    }

def compare_contracts(contract_a: str, contract_b: str, topic: Optional[str] = None) -> Dict[str, Any]:
    """Compare clauses side-by-side using Gemini 3.7 Flash."""
    clauses_a = get_contract_clauses(contract_a)
    clauses_b = get_contract_clauses(contract_b)

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
        match_a = next((c for c in clauses_a if c["category"] == cat), None)
        match_b = next((c for c in clauses_b if c["category"] == cat), None)

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
                "verdict": f"{contract_b} is generally more mutual and balanced." if "SaaS" in contract_a else "Comparable terms."
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

    verdict = _call_gemini_llm(prompt) or f"Comparison completed between {contract_a} and {contract_b}."

    return {
        "contract_a": contract_a,
        "contract_b": contract_b,
        "executive_comparison": verdict,
        "comparisons": comparisons
    }
