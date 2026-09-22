import re
import math
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from backend.retrieval.base import BaseRetriever, RetrievalResult

logger = logging.getLogger("retrieval.bm25")

# Standard stopwords that do NOT alter legal obligations or rights
# Notice: 'not', 'no', 'without', 'except', 'unless', 'sole' are intentionally EXCLUDED
# from removal because they invert legal obligations!
LEGAL_SAFE_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "by", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "this", "that", "these", "those",
    "it", "its", "their", "theirs", "such", "said", "herein", "therein"
}

def tokenize_legal_text(text: str) -> List[str]:
    """
    Legal-aware tokenizer:
    - Normalizes case.
    - Preserves statutory symbols (§27), percentages (100%), monetary caps ($50),
      and hyphenated terms (non-compete, non-disclosure).
    - Filters low-entropy general stopwords while preserving negation and scope operators.
    """
    if not text:
        return []

    # Preserve symbols like §27 -> section_27, $50 -> usd_50, 100% -> 100_percent
    clean = re.sub(r'§\s*(\d+)', r'section_\1', text)
    clean = re.sub(r'\$(\d+)', r'usd_\1', clean)
    clean = re.sub(r'(\d+)%', r'\1_percent', clean)

    # Extract alphanumeric words and hyphenated compound terms
    tokens = re.findall(r'[a-zA-Z0-9_\-]+', clean.lower())

    # Filter non-informative stopwords
    filtered = [t for t in tokens if len(t) > 1 and t not in LEGAL_SAFE_STOPWORDS]
    return filtered

class BM25Retriever(BaseRetriever):
    """
    BM25 lexical retriever tailored for exact legal terms and statutory citations.
    Maintains cached BM25 indices per contract to avoid re-indexing overhead on each query.
    """

    def __init__(self):
        # Map: contract_name -> {"bm25": BM25Okapi, "clauses": List[Dict], "tokenized_corpus": List[List[str]]}
        self.indices: Dict[str, Dict[str, Any]] = {}

    def index_clauses(self, contract_name: str, clauses: List[Dict[str, Any]]) -> None:
        """Build and cache a BM25 index for the clauses of contract_name."""
        if not clauses:
            logger.warning(f"No clauses to index for BM25: {contract_name}")
            return

        tokenized_corpus = [tokenize_legal_text(c["text"]) for c in clauses]
        bm25_model = BM25Okapi(tokenized_corpus)

        self.indices[contract_name] = {
            "bm25": bm25_model,
            "clauses": clauses,
            "tokenized_corpus": tokenized_corpus
        }
        logger.info(f"BM25 index built and cached for '{contract_name}' ({len(clauses)} clauses)")

    def retrieve(
        self,
        query: str,
        contract_name: Optional[str] = None,
        top_k: int = 4
    ) -> List[RetrievalResult]:
        """
        Execute BM25 lexical search.
        If contract_name is given, searches within that contract.
        If contract_name is None, searches across all indexed contracts.
        """
        query_tokens = tokenize_legal_text(query)
        if not query_tokens:
            return []

        target_contracts = [contract_name] if contract_name and contract_name in self.indices else list(self.indices.keys())
        if not target_contracts:
            return []

        candidate_records = []
        for c_name in target_contracts:
            index_data = self.indices.get(c_name)
            if not index_data:
                continue

            bm25 = index_data["bm25"]
            clauses = index_data["clauses"]
            scores = bm25.get_scores(query_tokens)

            for score, clause in zip(scores, clauses):
                if score > 0.0:
                    candidate_records.append((float(score), c_name, clause))

        if not candidate_records:
            return []

        # Sort by raw BM25 score descending
        candidate_records.sort(key=lambda x: x[0], reverse=True)

        # Min-max or soft normalizer to produce [0, 1] retrieval_score
        max_score = candidate_records[0][0]
        results: List[RetrievalResult] = []

        for score, c_name, clause in candidate_records[:top_k]:
            normalized_score = score / max_score if max_score > 0 else 0.0
            doc_id = f"{c_name}_clause_{clause.get('clause_number', 0)}"

            results.append(
                RetrievalResult(
                    contract_name=c_name,
                    clause_id=doc_id,
                    clause_number=clause.get("clause_number", 0),
                    title=clause.get("title", f"Clause {clause.get('clause_number', 0)}"),
                    category=clause.get("category", "General"),
                    text=clause["text"],
                    page=clause.get("page", 1),
                    retrieval_score=normalized_score,
                    retrieval_method="bm25",
                    metadata={"bm25_raw_score": score}
                )
            )

        return results

    def delete_contract(self, contract_name: str) -> bool:
        """Remove cached BM25 index for contract_name."""
        if contract_name in self.indices:
            del self.indices[contract_name]
            logger.info(f"Deleted BM25 index for {contract_name}")
            return True
        return False
