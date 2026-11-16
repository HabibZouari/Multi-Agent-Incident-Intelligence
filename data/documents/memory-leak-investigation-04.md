# Container Memory Leak & OOM Guide (Doc #004)

> **Service:** All Services | **Type:** technical_doc | **Topic:** Memory Leak / OOM

## Overview
This document outlines standard operating procedures and diagnostic workflows for memory leak / oom incidents affecting All Services.

## Common Symptoms & Indicators
- Container pods restarting continuously due to OOMKilled exit code 137.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- Unbounded cache growth in memory without TTL eviction policy.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for All Services.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Increased container memory limit from 2GB to 4GB temporarily and deployed patch implementing LRU cache eviction.
- Escalate to the on-call owner of All Services if unresolved after 30 minutes.
