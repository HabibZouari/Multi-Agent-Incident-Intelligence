#!/usr/bin/env python3
"""
Synthetic Dataset Generator for ResolveAI
Generates:
- 50 Technical Documentation Files & Runbooks
- 300 Historical Incident Records
- 20 Services with Dependencies
- 100 Deployment / Change Records
- 50 Golden Evaluation Questions
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Set fixed random seed for reproducibility
random.seed(42)

SERVICES = [
    {"service_id": "srv-auth", "name": "Authentication Service", "tier": "Tier-1", "owner": "sec-team@resolveai.internal", "dependencies": ["srv-db-users", "srv-redis"]},
    {"service_id": "srv-payment", "name": "Payment Processing Gateway", "tier": "Tier-1", "owner": "checkout-team@resolveai.internal", "dependencies": ["srv-db-orders", "srv-fraud", "srv-auth"]},
    {"service_id": "srv-catalog", "name": "Product Catalog API", "tier": "Tier-2", "owner": "catalog-team@resolveai.internal", "dependencies": ["srv-db-catalog", "srv-redis"]},
    {"service_id": "srv-search", "name": "Search & Recommendation Engine", "tier": "Tier-2", "owner": "search-team@resolveai.internal", "dependencies": ["srv-elasticsearch", "srv-catalog"]},
    {"service_id": "srv-notification", "name": "Notification Dispatcher", "tier": "Tier-3", "owner": "notif-team@resolveai.internal", "dependencies": ["srv-kafka", "srv-email-provider"]},
    {"service_id": "srv-db-users", "name": "User PostgreSQL DB", "tier": "Tier-1", "owner": "dba-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-db-orders", "name": "Orders PostgreSQL DB", "tier": "Tier-1", "owner": "dba-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-db-catalog", "name": "Catalog PostgreSQL DB", "tier": "Tier-2", "owner": "dba-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-redis", "name": "Redis Cache Cluster", "tier": "Tier-1", "owner": "cache-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-elasticsearch", "name": "Elasticsearch Cluster", "tier": "Tier-2", "owner": "search-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-fraud", "name": "Fraud Detection Microservice", "tier": "Tier-1", "owner": "risk-team@resolveai.internal", "dependencies": ["srv-db-orders"]},
    {"service_id": "srv-kafka", "name": "Kafka Event Bus", "tier": "Tier-1", "owner": "infra-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-email-provider", "name": "SendGrid Email Relay", "tier": "Tier-3", "owner": "notif-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-api-gateway", "name": "Kong API Gateway", "tier": "Tier-1", "owner": "infra-team@resolveai.internal", "dependencies": ["srv-auth", "srv-payment", "srv-catalog", "srv-search"]},
    {"service_id": "srv-recommendation", "name": "ML Recommendation Model", "tier": "Tier-3", "owner": "ml-team@resolveai.internal", "dependencies": ["srv-search"]},
    {"service_id": "srv-analytics", "name": "Analytics Data Pipeline", "tier": "Tier-3", "owner": "data-team@resolveai.internal", "dependencies": ["srv-kafka"]},
    {"service_id": "srv-storage", "name": "S3 Asset Storage", "tier": "Tier-2", "owner": "infra-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-cdn", "name": "CloudFront CDN", "tier": "Tier-1", "owner": "infra-team@resolveai.internal", "dependencies": []},
    {"service_id": "srv-inventory", "name": "Inventory Management", "tier": "Tier-2", "owner": "logistics-team@resolveai.internal", "dependencies": ["srv-db-orders"]},
    {"service_id": "srv-shipping", "name": "Shipping & Fulfillment", "tier": "Tier-2", "owner": "logistics-team@resolveai.internal", "dependencies": ["srv-inventory"]}
]

INCIDENT_CATEGORIES = [
    "Authentication Failure", "Database Connection Exhaustion", "API Gateway Timeout",
    "Memory Leak / OOM", "Deployment Regression", "Expired SSL/TLS Certificate",
    "Redis Cache Eviction Storm", "Kafka Consumer Lag Spike", "Third-Party API Outage",
    "Misconfigured Environment Variable"
]

SYMPTOMS_TEMPLATE = {
    "Authentication Failure": "Users experiencing HTTP 401/500 errors when logging in. Token validation failing.",
    "Database Connection Exhaustion": "PostgreSQL connection pool exhausted. New queries timing out with 54000/53300 error codes.",
    "API Gateway Timeout": "Kong gateway returning 504 Gateway Timeout on downstream calls to {service}.",
    "Memory Leak / OOM": "Container pods restarting continuously due to OOMKilled exit code 137.",
    "Deployment Regression": "HTTP 500 error rate spiked to 14% immediately following deployment of version {version}.",
    "Expired SSL/TLS Certificate": "Client connections failing with SSL handshake error. Certificate expired on {date}.",
    "Redis Cache Eviction Storm": "High memory pressure on Redis cluster leading to cache misses and database CPU spike.",
    "Kafka Consumer Lag Spike": "Event processing backlog increasing rapidly on topic {topic}.",
    "Third-Party API Outage": "External API provider returning HTTP 503 Service Unavailable.",
    "Misconfigured Environment Variable": "Service failing to start on boot due to missing or invalid ENV variable {env_var}."
}

ROOT_CAUSES_TEMPLATE = {
    "Authentication Failure": "JWT signing secret mismatch across authentication replicas after rolling deployment.",
    "Database Connection Exhaustion": "Connection leak in connection pool manager introduced in recent PR without proper cleanup in finally blocks.",
    "API Gateway Timeout": "Downstream service {service} thread pool saturated due to slow database queries.",
    "Memory Leak / OOM": "Unbounded cache growth in memory without TTL eviction policy.",
    "Deployment Regression": "Database migration script failed to add required column before application code execution.",
    "Expired SSL/TLS Certificate": "Automated certificate renewal cron job failed due to IAM role permission revocation.",
    "Redis Cache Eviction Storm": "Maxmemory-policy incorrectly set to noeviction instead of allkeys-lru.",
    "Kafka Consumer Lag Spike": "Consumer thread pool deadlock during message deserialization batching.",
    "Third-Party API Outage": "Upstream vendor experienced regional outage in us-east-1.",
    "Misconfigured Environment Variable": "Kubernetes ConfigMap update was not followed by a rolling pod restart."
}

RESOLUTIONS_TEMPLATE = {
    "Authentication Failure": "Rolled back authentication service deployment, synchronized JWT secret environment variable across all nodes, and verified login success.",
    "Database Connection Exhaustion": "Restarted application service pods to clear stale connections, adjusted max pool size from 50 to 200, and deployed connection leak fix.",
    "API Gateway Timeout": "Scaled up downstream service replicas from 3 to 8 and optimized database index on frequently queried table.",
    "Memory Leak / OOM": "Increased container memory limit from 2GB to 4GB temporarily and deployed patch implementing LRU cache eviction.",
    "Deployment Regression": "Rolled back deployment to previous stable version (v1.4.2) and applied missing database migration manually.",
    "Expired SSL/TLS Certificate": "Manually triggered Let's Encrypt certificate renewal via certbot and restarted ingress controller.",
    "Redis Cache Eviction Storm": "Updated Redis maxmemory-policy to volatile-lru and flushed expired keys.",
    "Kafka Consumer Lag Spike": "Increased Kafka consumer group concurrency and scaled consumer pods.",
    "Third-Party API Outage": "Enabled circuit breaker fallback to cached response data until vendor recovery.",
    "Misconfigured Environment Variable": "Updated Kubernetes ConfigMap, restarted pods, and added startup health check validation."
}

def generate_datasets():
    base_dir = Path("data")
    base_dir.mkdir(exist_ok=True)

    generated_dir = base_dir / "generated"
    generated_dir.mkdir(exist_ok=True)

    docs_dir = base_dir / "documents"
    docs_dir.mkdir(exist_ok=True)

    runbooks_dir = base_dir / "runbooks"
    runbooks_dir.mkdir(exist_ok=True)

    # 1. Services
    services_path = generated_dir / "services.json"
    with open(services_path, "w") as f:
        json.dump(SERVICES, f, indent=2)
    print(f"Generated {len(SERVICES)} services -> {services_path}")

    # 2. Deployments (100 records)
    deployments = []
    start_date = datetime.now() - timedelta(days=90)
    for i in range(1, 101):
        svc = random.choice(SERVICES)
        dep_date = start_date + timedelta(days=random.randint(0, 89), hours=random.randint(0, 23))
        status = random.choices(["success", "rollback", "failed"], weights=[80, 15, 5])[0]
        deployments.append({
            "deployment_id": f"dep-{i:03d}",
            "service_name": svc["name"],
            "service_id": svc["service_id"],
            "version": f"v1.{random.randint(0, 5)}.{random.randint(0, 20)}",
            "deployed_at": dep_date.isoformat(),
            "author": f"engineer-{random.randint(1, 15)}@resolveai.internal",
            "status": status,
            "changes_summary": f"Updated dependencies and refactored request handlers for {svc['name']}."
        })

    deployments_path = generated_dir / "deployments.json"
    with open(deployments_path, "w") as f:
        json.dump(deployments, f, indent=2)
    print(f"Generated {len(deployments)} deployments -> {deployments_path}")

    # 3. Incidents (300 records)
    incidents = []
    severities = ["P1", "P2", "P3", "P4"]
    for i in range(1, 301):
        svc = random.choice(SERVICES)
        category = random.choice(INCIDENT_CATEGORIES)
        inc_date = start_date + timedelta(days=random.randint(0, 89), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        duration_mins = random.randint(15, 360)
        resolved_date = inc_date + timedelta(minutes=duration_mins)
        severity = random.choices(severities, weights=[10, 25, 45, 20])[0]

        symptoms = SYMPTOMS_TEMPLATE.get(category, "Service exhibiting degraded performance.").format(
            service=svc["name"], version="v1.3.2", date=inc_date.strftime("%Y-%m-%d"), topic="orders-topic", env_var="DATABASE_URL"
        )
        root_cause = ROOT_CAUSES_TEMPLATE.get(category, "Unknown infrastructure anomaly.").format(service=svc["name"])
        resolution = RESOLUTIONS_TEMPLATE.get(category, "Restarted service and verified metrics.")

        incidents.append({
            "incident_id": f"INC-{i:04d}",
            "title": f"[{severity}] {category} in {svc['name']}",
            "severity": severity,
            "service_name": svc["name"],
            "service_id": svc["service_id"],
            "status": "resolved",
            "category": category,
            "symptoms": symptoms,
            "root_cause": root_cause,
            "resolution": resolution,
            "created_at": inc_date.isoformat(),
            "resolved_at": resolved_date.isoformat()
        })

    incidents_path = generated_dir / "incidents.json"
    with open(incidents_path, "w") as f:
        json.dump(incidents, f, indent=2)
    print(f"Generated {len(incidents)} historical incidents -> {incidents_path}")

    # 4. Technical Documentation & Runbooks (50 files)
    doc_topics = [
        ("auth-troubleshooting", "Authentication Troubleshooting Runbook", "runbook", "Authentication Service"),
        ("db-connection-pool", "PostgreSQL Connection Pool Management", "technical_doc", "User PostgreSQL DB"),
        ("api-gateway-timeouts", "Kong API Gateway Timeout Runbook", "runbook", "Kong API Gateway"),
        ("memory-leak-investigation", "Container Memory Leak & OOM Guide", "technical_doc", "All Services"),
        ("deployment-rollback-guide", "Production Deployment & Rollback Procedures", "runbook", "All Services"),
        ("ssl-cert-renewal", "SSL/TLS Certificate Lifecycle & Renewal Runbook", "runbook", "Kong API Gateway"),
        ("redis-cache-tuning", "Redis Cache Eviction & Memory Tuning", "technical_doc", "Redis Cache Cluster"),
        ("kafka-lag-mitigation", "Kafka Consumer Lag Troubleshooting Guide", "runbook", "Kafka Event Bus"),
        ("circuit-breaker-config", "Service Mesh Circuit Breaker Configuration", "technical_doc", "Kong API Gateway"),
        ("env-config-management", "Environment Variable Management & Secrets", "technical_doc", "All Services")
    ]

    for i in range(1, 51):
        topic_key, title, doc_type, svc_name = doc_topics[(i - 1) % len(doc_topics)]
        content = f"""# {title} (Doc #{i:03d})

## Overview
This document outlines standard operating procedures and diagnostic workflows for {svc_name}.

## Common Symptoms & Indicators
- Elevated HTTP error rates (5xx / 4xx).
- Latency spikes exceeding SLA thresholds (>500ms p95).
- Resource exhaustion (CPU, Memory, Connection Pool).

## Investigation Steps
1. Check CloudWatch / Prometheus metrics for anomalies around the incident window.
2. Inspect recent deployment logs and change management records.
3. Verify downstream dependencies status ({svc_name}).
4. Run health check endpoints and inspect error stack traces.

## Resolution & Mitigation
- Apply immediate rollback or traffic shedding if deployment-related.
- Scale container replicas or connection pool parameters if resource-constrained.
- Escalate to on-call owner ({svc_name}) if unresolved after 30 minutes.
"""
        target_dir = runbooks_dir if doc_type == "runbook" else docs_dir
        file_path = target_dir / f"{topic_key}-{i:02d}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"Generated 50 technical documentation and runbook files in data/documents and data/runbooks")

    # 5. Golden Evaluation Dataset (50 questions)
    eval_questions = []
    eval_categories = [
        "Simple Documentation Retrieval", "Technical Troubleshooting", "Similar Incident Discovery",
        "Structured Database Queries", "Multi-Step Investigations", "RAG + Database Combined",
        "Insufficient Information", "Hallucination Resistance"
    ]

    for i in range(1, 51):
        category = eval_categories[(i - 1) % len(eval_categories)]
        eval_questions.append({
            "question_id": f"EQ-{i:03d}",
            "category": category,
            "query": f"How should our engineering team investigate and resolve a {random.choice(INCIDENT_CATEGORIES).lower()} affecting the {random.choice(SERVICES)['name']}?",
            "expected_answer": "Investigation requires checking service health metrics, inspecting recent deployments, verifying database/cache connectivity, and following the standard runbook procedure.",
            "ground_truth_docs": ["auth-troubleshooting-01.md", "db-connection-pool-02.md"],
            "expected_tools": ["search_knowledge_base", "search_incidents", "get_service_dependencies"]
        })

    eval_path = Path("evaluation/datasets/golden_dataset.json")
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_questions, f, indent=2)
    print(f"Generated 50 golden evaluation questions -> {eval_path}")

if __name__ == "__main__":
    generate_datasets()
    print("Dataset generation completed successfully.")
