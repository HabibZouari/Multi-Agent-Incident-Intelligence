import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results" / "latest_evaluation.json"
DATASET = ROOT / "evaluation" / "datasets" / "golden_dataset.json"


@st.cache_data(show_spinner=False)
def load_json(path: str, modified: float):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt(value) -> str:
    return "n/a" if value is None else f"{value}%"


if not RESULTS.exists():
    st.info("No results yet. Run `PYTHONPATH=. python scripts/run_evaluation.py` to generate them.", icon=":material/info:")
else:
    report = load_json(str(RESULTS), RESULTS.stat().st_mtime)
    st.caption(
        f"Run on {report['generated_at']} in **{report['mode']}** mode over {report['total_test_cases']} questions. "
        "The question set is synthetic and template-based, so scores validate the pipeline rather than predict real-world accuracy."
    )

    row1 = st.columns(4)
    row1[0].metric("Retrieval hit rate", fmt(report["retrieval_hit_rate_pct"]), help=f"Questions with a ground-truth document in the top {report['top_k']} ({report['retrieval_cases']} questions)")
    row1[1].metric("Context precision", fmt(report["context_precision_pct"]), help="Share of retrieved chunks that are relevant")
    row1[2].metric("MRR", report["mrr"] if report["mrr"] is not None else "n/a", help="Mean reciprocal rank of the first relevant chunk")
    row1[3].metric("Routing accuracy", fmt(report["routing_accuracy_pct"]), help="Supervisor intent vs expected route")

    row2 = st.columns(4)
    row2[0].metric("Workflow completion", fmt(report["workflow_completion_rate_pct"]))
    row2[1].metric("Path adherence", fmt(report["path_adherence_pct"]), help="Only the required agents ran")

    st.subheader("Routing accuracy by category")
    by_category = pd.Series(report["routing_accuracy_by_category_pct"], name="accuracy (%)")
    st.bar_chart(by_category, horizontal=True, alt="Routing accuracy per question category")

if DATASET.exists():
    with st.expander("Golden dataset"):
        questions = load_json(str(DATASET), DATASET.stat().st_mtime)
        st.dataframe(
            pd.DataFrame(questions)[["question_id", "category", "query", "expected_route"]],
            hide_index=True,
            alt="Golden evaluation questions",
        )
