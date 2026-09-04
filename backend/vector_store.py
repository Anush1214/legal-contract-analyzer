import hashlib
import math
from typing import List, Dict, Any, Optional
import chromadb
from backend.config import get_gemini_api_key, CHROMA_PERSIST_DIR, EMBEDDING_MODEL
from backend.clause_parser import extract_clauses

# Initialize persistent Chroma client
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
contract_collection = chroma_client.get_or_create_collection(
    name="contracts",
    metadata={"hnsw:space": "cosine"}
)

def _generate_fallback_embedding(text: str, dim: int = 1536) -> List[float]:
    """
    Deterministic normalized vector for indexing and cosine similarity.
    """
    vec = [0.0] * dim
    words = text.lower().split()
    for i, word in enumerate(words):
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        weight = 1.0 / (1.0 + math.log(i + 1))
        vec[idx] += weight
        vec[(idx + 31) % dim] += 0.5 * weight
        
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]

def get_embedding(text: str) -> List[float]:
    """
    Generate embedding using Google GenAI or semantic fallback.
    """
    api_key = get_gemini_api_key()
    if api_key and not api_key.startswith("demo_"):
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text[:4000]
            )
            if hasattr(result, "embeddings") and result.embeddings:
                return result.embeddings[0].values
        except Exception as e:
            # Fallback to local semantic vector
            pass
            
    return _generate_fallback_embedding(text)

def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Batch generate embeddings."""
    return [get_embedding(t) for t in texts]

def index_contract(pdf_bytes: bytes, contract_name: str) -> Dict[str, Any]:
    """
    Index a legal contract by its clauses into ChromaDB.
    """
    clauses = extract_clauses(pdf_bytes, contract_name)
    if not clauses:
        raise ValueError(f"No clauses could be extracted from {contract_name}. Verify the PDF contains selectable text.")

    # Remove existing clauses if re-indexing
    existing = contract_collection.get(where={"contract": contract_name})
    if existing and existing.get("ids"):
        contract_collection.delete(ids=existing["ids"])

    texts = [c["text"] for c in clauses]
    embeddings = get_batch_embeddings(texts)

    ids = [f"{contract_name}_clause_{i}" for i in range(len(clauses))]
    metadatas = [
        {
            "contract": contract_name,
            "clause_number": c["clause_number"],
            "title": c.get("title", f"Clause {c['clause_number']}"),
            "category": c.get("category", "General"),
            "char_count": c.get("char_count", len(c["text"])),
            "page": c.get("page", 1)
        }
        for c in clauses
    ]

    contract_collection.add(
        documents=texts,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas
    )

    print(f"Index complete: {contract_name} ({len(clauses)} clauses indexed in ChromaDB)")
    return {
        "contract": contract_name,
        "total_clauses": len(clauses),
        "clauses": clauses
    }

def query_clauses(query: str, contract_name: Optional[str] = None, n_results: int = 4) -> Dict[str, Any]:
    """Search clauses by semantic similarity in ChromaDB."""
    q_embedding = get_embedding(query)
    where_filter = {"contract": contract_name} if contract_name else None

    count = contract_collection.count()
    if count == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    actual_n = min(n_results, count)
    results = contract_collection.query(
        query_embeddings=[q_embedding],
        n_results=actual_n,
        where=where_filter
    )
    return results

def list_indexed_contracts() -> List[Dict[str, Any]]:
    """Return summary of all indexed contracts."""
    all_data = contract_collection.get()
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

def get_contract_clauses(contract_name: str) -> List[Dict[str, Any]]:
    """Get all clauses for a contract."""
    results = contract_collection.get(
        where={"contract": contract_name},
        include=["documents", "metadatas"]
    )
    if not results or not results.get("ids"):
        return []

    clauses = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        clauses.append({
            "clause_number": meta.get("clause_number", 0),
            "title": meta.get("title", ""),
            "category": meta.get("category", "General"),
            "text": doc,
            "page": meta.get("page", 1),
            "char_count": meta.get("char_count", len(doc))
        })
    return sorted(clauses, key=lambda c: c["clause_number"])

def delete_contract(contract_name: str) -> bool:
    """Delete a contract from ChromaDB."""
    existing = contract_collection.get(where={"contract": contract_name})
    if existing and existing.get("ids"):
        contract_collection.delete(ids=existing["ids"])
        return True
    return False
