import logging
from typing import List, Dict, Any, Optional
import chromadb
from backend.config import CHROMA_PERSIST_DIR, RAG_TOP_K, RAG_MIN_RELEVANCE_SCORE
from backend.retrieval.base import BaseRetriever, RetrievalResult
from backend.retrieval.embedding_service import get_embedding, get_batch_embeddings

logger = logging.getLogger("retrieval.dense")

class DenseRetriever(BaseRetriever):
    """
    Dense semantic retriever backed by ChromaDB and Gemini embeddings.
    Cosine distance d in ChromaDB is converted to similarity: S = max(0.0, 1.0 - d).
    """

    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR, collection_name: str = "contracts"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def index_clauses(self, contract_name: str, clauses: List[Dict[str, Any]]) -> None:
        """Index extracted clauses into ChromaDB."""
        if not clauses:
            raise ValueError(f"No clauses provided for indexing contract: {contract_name}")

        # Remove existing clauses for this contract to prevent duplicate drift
        self.delete_contract(contract_name)

        texts = [c["text"] for c in clauses]
        embeddings = get_batch_embeddings(texts)
        ids = [f"{contract_name}_clause_{c.get('clause_number', i)}" for i, c in enumerate(clauses)]
        metadatas = [
            {
                "contract": contract_name,
                "clause_number": c.get("clause_number", i + 1),
                "title": c.get("title", f"Clause {c.get('clause_number', i + 1)}"),
                "category": c.get("category", "General"),
                "char_count": c.get("char_count", len(c["text"])),
                "page": c.get("page", 1)
            }
            for i, c in enumerate(clauses)
        ]

        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"Dense index complete: {contract_name} ({len(clauses)} clauses)")

    def retrieve(
        self,
        query: str,
        contract_name: Optional[str] = None,
        top_k: int = RAG_TOP_K,
        min_score: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Execute dense vector search against ChromaDB.
        Returns normalized RetrievalResult list sorted by similarity descending.
        """
        total_count = self.collection.count()
        if total_count == 0:
            return []

        q_embedding = get_embedding(query)
        where_filter = {"contract": contract_name} if contract_name else None
        actual_k = min(top_k, total_count)

        res = self.collection.query(
            query_embeddings=[q_embedding],
            n_results=actual_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]
        ids = res.get("ids", [[]])[0]

        results: List[RetrievalResult] = []
        for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
            # ChromaDB cosine distance d is in [0, 2], where d = 1 - cosine_similarity.
            # Convert to similarity score S in [0, 1]: S = max(0.0, 1.0 - d)
            similarity = max(0.0, 1.0 - float(dist))

            if min_score is not None and similarity < min_score:
                continue

            results.append(
                RetrievalResult(
                    contract_name=meta.get("contract", contract_name or "Unknown"),
                    clause_id=doc_id,
                    clause_number=meta.get("clause_number", 0),
                    title=meta.get("title", ""),
                    category=meta.get("category", "General"),
                    text=doc,
                    page=meta.get("page", 1),
                    retrieval_score=similarity,
                    retrieval_method="dense",
                    metadata={"cosine_distance": float(dist)}
                )
            )

        # Chroma returns results sorted by distance ascending (similarity descending)
        return results

    def delete_contract(self, contract_name: str) -> bool:
        """Remove all clauses matching contract_name from ChromaDB."""
        existing = self.collection.get(where={"contract": contract_name})
        if existing and existing.get("ids"):
            self.collection.delete(ids=existing["ids"])
            logger.info(f"Deleted {len(existing['ids'])} clauses for {contract_name} from dense store")
            return True
        return False

    def get_all_clauses(self, contract_name: str) -> List[Dict[str, Any]]:
        """Fetch all indexed clauses for contract_name sorted by clause_number."""
        existing = self.collection.get(
            where={"contract": contract_name},
            include=["documents", "metadatas"]
        )
        if not existing or not existing.get("ids"):
            return []

        clauses = []
        for doc_id, doc, meta in zip(existing["ids"], existing["documents"], existing["metadatas"]):
            clauses.append({
                "clause_id": doc_id,
                "clause_number": meta.get("clause_number", 0),
                "title": meta.get("title", ""),
                "category": meta.get("category", "General"),
                "text": doc,
                "page": meta.get("page", 1),
                "char_count": meta.get("char_count", len(doc)),
                "contract": meta.get("contract", contract_name)
            })
        return sorted(clauses, key=lambda c: c["clause_number"])

    def list_contracts(self) -> List[Dict[str, Any]]:
        """Return summary of all contracts currently indexed."""
        all_data = self.collection.get(include=["documents", "metadatas"])
        if not all_data or not all_data.get("metadatas"):
            return []

        contracts_map = {}
        for meta, doc in zip(all_data["metadatas"], all_data["documents"]):
            name = meta.get("contract", "Unknown")
            if name not in contracts_map:
                contracts_map[name] = {
                    "name": name,
                    "clause_count": 0,
                    "categories": set(),
                    "sample_preview": doc[:150] + "..."
                }
            contracts_map[name]["clause_count"] += 1
            contracts_map[name]["categories"].add(meta.get("category", "General"))

        result = []
        for name, data in contracts_map.items():
            result.append({
                "name": name,
                "clause_count": data["clause_count"],
                "categories": sorted(list(data["categories"])),
                "sample_preview": data["sample_preview"]
            })
        return sorted(result, key=lambda x: x["name"])
