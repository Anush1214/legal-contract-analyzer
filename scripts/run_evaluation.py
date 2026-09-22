import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.runner import run_retrieval_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_evaluation")

def main():
    print("\n" + "=" * 95)
    print("LEGAL CONTRACT ANALYZER: RETRIEVAL ARCHITECTURE BENCHMARK")
    print("Evaluating V1 (Dense), V2A (BM25), V2B (Hybrid), V2C (Hybrid+Rerank), and V3 (Agentic)")
    print("=" * 95 + "\n")

    results = run_retrieval_benchmark()

    # Formatted terminal table
    header = f"{'System':<22} | {'Recall@4':<9} | {'Recall@8':<9} | {'Precision@4':<11} | {'MRR':<8} | {'nDCG@4':<8} | {'Latency (ms)':<13} | {'Tool Calls':<10}"
    print("\n" + "-" * len(header))
    print(header)
    print("-" * len(header))

    for sys_name, m in results.items():
        row = (
            f"{sys_name:<22} | "
            f"{m['recall_at_4']:<9.4f} | "
            f"{m['recall_at_8']:<9.4f} | "
            f"{m['precision_at_4']:<11.4f} | "
            f"{m['mrr']:<8.4f} | "
            f"{m['ndcg_at_4']:<8.4f} | "
            f"{m['avg_latency_ms']:<13.1f} | "
            f"{m['avg_tool_calls']:<10.1f}"
        )
        print(row)

    print("-" * len(header) + "\n")
    print("Detailed report saved to: evaluation/results/benchmark_results.json and .csv")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    main()
