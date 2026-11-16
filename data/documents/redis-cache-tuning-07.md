# Redis Cache Eviction & Memory Tuning (Doc #007)

> **Service:** Redis Cache Cluster | **Type:** technical_doc | **Topic:** Redis Cache Eviction Storm

## Overview
This document outlines standard operating procedures and diagnostic workflows for redis cache eviction storm incidents affecting Redis Cache Cluster.

## Common Symptoms & Indicators
- High memory pressure on Redis cluster leading to cache misses and database CPU spike.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- Maxmemory-policy incorrectly set to noeviction instead of allkeys-lru.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for Redis Cache Cluster.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Updated Redis maxmemory-policy to volatile-lru and flushed expired keys.
- Escalate to the on-call owner of Redis Cache Cluster if unresolved after 30 minutes.
