import json
import os

import pytest

from backend.agents.supervisor import ROUTES
from scripts.generate_dataset import generate_datasets


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("generated")
    previous = os.getcwd()
    os.chdir(workdir)
    try:
        generate_datasets()
    finally:
        os.chdir(previous)
    return workdir


def _load(workdir, *parts):
    return json.loads(workdir.joinpath(*parts).read_text(encoding="utf-8"))


def test_expected_volumes(generated):
    assert len(_load(generated, "data", "generated", "services.json")) == 20
    assert len(_load(generated, "data", "generated", "incidents.json")) == 300
    assert len(_load(generated, "data", "generated", "deployments.json")) == 100
    assert len(list((generated / "data").glob("*/*.md"))) == 50


def test_golden_questions_have_consistent_ground_truth(generated):
    questions = _load(generated, "evaluation", "datasets", "golden_dataset.json")
    existing = {p.name for p in (generated / "data").glob("*/*.md")}
    assert len(questions) == 50
    for q in questions:
        assert q["expected_route"] in ROUTES
        assert set(q["ground_truth_docs"]) <= existing

    ground_truths = {tuple(q["ground_truth_docs"]) for q in questions if q["ground_truth_docs"]}
    assert len(ground_truths) > 1, "ground truth must differ between questions (it used to be identical for all)"


def test_each_runbook_describes_its_own_topic(generated):
    text = (generated / "data" / "runbooks" / "kafka-lag-mitigation-08.md").read_text(encoding="utf-8")
    assert "**Service:** Kafka Event Bus" in text
    assert "backlog" in text.lower()
