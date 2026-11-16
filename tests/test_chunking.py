from backend.rag.chunking import chunk_markdown, doc_title, parse_doc_metadata

DOC = """# Title (Doc #001)

> **Service:** Kafka Event Bus | **Type:** runbook | **Topic:** Lag

## Overview
Intro text.

## Resolution
- Scale consumers.
"""


def test_parse_metadata_header():
    assert parse_doc_metadata(DOC) == {"service": "Kafka Event Bus", "type": "runbook"}


def test_parse_metadata_missing_header():
    assert parse_doc_metadata("# Just a title\n\nBody") == {}


def test_title_extraction():
    assert doc_title(DOC) == "Title (Doc #001)"
    assert doc_title("no heading", "fallback") == "fallback"


def test_chunks_are_sections_prefixed_with_title():
    chunks = chunk_markdown(DOC)
    assert len(chunks) == 3  # preamble/metadata, Overview, Resolution
    assert all(c.startswith("Title (Doc #001)") for c in chunks)
    assert "Scale consumers." in chunks[-1]


def test_oversized_sections_are_split_on_paragraphs():
    body = "\n\n".join(f"Paragraph {i} " + "x" * 200 for i in range(6))
    chunks = chunk_markdown(f"# T\n\n## Big\n{body}", max_chars=500)
    assert len(chunks) > 1
