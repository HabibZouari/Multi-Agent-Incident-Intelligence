"""Thin client for the ResolveAI backend API."""

import os
from typing import Any

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def _headers() -> dict[str, str]:
    """Send the shared API key (if configured) with every backend call."""
    key = os.getenv("API_KEY", "")
    return {"X-API-Key": key} if key else {}


class BackendError(RuntimeError):
    """Raised when the backend is unreachable or returns an error."""


def _error_message(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            return str(response.json().get("detail", response.text))
        except ValueError:
            return response.text
    return f"Cannot reach the backend at {BACKEND_URL} ({type(exc).__name__})."


@st.cache_data(ttl=30, show_spinner=False)
def get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        response = requests.get(f"{BACKEND_URL}{path}", params=params, headers=_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise BackendError(_error_message(exc)) from exc


@st.cache_data(ttl=10, show_spinner=False)
def health() -> dict[str, Any] | None:
    """Backend health payload, or None when the backend is down."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def investigate(query: str, model: str | None = None) -> dict[str, Any]:
    try:
        response = requests.post(f"{BACKEND_URL}/api/investigate", json={"query": query, "model": model}, headers=_headers(), timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise BackendError(_error_message(exc)) from exc


def upload_document(name: str, data: bytes, document_type: str, service_name: str) -> dict[str, Any]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/documents/upload",
            files={"file": (name, data)},
            data={"document_type": document_type, "service_name": service_name},
            headers=_headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise BackendError(_error_message(exc)) from exc
