import pytest
from backend.clause_parser import detect_clause_category, extract_clause_title

def test_detect_clause_category():
    assert detect_clause_category("The agreement shall terminate upon 30 days notice") == "Termination & Term"
    assert detect_clause_category("Customer shall not compete or solicit employees") == "Non-Compete & Restrictive"
    assert detect_clause_category("In no event shall damages exceed $50") == "Limitation of Liability"
    assert detect_clause_category("Customer agrees to indemnify and hold harmless vendor") == "Indemnification"
    assert detect_clause_category("Vendor retains all intellectual property and patent rights") == "Intellectual Property"
    assert detect_clause_category("Payment shall be Net 30 days upon invoice") == "Fees & Payment"
    assert detect_clause_category("Arbitration shall take place in Delaware under governing law") == "Governing Law & Disputes"
    assert detect_clause_category("Miscellaneous provisions and severability") == "General & Boilerplate"

def test_extract_clause_title():
    text = "Section 4. Term and Termination of Agreement.\nCustomer may terminate on written notice."
    title = extract_clause_title(text)
    assert title.startswith("Section 4")

def test_extract_clause_title_empty():
    assert extract_clause_title("") == "Clause"
