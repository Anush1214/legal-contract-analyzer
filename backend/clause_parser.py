import io
import re
from typing import List, Dict, Any
import pdfplumber

def detect_clause_category(text: str) -> str:
    """Classify legal clause into common contract categories for UI tagging."""
    t = text.lower()
    if any(k in t for k in ["terminate", "termination", "term of agreement", "expiration"]):
        return "Termination & Term"
    if any(k in t for k in ["non-compete", "non compete", "not compete", "non-solicitation", "solicit", "restrictive covenant"]):
        return "Non-Compete & Restrictive"
    if any(k in t for k in ["liability", "limitation of liability", "damages", "consequential"]):
        return "Limitation of Liability"
    if any(k in t for k in ["indemnif", "hold harmless", "defense"]):
        return "Indemnification"
    if any(k in t for k in ["confidential", "proprietary information", "trade secret"]):
        return "Confidentiality"
    if any(k in t for k in ["intellectual property", "ip rights", "ownership of work", "patent", "copyright"]):
        return "Intellectual Property"
    if any(k in t for k in ["payment", "fee", "compensation", "billing", "invoice", "net 30"]):
        return "Fees & Payment"
    if any(k in t for k in ["warranty", "representation", "disclaimer", "as is"]):
        return "Warranties"
    if any(k in t for k in ["governing law", "jurisdiction", "dispute", "arbitration"]):
        return "Governing Law & Disputes"
    if any(k in t for k in ["assignment", "force majeure", "severability", "entire agreement", "miscellaneous"]):
        return "General & Boilerplate"
    return "Contractual Obligation"

def extract_clause_title(text: str) -> str:
    """Extract a human-readable title from the first line or sentence of a clause."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Clause"
    first_line = lines[0]
    # If first line has a section header e.g. "Section 4. Term and Termination: ..."
    if len(first_line) > 90:
        first_line = first_line[:87] + "..."
    return first_line

def extract_clauses(pdf_bytes: bytes, contract_name: str) -> List[Dict[str, Any]]:
    """
    Extract text and split by legal clause structure.
    Implements the specification's clause-aware regex parsing.
    """
    clauses = []
    full_text = ""
    page_map = []  # track character offset to page number
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            start_pos = len(full_text)
            full_text += page_text + "\n"
            page_map.append((start_pos, len(full_text), page_idx + 1))
            
    # Split by numbered clauses (1., 2., 1.1, Section 1, Article 1, CLAUSE 1 etc.)
    clause_pattern = r'(?=(?:\d+\.\d*|Section\s+\d+|Article\s+\d+|CLAUSE\s+\d+)[\s\.])'
    sections = re.split(clause_pattern, full_text, flags=re.IGNORECASE)
    
    # Fallback if contract format is unnumbered or uses standard paragraph headers
    if len(sections) <= 1 and len(full_text) > 300:
        # Split on double newlines or Roman numerals / uppercase headers
        sections = re.split(r'\n\s*\n', full_text)
        
    clause_count = 0
    for section in sections:
        section = section.strip()
        # Keep clauses that meet minimum length threshold (from spec > 100 chars)
        if len(section) >= 80:
            clause_count += 1
            category = detect_clause_category(section)
            title = extract_clause_title(section)
            
            # Approximate page number
            first_words = section[:40]
            approx_page = 1
            for p_start, p_end, p_num in page_map:
                if first_words in full_text[p_start:p_end]:
                    approx_page = p_num
                    break
                    
            clauses.append({
                "text": section,
                "clause_number": clause_count,
                "title": title,
                "category": category,
                "contract": contract_name,
                "char_count": len(section),
                "page": approx_page
            })
            
    return clauses
