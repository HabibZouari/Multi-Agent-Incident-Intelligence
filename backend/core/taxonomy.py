"""Shared incident taxonomy: category keywords used for query understanding and routing."""

import re

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Authentication Failure": ("authentication", "auth", "login", "token", "jwt", "401", "credential", "sso"),
    "Database Connection Exhaustion": ("database", "connection pool", "pool", "postgres", "postgresql", "sql", "exhausted"),
    "API Gateway Timeout": ("gateway", "timeout", "504", "kong", "upstream"),
    "Memory Leak / OOM": ("memory", "oom", "oomkilled", "leak", "heap", "137"),
    "Deployment Regression": ("deployment", "deploy", "regression", "rollback", "release"),
    "Expired SSL/TLS Certificate": ("ssl", "tls", "certificate", "cert", "handshake"),
    "Redis Cache Eviction Storm": ("redis", "cache", "eviction", "maxmemory"),
    "Kafka Consumer Lag Spike": ("kafka", "consumer", "lag", "backlog"),
    "Third-Party API Outage": ("third-party", "third party", "vendor", "external api", "503", "circuit breaker"),
    "Misconfigured Environment Variable": ("environment variable", "env var", "configmap", "misconfigured", "secret"),
}

# Phrases that signal the user wants historical / operational records rather than documentation.
INCIDENT_SIGNALS = (
    "incident", "before", "previous", "past", "history", "historical", "similar", "recent",
    "depend", "owner", "tier", "last week", "yesterday",
)
# Phrases that signal the user wants documentation / procedures.
KNOWLEDGE_SIGNALS = (
    "runbook", "procedure", "steps", "how to", "how do", "guide", "documentation", "playbook", "troubleshoot", "mitigat",
)


def has_signal(text: str, signals: tuple[str, ...]) -> bool:
    """True if any signal occurs in ``text`` at a word start (so 'depend' matches 'dependencies')."""
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(signal)}", lowered) for signal in signals)


def match_categories(text: str) -> list[str]:
    """Incident categories whose keywords appear in ``text``, best match first."""
    scored = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}", text.lower()))
        if hits:
            scored.append((hits, category))
    return [category for _, category in sorted(scored, key=lambda x: -x[0])]
