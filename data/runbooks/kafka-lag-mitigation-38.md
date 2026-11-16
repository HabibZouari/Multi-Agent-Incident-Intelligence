# Kafka Consumer Lag Troubleshooting Guide (Doc #038)

## Overview
This document outlines standard operating procedures and diagnostic workflows for Kafka Event Bus.

## Common Symptoms & Indicators
- Elevated HTTP error rates (5xx / 4xx).
- Latency spikes exceeding SLA thresholds (>500ms p95).
- Resource exhaustion (CPU, Memory, Connection Pool).

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records.
3. Verify downstream dependencies status (Kafka Event Bus).
4. Run health check endpoints and inspect error stack traces.

## Resolution & Mitigation
- Apply immediate rollback or traffic shedding if deployment-related.
- Scale container replicas or connection pool parameters if resource-constrained.
- Escalate to on-call owner (Kafka Event Bus) if unresolved after 30 minutes.
