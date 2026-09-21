import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import EVALUATION_DIR

def run_error_analysis():
    results_path = EVALUATION_DIR / "results" / "benchmark_results.json"
    if not results_path.exists():
        print("No evaluation results found. Please run 'python scripts/run_evaluation.py' first.")
        return

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    full_results = data.get("full_results", {})
    print("\n" + "=" * 80)
    print("RETRIEVAL ERROR & DISCREPANCY ANALYSIS")
    print("=" * 80 + "\n")

    for sys_name, sys_data in full_results.items():
        query_details = sys_data.get("query_details", [])
        misses = [q for q in query_details if q.get("recall@4", 0.0) < 1.0]
        ranking_errors = [q for q in query_details if q.get("recall@4", 0.0) == 1.0 and q.get("mrr", 0.0) < 1.0]

        print(f"--- System: {sys_name} ---")
        print(f"Total Queries: {len(query_details)} | Top-4 Misses: {len(misses)} | Sub-Optimal Top-1 Rankings: {len(ranking_errors)}")

        if misses:
            print("\n  [Top-4 Retrieval Misses]:")
            for m in misses:
                print(f"    - Query [{m['query_id']}]: \"{m['question']}\"")
                print(f"      Expected:  {m['ground_truth']}")
                print(f"      Retrieved: {m['retrieved']}")
                print(f"      Classification: Retrieval Miss / Semantic Vocabulary Mismatch")

        if ranking_errors:
            print("\n  [Sub-Optimal Rankings (Found in Top 4, but not Rank 1)]:")
            for r in ranking_errors:
                print(f"    - Query [{r['query_id']}]: \"{r['question']}\" (MRR: {r['mrr']:.2f})")
                print(f"      Expected:  {r['ground_truth']}")
                print(f"      Retrieved: {r['retrieved']}")
                print(f"      Classification: Ranking Calibration Error (Cross-Encoder target)")

        print("-" * 80 + "\n")

if __name__ == "__main__":
    run_error_analysis()
