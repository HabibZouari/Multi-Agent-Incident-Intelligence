# Authentication Troubleshooting Runbook (Doc #031)

> **Service:** Authentication Service | **Type:** runbook | **Topic:** Authentication Failure

## Overview
This document outlines standard operating procedures and diagnostic workflows for authentication failure incidents affecting Authentication Service.

## Common Symptoms & Indicators
- Users experiencing HTTP 401/500 errors when logging in. Token validation failing.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- JWT signing secret mismatch across authentication replicas after rolling deployment.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for Authentication Service.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Rolled back authentication service deployment, synchronized JWT secret environment variable across all nodes, and verified login success.
- Escalate to the on-call owner of Authentication Service if unresolved after 30 minutes.
