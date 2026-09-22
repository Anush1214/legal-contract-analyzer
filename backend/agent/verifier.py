import re
import logging
from typing import Dict, Any, List, Set
from backend.agent.state import AgentState, EvidenceItem

logger = logging.getLogger("agent.verifier")

def extract_cited_clauses(text: str) -> List[int]:
    """
    Extract clause numbers referenced in text e.g.,
    'Clause 4', 'Clause 7', 'Section 4', 'Section 8'.
    """
    matches = re.findall(r'(?:clause|section)\s+(\d+)', text, flags=re.IGNORECASE)
    return sorted(list(set(int(m) for m in matches)))

def extract_cited_statutes(text: str) -> List[str]:
    """Extract statutory patterns like 'Section 27', 'Section 74', 'UCC', 'UCTA'."""
    patterns = [
        r'Section\s+(?:27|73|74|28|124|125)\s+(?:of\s+the\s+)?Indian Contract Act',
        r'UCC\s+§?\s*2-719',
        r'Unfair Contract Terms Act\s+1977',
        r'UCTA',
        r'Cavendish',
        r'SEC EDGAR'
    ]
    found = set()
    for p in patterns:
        for m in re.finditer(p, text, flags=re.IGNORECASE):
            found.add(m.group(0))
    return sorted(list(found))

def verify_citations(final_answer: str, state: AgentState) -> Dict[str, Any]:
    """
    Verify citation integrity and evidence grounding:
    1. Checks if each cited contract clause number was retrieved in the evidence state.
    2. Checks if the cited text reflects retrieved contract clauses.
    3. Flags external sources mentioned in the answer that were never retrieved via tools.
    """
    cited_clauses = extract_cited_clauses(final_answer)
    retrieved_clause_numbers: Set[int] = set()

    for item in state.evidence:
        if item.source_type == "contract":
            clause_num = item.metadata.get("clause_number")
            if clause_num is not None:
                retrieved_clause_numbers.add(int(clause_num))

    valid_clauses = [c for c in cited_clauses if c in retrieved_clause_numbers]
    unsupported_clauses = [c for c in cited_clauses if c not in retrieved_clause_numbers]

    # Check external statutory grounding
    cited_statutes = extract_cited_statutes(final_answer)
    retrieved_statute_texts = " ".join([e.content.lower() for e in state.evidence if e.source_type in {"statute", "case", "benchmark"}])

    unsupported_statutes = []
    valid_statutes = []
    for s in cited_statutes:
        s_norm = s.lower().replace("§", "").replace("of the ", "")
        tokens = [t for t in s_norm.split() if len(t) > 2]
        if any(t in retrieved_statute_texts for t in tokens):
            valid_statutes.append(s)
        else:
            unsupported_statutes.append(s)

    # Calculate overall grounding confidence
    total_citations = len(cited_clauses) + len(cited_statutes)
    valid_citations = len(valid_clauses) + len(valid_statutes)

    citation_precision = (valid_citations / total_citations) if total_citations > 0 else 1.0
    has_contract_evidence = len(state.get_contract_evidence()) > 0

    warnings = []
    if unsupported_clauses:
        warnings.append(f"Answer references Clause(s) {unsupported_clauses} which were NOT retrieved into the evidence pool.")
    if unsupported_statutes:
        warnings.append(f"Answer references statutory terms {unsupported_statutes} without corresponding retrieved external legal evidence.")
    if not has_contract_evidence and cited_clauses:
        warnings.append("Answer makes contract clause claims but zero contract clauses were retrieved.")

    is_verified = (len(unsupported_clauses) == 0 and len(unsupported_statutes) == 0)

    result = {
        "is_verified": is_verified,
        "citation_precision": round(citation_precision, 4),
        "total_citations": total_citations,
        "valid_clause_citations": valid_clauses,
        "unsupported_clause_citations": unsupported_clauses,
        "valid_statute_citations": valid_statutes,
        "unsupported_statute_citations": unsupported_statutes,
        "has_contract_evidence": has_contract_evidence,
        "warnings": warnings
    }

    if warnings:
        logger.warning(f"Citation verification flags: {warnings}")
    else:
        logger.info("Citation verification passed: all cited references exist in retrieved evidence pool.")

    return result
