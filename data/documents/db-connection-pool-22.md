# PostgreSQL Connection Pool Management (Doc #022)

> **Service:** User PostgreSQL DB | **Type:** technical_doc | **Topic:** Database Connection Exhaustion

## Overview
This document outlines standard operating procedures and diagnostic workflows for database connection exhaustion incidents affecting User PostgreSQL DB.

## Common Symptoms & Indicators
- PostgreSQL connection pool exhausted. New queries timing out with 54000/53300 error codes.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- Connection leak in connection pool manager introduced in recent PR without proper cleanup in finally blocks.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for User PostgreSQL DB.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Restarted application service pods to clear stale connections, adjusted max pool size from 50 to 200, and deployed connection leak fix.
- Escalate to the on-call owner of User PostgreSQL DB if unresolved after 30 minutes.
