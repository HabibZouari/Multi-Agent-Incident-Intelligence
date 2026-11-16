# Service Mesh Circuit Breaker Configuration (Doc #029)

> **Service:** Kong API Gateway | **Type:** technical_doc | **Topic:** Third-Party API Outage

## Overview
This document outlines standard operating procedures and diagnostic workflows for third-party api outage incidents affecting Kong API Gateway.

## Common Symptoms & Indicators
- External API provider returning HTTP 503 Service Unavailable.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- Upstream vendor experienced regional outage in us-east-1.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for Kong API Gateway.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Enabled circuit breaker fallback to cached response data until vendor recovery.
- Escalate to the on-call owner of Kong API Gateway if unresolved after 30 minutes.
