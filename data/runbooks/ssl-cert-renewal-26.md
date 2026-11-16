# SSL/TLS Certificate Lifecycle & Renewal Runbook (Doc #026)

> **Service:** Kong API Gateway | **Type:** runbook | **Topic:** Expired SSL/TLS Certificate

## Overview
This document outlines standard operating procedures and diagnostic workflows for expired ssl/tls certificate incidents affecting Kong API Gateway.

## Common Symptoms & Indicators
- Client connections failing with SSL handshake error. Certificate expired on the renewal deadline.
- Elevated HTTP error rates (5xx / 4xx) and latency spikes exceeding SLA thresholds (>500ms p95).

## Known Root Causes
- Automated certificate renewal cron job failed due to IAM role permission revocation.

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records for Kong API Gateway.
3. Verify downstream dependencies and inspect error stack traces.

## Resolution & Mitigation
- Manually triggered Let's Encrypt certificate renewal via certbot and restarted ingress controller.
- Escalate to the on-call owner of Kong API Gateway if unresolved after 30 minutes.
