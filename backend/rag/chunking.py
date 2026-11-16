"""Markdown chunking and document-metadata helpers."""

import re

_HEADER_FIELD = re.compile(r"\*\*(Service|Type):\*\*\s*([^|\n]+)")


def parse_doc_metadata(text: str) -> dict[str, str]:
    """Read the ``> **Service:** X | **Type:** runbook`` header emitted by the dataset generator."""
    return {key.lower(): value.strip() for key, value in _HEADER_FIELD.findall(text)}


def doc_title(text: str, fallback: str = "") -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def chunk_markdown(text: str, max_chars: int = 900) -> list[str]:
    """Split a markdown document into section-level chunks.

    Every chunk is prefixed with the document title so that it stays self-describing once it is
    retrieved on its own, and oversized sections are split on paragraph boundaries.
    """
    title = doc_title(text)
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = []
        if not line.startswith("# "):
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())

    chunks: list[str] = []
    for section in filter(None, sections):
        pieces, buffer = [], ""
        for paragraph in section.split("\n\n"):
            if buffer and len(buffer) + len(paragraph) > max_chars:
                pieces.append(buffer)
                buffer = paragraph
            else:
                buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if buffer:
            pieces.append(buffer)
        chunks.extend(f"{title}\n\n{piece}" if title else piece for piece in pieces)
    return chunks
