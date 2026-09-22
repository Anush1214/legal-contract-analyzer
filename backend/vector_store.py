"""
Vector Store and Retrieval Facade.
Maintains backward compatibility with legacy endpoints while delegating to the
modular retrieval layer (DenseRetriever, BM25Retriever, HybridRetriever).
"""

from typing import List, Dict, Any, Optional
from backend.clause_parser import extract_clauses
from backend.retrieval.dense import DenseRetriever
from backend.retrieval.bm25 import BM25Retriever
from backend.retrieval.hybrid import HybridRetriever
from backend.retrieval.embedding_service import (
    get_embedding,
    get_batch_embeddings,
    get_embedding_status
)

# Global retriever instances
dense_retriever = DenseRetriever()
bm25_retriever = BM25Retriever()
hybrid_retriever = HybridRetriever(
    dense_retriever=dense_retriever,
    bm25_retriever=bm25_retriever
)

# Backward-compatible references
chroma_client = dense_retriever.client
contract_collection = dense_retriever.collection

def index_contract(pdf_bytes: bytes, contract_name: str) -> Dict[str, Any]:
    """
    Extract clauses from contract PDF and index them across both Dense (ChromaDB)
    and Lexical (BM25) stores.
    """
    clauses = extract_clauses(pdf_bytes, contract_name)
    if not clauses:
        raise ValueError(f"No clauses could be extracted from {contract_name}. Verify the PDF contains selectable text.")

    # Index in dense store
    dense_retriever.index_clauses(contract_name, clauses)
    # Index in BM25 store
    bm25_retriever.index_clauses(contract_name, clauses)

    return {
        "contract": contract_name,
        "total_clauses": len(clauses),
        "clauses": clauses
    }

def query_clauses(query: str, contract_name: Optional[str] = None, n_results: int = 4) -> Dict[str, Any]:
    """
    Search clauses by semantic similarity in ChromaDB.
    Returns format compatible with legacy callers: {"documents": [...], "metadatas": [...], "distances": [...]}
    """
    q_embedding = get_embedding(query)
    where_filter = {"contract": contract_name} if contract_name else None

    count = contract_collection.count()
    if count == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

    actual_n = min(n_results, count)
    results = contract_collection.query(
        query_embeddings=[q_embedding],
        n_results=actual_n,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    return results

def list_indexed_contracts() -> List[Dict[str, Any]]:
    """Return summary of all indexed contracts."""
    return dense_retriever.list_contracts()

def get_contract_clauses(contract_name: str) -> List[Dict[str, Any]]:
    """Get all clauses for a contract."""
    return dense_retriever.get_all_clauses(contract_name)

def delete_contract(contract_name: str) -> bool:
    """Delete a contract from ChromaDB and BM25 index."""
    dense_deleted = dense_retriever.delete_contract(contract_name)
    bm25_deleted = bm25_retriever.delete_contract(contract_name)
    return dense_deleted or bm25_deleted
