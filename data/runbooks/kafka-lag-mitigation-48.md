# Kafka Consumer Lag Troubleshooting Guide (Doc #048)

> **Service:** Kafka Event Bus | **Type:** runbook | **Topic:** Kafka Consumer Lag Spike

## Overview
This document outlines standard operating procedures and diagnostic workflows for kafka consumer lag spike incidents affecting Kafka Event Bus.

## Common Symptoms & Indicators
- Event processing backlog increasing rapidly on topic orders-topic.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- Consumer thread pool deadlock during message deserialization batching.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for Kafka Event Bus.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Increased Kafka consumer group concurrency and scaled consumer pods.
- Escalate to the on-call owner of Kafka Event Bus if unresolved after 30 minutes.
