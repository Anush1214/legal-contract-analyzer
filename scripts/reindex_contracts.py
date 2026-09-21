import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import UPLOAD_DIR, SAMPLE_DIR, EMBEDDING_MODEL, EMBEDDING_DIM
from backend.clause_parser import extract_clauses
from backend.sample_contracts import ensure_sample_contracts
from backend.retrieval.dense import DenseRetriever
from backend.retrieval.bm25 import BM25Retriever
from backend.retrieval.embedding_service import get_embedding_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reindex")

def reindex_all():
    """
    Safely rebuild vector index in ChromaDB and BM25 index from scratch.
    Ensures that vector dimensionality and embedding model match current config.
    """
    logger.info("=== REINDEXING CONTRACT REPOSITORY ===")
    status = get_embedding_status()
    logger.info(f"Target Embedding Model: {status['embedding_model']} (Dimension: {status['embedding_dimension']})")
    logger.info(f"Active Retrieval Mode: {status['mode']}")

    # 1. Initialize retrievers
    dense = DenseRetriever()
    bm25 = BM25Retriever()

    # 2. Recreate / clear collection
    logger.info(f"Clearing ChromaDB collection '{dense.collection_name}' to avoid mixing incompatible vectors...")
    dense.client.delete_collection(dense.collection_name)
    dense.collection = dense.client.get_or_create_collection(
        name=dense.collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    logger.info("ChromaDB collection cleared and recreated.")

    # 3. Ensure sample contracts exist
    logger.info("Verifying sample contracts in sample_data/...")
    sample_files = ensure_sample_contracts()

    # 4. Discover all PDFs in sample_data and uploads
    pdf_files = list(sample_files)
    for f in UPLOAD_DIR.glob("*.pdf"):
        if f not in pdf_files:
            pdf_files.append(f)

    logger.info(f"Found {len(pdf_files)} PDF contract(s) to index.")

    total_clauses = 0
    indexed_contracts = 0

    for pdf_path in pdf_files:
        contract_name = pdf_path.name
        logger.info(f"Processing contract: {contract_name}")

        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            if len(pdf_bytes) == 0:
                logger.warning(f"Skipping empty file: {contract_name}")
                continue

            clauses = extract_clauses(pdf_bytes, contract_name)
            if not clauses:
                logger.warning(f"No clauses extracted from: {contract_name}")
                continue

            # Index in dense ChromaDB
            dense.index_clauses(contract_name, clauses)
            # Index in BM25
            bm25.index_clauses(contract_name, clauses)

            total_clauses += len(clauses)
            indexed_contracts += 1
            logger.info(f"Successfully indexed '{contract_name}' with {len(clauses)} clauses.")
        except Exception as e:
            logger.error(f"Failed to index '{contract_name}': {e}", exc_info=True)

    logger.info("=== REINDEX SUMMARY ===")
    logger.info(f"Contracts Indexed: {indexed_contracts} / {len(pdf_files)}")
    logger.info(f"Total Clauses Indexed: {total_clauses}")
    logger.info("Reindexing completed successfully.")

if __name__ == "__main__":
    reindex_all()
