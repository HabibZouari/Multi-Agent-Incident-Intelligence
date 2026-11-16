#!/usr/bin/env python3
"""Evaluation runner for ResolveAI.

Measures, against the golden dataset (evaluation/datasets/golden_dataset.json):
  * retrieval  - hit rate, context precision@k and MRR (questions that have ground-truth documents)
  * routing    - Supervisor intent classification accuracy
  * workflow   - completion rate and path adherence of the real LangGraph workflow

By default the run is fully offline and deterministic (keyword router + evidence-summary agents), so it is
free and reproducible. Pass --use-llm to evaluate with the configured LLM (needs ANTHROPIC_API_KEY).

Usage:  PYTHONPATH=. python scripts/run_evaluation.py [--use-llm] [--top-k 3]
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from backend.core.config import settings

EVAL_PATH = Path("evaluation/datasets/golden_dataset.json")
RESULTS_PATH = Path("evaluation/results/latest_evaluation.json")


def pct(values: list[float]) -> float | None:
    return round(mean(values) * 100, 1) if values else None


def run_evaluation(use_llm: bool = False, top_k: int = 3) -> dict:
    if not use_llm:
        settings.anthropic_api_key = ""  # force the deterministic offline path before agents are built
    elif not settings.llm_enabled:
        raise SystemExit("--use-llm requires ANTHROPIC_API_KEY to be configured.")

    # Imported after the settings override so the agents pick it up.
    from backend.agents.supervisor import SupervisorAgent
    from backend.orchestration.workflow import run_investigation
    from backend.rag.retrieval import get_retriever
    from evaluation.metrics.agent_metrics import path_adherence, routing_accuracy, workflow_completed
    from evaluation.metrics.rag_metrics import context_precision, hit_rate, reciprocal_rank

    if not EVAL_PATH.exists():
        raise SystemExit(f"{EVAL_PATH} not found. Run `python scripts/generate_dataset.py` first.")
    dataset = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

    retriever, supervisor = get_retriever(), SupervisorAgent()
    hits, precisions, rrs, routing, completion, adherence = [], [], [], [], [], []
    by_category: dict[str, list[float]] = defaultdict(list)

    print(f"Evaluating {len(dataset)} golden questions (llm={'on' if use_llm else 'off'}, top_k={top_k})...")
    for item in dataset:
        truth = item["ground_truth_docs"]
        if truth:  # retrieval metrics are only defined when a relevant document exists
            retrieved = retriever.search(item["query"], top_k=top_k)
            hits.append(hit_rate(retrieved, truth))
            precisions.append(context_precision(retrieved, truth))
            rrs.append(reciprocal_rank(retrieved, truth))

        correct = routing_accuracy(supervisor.classify_intent(item["query"]), item["expected_route"])
        routing.append(correct)
        by_category[item["category"]].append(correct)

        result = run_investigation(item["query"])
        completion.append(workflow_completed(result))
        adherence.append(path_adherence(result["classification"], result))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "llm" if use_llm else "offline",
        "top_k": top_k,
        "total_test_cases": len(dataset),
        "retrieval_cases": len(hits),
        "retrieval_hit_rate_pct": pct(hits),
        "context_precision_pct": pct(precisions),
        "mrr": round(mean(rrs), 3) if rrs else None,
        "routing_accuracy_pct": pct(routing),
        "routing_accuracy_by_category_pct": {c: pct(v) for c, v in sorted(by_category.items())},
        "workflow_completion_rate_pct": pct(completion),
        "path_adherence_pct": pct(adherence),
    }

    print("=" * 52)
    print("ResolveAI evaluation report")
    print("=" * 52)
    for key, value in report.items():
        if key != "routing_accuracy_by_category_pct":
            print(f"{key:<32}: {value}")
    print("routing accuracy by category:")
    for category, value in report["routing_accuracy_by_category_pct"].items():
        print(f"  {category:<34}{value}%")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved report to {RESULTS_PATH}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--use-llm", action="store_true", help="evaluate with the configured LLM instead of the offline path")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    run_evaluation(use_llm=args.use_llm, top_k=args.top_k)
