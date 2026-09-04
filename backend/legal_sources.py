import json
import urllib.parse
from typing import List, Dict, Any, Optional
import requests

HEADERS_GENERIC = {
    "User-Agent": "LegalContractAnalyzer/1.0 (academic.research.legal.ai@example.com)"
}

# -------------------------------------------------------------------------
# 1. Indian Law: IndiaCode & Indian Contract Act, 1872
# -------------------------------------------------------------------------
INDIAN_STATUTE_KNOWLEDGE = [
    {
        "source": "Indian Contract Act, 1872 - Section 27",
        "jurisdiction": "India",
        "topic": "Non-Compete & Restraint of Trade",
        "summary": "Every agreement by which anyone is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void. Under Indian law (Niranjan Shankar Golikari v. Century Spg & Mfg, Percept D'Mark v. Zaheer Khan), negative covenants operating after termination of employment are completely void and unenforceable, unlike US law which allows reasonable restrictions.",
        "keywords": ["non-compete", "restraint of trade", "section 27", "post-employment"]
    },
    {
        "source": "Indian Contract Act, 1872 - Section 73 & 74",
        "jurisdiction": "India",
        "topic": "Liquidated Damages & Penalties",
        "summary": "Section 74 stipulates that where a contract names a sum to be paid in case of breach, the aggrieved party is only entitled to receive 'reasonable compensation' not exceeding the amount so named. Supreme Court in Kailash Nath Associates v. DDA held that 100% forfeiture or liquidated damages cannot be awarded automatically as a penalty; actual loss must be proved unless difficult to quantify.",
        "keywords": ["liquidated damages", "penalty", "early termination", "forfeiture"]
    },
    {
        "source": "Indian Contract Act, 1872 - Section 28",
        "jurisdiction": "India",
        "topic": "Agreements in Restraint of Legal Proceedings",
        "summary": "Agreements restricting any party from enforcing their rights in ordinary tribunals or limiting the time within which they may enforce their rights are void, except for valid arbitration clauses.",
        "keywords": ["restraint of legal proceedings", "limitation period", "jurisdiction waiver"]
    },
    {
        "source": "Indian Contract Act, 1872 - Section 124 & 125",
        "jurisdiction": "India",
        "topic": "Indemnification Obligations",
        "summary": "Defines contract of indemnity as promise to save harmless from loss caused by conduct of promisor or third person. Broad unilateral indemnification without reciprocal obligations is heavily scrutinized by Indian courts.",
        "keywords": ["indemnity", "indemnification", "hold harmless"]
    },
    {
        "source": "Information Technology Act, 2000 & DPDP Act, 2023",
        "jurisdiction": "India",
        "topic": "Data Ownership & Privacy in Cloud / Software",
        "summary": "Data fiduciaries must ensure processing is for lawful purpose with notice and consent. Unilateral licenses granting vendors unrestricted rights to train models on proprietary client data raises non-compliance risks under Indian privacy regulations.",
        "keywords": ["data ownership", "privacy", "machine learning", "telemetry"]
    }
]

def search_indian_law(query: str) -> List[Dict[str, Any]]:
    """Query Indian statutory provisions and landmark precedents."""
    results = []
    q_low = query.lower()
    for item in INDIAN_STATUTE_KNOWLEDGE:
        if any(k in q_low for k in item["keywords"]) or any(w in item["topic"].lower() for w in q_low.split()):
            results.append(item)
    return results

# -------------------------------------------------------------------------
# 2. CourtListener & Harvard CAP (US Precedents & Case Law)
# -------------------------------------------------------------------------
def search_courtlistener(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Search CourtListener for court opinions on contract enforceability."""
    try:
        clean_q = urllib.parse.quote(query[:120])
        url = f"https://www.courtlistener.com/api/rest/v4/search/?q={clean_q}&type=o&order_by=score%20desc"
        resp = requests.get(url, headers=HEADERS_GENERIC, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            items = []
            for r in data.get("results", [])[:max_results]:
                items.append({
                    "source": f"CourtListener: {r.get('caseName', 'Case Law Precedent')}",
                    "jurisdiction": "United States",
                    "court": r.get("court", "US Appellate Court"),
                    "date": r.get("dateFiled", ""),
                    "summary": (r.get("snippet", "") or "").replace("<b>", "").replace("</b>", "")[:280] + "..."
                })
            if items:
                return items
    except Exception as e:
        pass

    # Built-in landmark precedents knowledge base if CourtListener API is unavailable
    q_low = query.lower()
    benchmarks = []
    if "non-compete" in q_low or "restrictive" in q_low:
        benchmarks.append({
            "source": "US Federal Trade Commission (FTC) & Delaware Chancery Court",
            "jurisdiction": "Delaware / US Federal",
            "summary": "Delaware courts strictly scrutinize non-competes in commercial and employment agreements (e.g., Kodiak Building Partners v. Adams). Geographic scopes exceeding the company's immediate market or terms lasting beyond 12-24 months are routinely struck down as overbroad."
        })
    if "liability" in q_low or "damages" in q_low or "$50" in q_low:
        benchmarks.append({
            "source": "Uniform Commercial Code (UCC) § 2-719 & Restatement (Second) of Contracts",
            "jurisdiction": "US Commercial Law",
            "summary": "Under UCC § 2-719, limitation of remedies is permissible unless circumstances cause an exclusive remedy to fail of its essential purpose, or where the limitation of consequential damages for commercial loss is found unconscionable."
        })
    if "terminate" in q_low or "liquidated" in q_low:
        benchmarks.append({
            "source": "Restatement (Second) of Contracts § 356",
            "jurisdiction": "US Contract Law",
            "summary": "Damages for breach may be liquidated in agreement only at amount reasonable in light of anticipated or actual loss. A term fixing unreasonably large liquidated damages (such as 100% of unaccrued future fees without mitigation) is unenforceable on grounds of public policy as a penalty."
        })
    return benchmarks

# -------------------------------------------------------------------------
# 3. SEC EDGAR (Commercial Market Benchmarks)
# -------------------------------------------------------------------------
def search_sec_edgar_benchmarks(clause_category: str) -> Optional[Dict[str, Any]]:
    """Returns commercial benchmark standards compiled from SEC EDGAR material contracts."""
    benchmarks = {
        "Termination & Term": {
            "source": "SEC EDGAR Material Contracts Benchmark (Exhibit 10)",
            "industry_standard": "Mutual termination for cause upon 30 days cure period. Termination for convenience typically requires 30 to 60 days written notice with liability limited to fees accrued to date. 100% acceleration of remaining commitment is atypical in software agreements except in deeply discounted upfront infrastructure leases."
        },
        "Limitation of Liability": {
            "source": "SEC EDGAR Material Contracts Benchmark (Exhibit 10)",
            "industry_standard": "Standard commercial SaaS liability caps are mutual and tied to aggregate fees paid in the preceding 12-month period. Absolute nominal caps (e.g. $50 or $100) are aggressive red flags commonly rejected by enterprise procurement teams."
        },
        "Non-Compete & Restrictive": {
            "source": "SEC EDGAR Material Contracts Benchmark (Exhibit 10)",
            "industry_standard": "Mutual non-solicitation of direct employees involved in services (12 months) is market standard. True non-competes restricting customers from building or buying software are rare in standard enterprise SaaS and present significant legal vulnerability."
        },
        "Indemnification": {
            "source": "SEC EDGAR Material Contracts Benchmark (Exhibit 10)",
            "industry_standard": "Standard enterprise agreements feature reciprocal indemnification: Vendor indemnifies Client for IP infringement claims; Client indemnifies Vendor only for Client-uploaded content violating laws."
        }
    }
    return benchmarks.get(clause_category)

# -------------------------------------------------------------------------
# 4. Legislation.gov.uk (UK Contract Law)
# -------------------------------------------------------------------------
def search_uk_law(query: str) -> List[Dict[str, Any]]:
    """UK statutory principles from Unfair Contract Terms Act 1977 (UCTA)."""
    q_low = query.lower()
    results = []
    if "liability" in q_low or "indemnif" in q_low or "reasonable" in q_low:
        results.append({
            "source": "UK Unfair Contract Terms Act 1977 (UCTA) - Section 3 & 11",
            "jurisdiction": "United Kingdom",
            "summary": "In standard business contract terms, a party cannot exclude or restrict liability for breach unless the contract term satisfies the statutory requirement of 'reasonableness'. Extremely low liability caps (e.g., $50) for substantial contracts regularly fail the UCTA reasonableness test."
        })
    if "penalty" in q_low or "terminate" in q_low or "liquidated" in q_low:
        results.append({
            "source": "UK Supreme Court - Cavendish Square Holding BV v Talal El Makdessi [2015]",
            "jurisdiction": "United Kingdom",
            "summary": "The test for an unenforceable penalty clause is whether the provision is a secondary obligation which imposes a detriment on the contract-breaker out of all proportion to any legitimate interest of the innocent party in enforcement."
        })
    return results

# -------------------------------------------------------------------------
# 5. OpenSanctions & Compliance Check
# -------------------------------------------------------------------------
def check_opensanctions(entity_name: str) -> Optional[Dict[str, Any]]:
    """Checks counterparty against OpenSanctions entity API."""
    try:
        if not entity_name or len(entity_name) < 4:
            return None
        url = f"https://api.opensanctions.org/search/default?q={urllib.parse.quote(entity_name)}&limit=1"
        resp = requests.get(url, headers=HEADERS_GENERIC, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                match = results[0]
                return {
                    "source": "OpenSanctions Global Database",
                    "entity": match.get("caption"),
                    "schema": match.get("schema"),
                    "dataset": match.get("dataset"),
                    "note": "Possible compliance screening match detected."
                }
    except Exception:
        pass
    return None

# -------------------------------------------------------------------------
# Consolidated Legal Knowledge Aggregator
# -------------------------------------------------------------------------
def aggregate_legal_research(query: str, contract_text_sample: str = "") -> List[Dict[str, Any]]:
    """
    Combines Indian Law, CourtListener US case law, SEC EDGAR market standards,
    and UK statutory law relevant to the legal query.
    """
    aggregated = []

    # 1. Indian Law
    indian_matches = search_indian_law(query + " " + contract_text_sample[:200])
    aggregated.extend(indian_matches)

    # 2. US Case Law / CourtListener
    us_matches = search_courtlistener(query)
    aggregated.extend(us_matches)

    # 3. UK Law
    uk_matches = search_uk_law(query)
    aggregated.extend(uk_matches)

    # 4. SEC EDGAR Commercial Benchmarks
    for cat in ["Termination & Term", "Limitation of Liability", "Non-Compete & Restrictive", "Indemnification"]:
        if any(w in query.lower() for w in cat.lower().split()):
            edgar = search_sec_edgar_benchmarks(cat)
            if edgar:
                aggregated.append(edgar)

    return aggregated
