import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

from backend.config import EVALUATION_DIR
from backend.retrieval.dense import DenseRetriever
from backend.retrieval.bm25 import BM25Retriever
from backend.retrieval.hybrid import HybridRetriever
from backend.agent.orchestrator import run_agent_analysis
from evaluation.metrics import recall_at_k, precision_at_k, reciprocal_rank, ndcg_at_k

logger = logging.getLogger("evaluation.runner")

BENCHMARK_PATH = EVALUATION_DIR / "datasets" / "queries.json"
RESULTS_DIR = EVALUATION_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def load_benchmark_dataset() -> Dict[str, Any]:
    """Load benchmark queries and ground truth from JSON."""
    if not BENCHMARK_PATH.exists():
        raise FileNotFoundError(f"Benchmark dataset not found at {BENCHMARK_PATH}")
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_retrieval_benchmark() -> Dict[str, Any]:
    """
    Execute standardized benchmark across all retrieval configurations:
      1. V1: Dense Retrieval Alone
      2. V2A: BM25 Lexical Alone
      3. V2B: Hybrid (Dense + BM25) without Reranking
      4. V2C: Hybrid (Dense + BM25) + Cross-Encoder Reranking
      5. V3: Controlled Agentic RAG
    """
    data = load_benchmark_dataset()
    queries = data.get("queries", [])
    if not queries:
        raise ValueError("No queries found in benchmark dataset.")

    # Initialize retrieval systems
    dense = DenseRetriever()
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(dense_retriever=dense, bm25_retriever=bm25)

    # Ensure contracts are indexed in BM25
    for q in queries:
        c_name = q["contract_name"]
        if c_name not in bm25.indices:
            clauses = dense.get_all_clauses(c_name)
            if clauses:
                bm25.index_clauses(c_name, clauses)

    systems = {
        "V1_Dense": lambda q, c: dense.retrieve(q, contract_name=c, top_k=8),
        "V2A_BM25": lambda q, c: bm25.retrieve(q, contract_name=c, top_k=8),
        "V2B_Hybrid_NoRerank": lambda q, c: hybrid.retrieve(q, contract_name=c, top_k=8, use_reranker=False),
        "V2C_Hybrid_Reranked": lambda q, c: hybrid.retrieve(q, contract_name=c, top_k=8, use_reranker=True),
        "V3_Controlled_Agent": None  # Handled separately
    }

    results: Dict[str, Dict[str, Any]] = {}

    for sys_name, retriever_fn in systems.items():
        logger.info(f"Evaluating system: {sys_name}...")
        r4_list, r8_list, p4_list, rr_list, ndcg4_list, lat_list = [], [], [], [], [], []
        query_details = []
        tool_calls_list = []

        for q_item in queries:
            qid = q_item["query_id"]
            question = q_item["question"]
            c_name = q_item["contract_name"]
            gt_ids = q_item["relevant_clause_ids"]

            t0 = time.time()
            if sys_name == "V3_Controlled_Agent":
                agent_res = run_agent_analysis(question, contract_name=c_name, max_steps=4)
                latency = time.time() - t0
                retrieved_items = agent_res.get("retrieval", {}).get("results", [])
                retrieved_ids = [item.get("clause_id", f"{c_name}_clause_{item.get('metadata', {}).get('clause_number')}") for item in retrieved_items]
                tool_calls_list.append(len(agent_res.get("agent_trace", {}).get("tool_calls", [])))
            else:
                ret_results = retriever_fn(question, c_name)
                latency = time.time() - t0
                retrieved_ids = [r.clause_id for r in ret_results]
                tool_calls_list.append(0)

            # Calculate metrics
            r4 = recall_at_k(retrieved_ids, gt_ids, k=4)
            r8 = recall_at_k(retrieved_ids, gt_ids, k=8)
            p4 = precision_at_k(retrieved_ids, gt_ids, k=4)
            rr = reciprocal_rank(retrieved_ids, gt_ids)
            ndcg4 = ndcg_at_k(retrieved_ids, gt_ids, k=4)

            r4_list.append(r4)
            r8_list.append(r8)
            p4_list.append(p4)
            rr_list.append(rr)
            ndcg4_list.append(ndcg4)
            lat_list.append(latency)

            query_details.append({
                "query_id": qid,
                "question": question,
                "ground_truth": gt_ids,
                "retrieved": retrieved_ids[:4],
                "recall@4": r4,
                "mrr": rr,
                "ndcg@4": ndcg4,
                "latency_seconds": round(latency, 4)
            })

        n = len(queries)
        results[sys_name] = {
            "system_name": sys_name,
            "queries_evaluated": n,
            "recall_at_4": round(sum(r4_list) / n, 4),
            "recall_at_8": round(sum(r8_list) / n, 4),
            "precision_at_4": round(sum(p4_list) / n, 4),
            "mrr": round(sum(rr_list) / n, 4),
            "ndcg_at_4": round(sum(ndcg4_list) / n, 4),
            "avg_latency_ms": round((sum(lat_list) / n) * 1000.0, 2),
            "avg_tool_calls": round(sum(tool_calls_list) / n, 2),
            "query_details": query_details
        }

    # Save to JSON
    json_path = RESULTS_DIR / "benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": data.get("benchmark_metadata", {}),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {k: {m: v[m] for m in ["recall_at_4", "recall_at_8", "mrr", "ndcg_at_4", "avg_latency_ms", "avg_tool_calls"]} for k, v in results.items()},
                "full_results": results
            },
            f,
            indent=2
        )

    # Save to CSV
    csv_path = RESULTS_DIR / "benchmark_results.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("System,Recall@4,Recall@8,Precision@4,MRR,nDCG@4,Avg_Latency_ms,Avg_Tool_Calls\n")
        for sys_name, res in results.items():
            f.write(f"{sys_name},{res['recall_at_4']},{res['recall_at_8']},{res['precision_at_4']},{res['mrr']},{res['ndcg_at_4']},{res['avg_latency_ms']},{res['avg_tool_calls']}\n")

    logger.info(f"Benchmark results successfully saved to {json_path} and {csv_path}")
    return results
