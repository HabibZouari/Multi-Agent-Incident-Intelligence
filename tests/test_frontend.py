import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "frontend" / "app_pages"


def test_main_app_renders_when_backend_is_down(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://127.0.0.1:9")  # nothing listens on the discard port
    at = AppTest.from_file(str(ROOT / "frontend" / "streamlit_app.py"), default_timeout=30).run()
    assert not at.exception
    assert any("Backend unreachable" in e.value for e in at.error)


def test_monitor_page_without_investigation_shows_hint():
    at = AppTest.from_file(str(PAGES / "monitor.py"), default_timeout=30).run()
    assert not at.exception
    assert any("No investigation yet" in i.value for i in at.info)


def test_monitor_page_renders_a_result():
    at = AppTest.from_file(str(PAGES / "monitor.py"), default_timeout=30)
    at.session_state["last_result"] = {
        "query": "q",
        "execution_trace": [{"agent": "Supervisor", "action": "Analysing"}],
        "retrieved_docs": [
            {"source": "a.md (Chunk 0)", "score": 0.9, "bm25_score": 1.0, "vector_score": 0.5, "service_name": "S", "content": "text"}
        ],
        "historical_incidents": [],
        "deployments": [],
    }
    at.run()
    assert not at.exception
    assert any("Supervisor" in e.label for e in at.expander)


def test_evaluation_page_reads_real_results():
    results = ROOT / "evaluation" / "results" / "latest_evaluation.json"
    if not results.exists():
        pytest.skip("evaluation results not generated")
    at = AppTest.from_file(str(PAGES / "evaluation.py"), default_timeout=30).run()
    assert not at.exception
    expected = json.loads(results.read_text(encoding="utf-8"))["routing_accuracy_pct"]
    assert any(m.value == f"{expected}%" for m in at.metric)
