import pytest
from backend.agent.tool_registry import is_tool_allowed, execute_tool
from backend.agent.state import AgentState, EvidenceItem
from backend.agent.verifier import verify_citations, extract_cited_clauses

def test_tool_whitelist_security():
    assert is_tool_allowed("search_contract") is True
    assert is_tool_allowed("get_clause") is True
    assert is_tool_allowed("search_statutes") is True
    assert is_tool_allowed("search_cases") is True
    assert is_tool_allowed("compare_contracts") is True

    # Unknown or arbitrary function execution must be rejected
    assert is_tool_allowed("os.system") is False
    assert is_tool_allowed("subprocess.Popen") is False
    assert is_tool_allowed("arbitrary_code") is False

    exec_res = execute_tool("forbidden_tool", {})
    assert "error" in exec_res
    assert "SECURITY ALERT" in exec_res["error"]

def test_extract_cited_clauses():
    text = "Under Clause 4 and Section 7, the vendor liability is capped, while Clause 9 imposes non-compete."
    cited = extract_cited_clauses(text)
    assert cited == [4, 7, 9]

def test_citation_verifier_success():
    state = AgentState(user_query="Can customer terminate?", contract_name="Agreement.pdf")
    state.add_evidence(
        EvidenceItem(
            source_type="contract",
            source_identifier="Clause 4",
            title="Termination",
            content="Customer may not terminate early.",
            contract_name="Agreement.pdf",
            metadata={"clause_number": 4}
        )
    )

    answer = "According to Clause 4, customer cannot terminate early."
    verif = verify_citations(answer, state)
    assert verif["is_verified"] is True
    assert verif["valid_clause_citations"] == [4]
    assert len(verif["unsupported_clause_citations"]) == 0

def test_citation_verifier_flags_hallucination():
    state = AgentState(user_query="Can customer terminate?", contract_name="Agreement.pdf")
    # State has only clause 4
    state.add_evidence(
        EvidenceItem(
            source_type="contract",
            source_identifier="Clause 4",
            title="Termination",
            content="Customer may not terminate early.",
            contract_name="Agreement.pdf",
            metadata={"clause_number": 4}
        )
    )

    # Answer hallucinates Clause 12
    answer = "Under Clause 4 and Clause 12, customer must pay damages."
    verif = verify_citations(answer, state)
    assert verif["is_verified"] is False
    assert 12 in verif["unsupported_clause_citations"]
    assert len(verif["warnings"]) > 0
