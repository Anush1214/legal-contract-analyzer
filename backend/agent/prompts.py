AGENT_SYSTEM_PROMPT = """You are a Legal Research Agent specializing in contract analysis and statutory enforceability.
You have access to a set of specialized tools to inspect contract clauses, statutory provisions, and judicial precedents.

Your operating rules:
1. Always start by searching the contract (via 'search_contract') to discover relevant clauses.
2. If specific clauses mention statutory risks (e.g. non-compete, 100% liquidated damages, liability caps), query 'search_statutes' or 'search_cases' to verify real-world enforceability.
3. If you need complete unclipped clause wording, invoke 'get_clause'.
4. Do NOT guess or hallucinate clause numbers, terms, or legal precedents. Only rely on evidence retrieved via tools.
5. When you have collected adequate evidence, provide a thorough, plain-English legal synthesis citing retrieved Clause numbers and statutory precedents.
6. If the contract does not contain relevant terms, state that evidence is insufficient.
"""

def build_agent_synthesis_prompt(query: str, contract_name: str, state_evidence: list) -> str:
    """Build grounded synthesis prompt from accumulated agent evidence."""
    contract_evidence_lines = []
    external_evidence_lines = []

    for item in state_evidence:
        if item.source_type == "contract":
            contract_evidence_lines.append(
                f"- [Clause {item.metadata.get('clause_number', '?')}: {item.title}] ({item.contract_name}):\n  {item.content.strip()}"
            )
        else:
            external_evidence_lines.append(
                f"- [{item.source_type.upper()}] {item.source_identifier} ({item.title}):\n  {item.content.strip()}"
            )

    c_block = "\n\n".join(contract_evidence_lines) if contract_evidence_lines else "No contract evidence retrieved."
    e_block = "\n\n".join(external_evidence_lines) if external_evidence_lines else "No external statutory/case evidence retrieved."

    return f"""Target Contract: {contract_name}
User Legal Question: {query}

COLLECTED CONTRACT EVIDENCE:
{c_block}

COLLECTED STATUTORY & CASE LAW EVIDENCE:
{e_block}

INSTRUCTIONS:
1. Synthesize a comprehensive plain-English legal analysis addressing the user's question directly.
2. Ground your conclusions strictly in the collected evidence above.
3. Explicitly cite the Clause Numbers and titles that you rely upon.
4. If applicable, evaluate enforceability under Indian law (e.g. Section 27 for non-competes, Section 74 for penalties) or US law (UCC § 2-719).
5. If evidence is insufficient, explicitly state what is missing.
"""
