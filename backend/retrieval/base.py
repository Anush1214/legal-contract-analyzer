from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class RetrievalResult:
    """
    Standardized result structure shared across V1, V2, and V3 retrieval pipelines.
    Enables fair cross-architecture evaluation and uniform presentation.
    """
    contract_name: str
    clause_id: str
    clause_number: int
    title: str
    category: str
    text: str
    page: int = 1
    retrieval_score: float = 0.0
    retrieval_method: str = "dense"
    rerank_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "clause_id": self.clause_id,
            "clause_number": self.clause_number,
            "title": self.title,
            "category": self.category,
            "text": self.text,
            "page": self.page,
            "retrieval_score": round(self.retrieval_score, 4),
            "retrieval_method": self.retrieval_method,
            "rerank_score": round(self.rerank_score, 4) if self.rerank_score is not None else None,
            "metadata": self.metadata
        }

class BaseRetriever(ABC):
    """Abstract interface for all contract clause retrievers."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        contract_name: Optional[str] = None,
        top_k: int = 4
    ) -> List[RetrievalResult]:
        """Retrieve top_k matching clauses for query, optionally filtered by contract_name."""
        pass

    @abstractmethod
    def index_clauses(self, contract_name: str, clauses: List[Dict[str, Any]]) -> None:
        """Index a list of extracted clauses for contract_name."""
        pass

    @abstractmethod
    def delete_contract(self, contract_name: str) -> bool:
        """Remove all indexed clauses for contract_name."""
        pass
