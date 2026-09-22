"""
Prompt construction and context assembly for grounded legal analysis.
Implements prompt injection defense using strict delimiter boundaries.
"""

from typing import List, Dict, Any, Optional
from backend.retrieval.base import RetrievalResult

SYSTEM_DIRECTIVE = """You are an expert international corporate legal assistant assisting in contract evaluation.
Your principles:
1. Ground your answers strictly in the provided CONTRACT CLAUSES and EXTERNAL LEGAL REFERENCES.
2. If the retrieved evidence does not contain sufficient information to answer the question, clearly state that evidence is insufficient rather than speculating or hallucinating.
3. Explicitly cite the specific clause numbers and titles you rely upon.
4. Explain legal ramifications, risks, and commercial norms in clear, professional English.
5. Format answers with clean markdown headings, bold highlights, and bullet points."""

def build_grounded_rag_prompt(
    question: str,
    contract_name: str,
    retrieved_clauses: List[RetrievalResult],
    external_legal_context: Optional[str] = None
) -> str:
    """
    Construct a structured RAG prompt separating retrieved evidence from system instructions.
    Uses XML-style tags to isolate untrusted contract text and prevent prompt injection.
    """
    clause_blocks = []
    for c in retrieved_clauses:
        clause_blocks.append(
            f"<clause id=\"{c.clause_id}\" number=\"{c.clause_number}\" title=\"{c.title}\" category=\"{c.category}\" page=\"{c.page}\" score=\"{c.retrieval_score:.4f}\">\n"
            f"{c.text.strip()}\n"
            f"</clause>"
        )
    formatted_clauses = "\n\n".join(clause_blocks) if clause_blocks else "<no_clauses_retrieved />"

    external_context_block = f"<external_statutes_and_benchmarks>\n{external_legal_context.strip()}\n</external_statutes_and_benchmarks>" if external_legal_context else ""

    prompt = f"""Target Contract: {contract_name}

<retrieved_contract_evidence>
{formatted_clauses}
</retrieved_contract_evidence>

{external_context_block}

<user_inquiry>
{question}
</user_inquiry>

INSTRUCTIONS:
1. Answer the user's inquiry based strictly on the retrieved contract evidence above.
2. Cite the specific Clause Number and Title for every claim made.
3. Highlight any asymmetric liability, aggressive termination penalties, or non-compete risks if relevant.
4. If the retrieved clauses do not contain the answer, explicitly state: "The retrieved contract evidence does not specify terms addressing this question."
"""
    return prompt
