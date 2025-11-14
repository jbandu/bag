# Baggage AI Production Deployment Guide

Complete deployment configuration for Copa Airlines production environment.

**Version**: 1.0.0
**Last Updated**: 2025-11-14
**Environment**: Production
**Tenant**: Copa Airlines

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Local Development (Docker Compose)](#local-development)
4. [Production Deployment (Kubernetes)](#production-deployment)
5. [Security Configuration](#security-configuration)
6. [Monitoring Setup](#monitoring-setup)
7. [Backup & Disaster Recovery](#backup--disaster-recovery)
8. [Scaling & Performance](#scaling--performance)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Components

- **8 AI Agents**: Autonomous agents for baggage handling operations
- **Semantic API Gateway**: Unified interface to 7 external systems
- **Neo4j Cluster**: 3-node knowledge graph (High Availability)
- **Redis Cluster**: Distributed caching and working memory
- **Orchestration Layer**: LangGraph-based workflow orchestration
- **Memory System**: 3-layer semantic memory (Working, Episodic, Semantic)

### Infrastructure

- **Container Orchestration**: Kubernetes 1.28+
- **Service Mesh**: Istio (optional)
- **Ingress**: Nginx Ingress Controller
- **Monitoring**: Prometheus + Grafana
- **Logging**: Fluentd → Elasticsearch → Kibana
- **Secret Management**: HashiCorp Vault
- **Backup**: AWS S3 with 30-day retention

---

## Prerequisites

### Required Tools

```bash
# Kubernetes CLI
kubectl version --client

# Docker (for local development)
docker --version
docker-compose --version

# Helm (for package management)
helm version

# AWS CLI (for backups)
aws --version

# Vault CLI (for secrets)
vault version
```

### Required Access

- Kubernetes cluster with admin access
- AWS account with S3 access
- HashiCorp Vault instance
- Container registry (Docker Hub, AWS ECR, or GCR)
- Copa Airlines SSO credentials

---

## Local Development

### Quick Start with Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/copa-airlines/baggage-ai.git
cd baggage-ai

# 2. Set environment variables
cp deploy/environments/development.env .env
source .env

# 3. Start all services
docker-compose -f deploy/docker-compose.yml up -d

# 4. Verify services are running
docker-compose ps

# 5. Access services
# - API Gateway: http://localhost:8000
# - Neo4j Browser: http://localhost:7474
# - Grafana: http://localhost:3000 (admin/baggage-ai-2024)
# - Prometheus: http://localhost:9090
```

### Service Endpoints

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| API Gateway | 8000 | http://localhost:8000 | N/A (dev mode) |
| Neo4j Browser | 7474 | http://localhost:7474 | neo4j/baggage-ai-2024 |
| Neo4j Bolt | 7687 | bolt://localhost:7687 | neo4j/baggage-ai-2024 |
| Redis | 6379 | localhost:6379 | N/A |
| Grafana | 3000 | http://localhost:3000 | admin/baggage-ai-2024 |
| Prometheus | 9090 | http://localhost:9090 | N/A |

### Development Workflow

```bash
# View logs
docker-compose logs -f api-gateway

# Restart a service
docker-compose restart api-gateway

# Run tests
docker-compose exec api-gateway pytest tests/

# Access Neo4j shell
docker-compose exec neo4j-core1 cypher-shell -u neo4j -p baggage-ai-2024

# Access Redis CLI
docker-compose exec redis-master redis-cli

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

---

## Production Deployment

### 1. Prepare Kubernetes Cluster

```bash
# Create namespace
kubectl apply -f deploy/k8s/namespace.yaml

# Verify namespace
kubectl get namespace baggage-ai
```

### 2. Configure Secrets (Using Vault)

```bash
# Set up Vault authentication
vault login -method=oidc

# Create secrets in Vault
vault kv put secret/baggage-ai/database/neo4j \
  username=neo4j \
  password=<STRONG_PASSWORD>

vault kv put secret/baggage-ai/database/redis \
  password=<STRONG_PASSWORD>

vault kv put secret/baggage-ai/api-keys \
  worldtracer=<API_KEY> \
  dcs=<API_KEY> \
  courier=<API_KEY>

vault kv put secret/baggage-ai/oauth2 \
  client_id=<CLIENT_ID> \
  client_secret=<CLIENT_SECRET> \
  jwt_secret=<JWT_SECRET>

# Apply Vault integration
kubectl apply -f deploy/security/vault-integration.yaml

# Run initial secret sync
kubectl create job --from=cronjob/vault-secret-sync vault-secret-sync-initial -n baggage-ai
```

### 3. Deploy ConfigMaps

```bash
# Apply configuration
kubectl apply -f deploy/k8s/configmap.yaml

# Verify
kubectl get configmap -n baggage-ai
```

### 4. Deploy Services

```bash
# Deploy Neo4j cluster
kubectl apply -f deploy/k8s/neo4j-cluster.yaml

# Wait for Neo4j to be ready
kubectl wait --for=condition=ready pod -l app=neo4j -n baggage-ai --timeout=300s

# Deploy Redis cluster
kubectl apply -f deploy/k8s/redis-cluster.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n baggage-ai --timeout=120s

# Deploy API Gateway
kubectl apply -f deploy/k8s/api-gateway-deployment.yaml

# Deploy Agents
kubectl apply -f deploy/k8s/agents-deployment.yaml

# Deploy Ingress
kubectl apply -f deploy/k8s/ingress.yaml
```

### 5. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n baggage-ai

# Check services
kubectl get svc -n baggage-ai

# Check ingress
kubectl get ingress -n baggage-ai

# View API Gateway logs
kubectl logs -f deployment/api-gateway -n baggage-ai

# Test health endpoint
kubectl run curl --image=curlimages/curl -i --rm --restart=Never -- \
  curl -s http://api-gateway:8000/health
```

### 6. Configure DNS

```bash
# Get LoadBalancer IP
kubectl get svc nginx-ingress-controller -n baggage-ai -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Add DNS records (example with Route53)
aws route53 change-resource-record-sets --hosted-zone-id <ZONE_ID> --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "api.baggage-ai.copa.com",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "<LOADBALANCER_IP>"}]
    }
  }]
}'
```

---

## Security Configuration

### OAuth2 / OpenID Connect

```bash
# Apply OAuth2 configuration
kubectl apply -f deploy/security/oauth2-config.yaml

# Test OAuth2 flow
curl -X POST https://auth.copaair.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "scope=baggage:read baggage:write"
```

### TLS Certificates

```bash
# Using cert-manager (recommended)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@copaair.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Certificates will be automatically provisioned via Ingress annotations
```

### Audit Logging

```bash
# Deploy audit logging
kubectl apply -f deploy/security/audit-logging.yaml

# View audit logs
kubectl logs -f daemonset/fluentd-audit -n baggage-ai

# Query audit events in Elasticsearch
curl -X GET "https://elasticsearch.copaair.com/baggage-ai-audit-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"event_type": "pii_access"}}}'
```

---

## Monitoring Setup

### Deploy Prometheus & Grafana

```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace baggage-ai \
  --values deploy/monitoring/prometheus-values.yaml

# Access Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n baggage-ai

# Default credentials: admin / prom-operator
```

### Import Dashboards

```bash
# API Gateway dashboard
kubectl apply -f deploy/monitoring/grafana/dashboards/api-gateway.json

# Agent Performance dashboard
kubectl apply -f deploy/monitoring/grafana/dashboards/agent-performance.json

# Neo4j Cluster dashboard
kubectl apply -f deploy/monitoring/grafana/dashboards/neo4j-cluster.json
```

### Configure Alerts

```bash
# Apply alert rules
kubectl apply -f deploy/monitoring/alerts.yml

# Configure AlertManager webhook (Slack example)
kubectl create secret generic alertmanager-slack-webhook \
  --from-literal=webhook-url=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK \
  -n baggage-ai

# Test alert
curl -X POST http://prometheus-alertmanager:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "info"},
    "annotations": {"summary": "Test alert from Baggage AI"}
  }]'
```

---

## Backup & Disaster Recovery

### Automated Backups

```bash
# Deploy backup CronJob
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neo4j-backup
  namespace: baggage-ai
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: baggage-ai/backup:latest
            env:
            - name: BACKUP_TYPE
              value: "full"
            - name: S3_BUCKET
              value: "copa-baggage-ai-backups"
            command: ["/scripts/neo4j-backup.sh"]
          restartPolicy: OnFailure
EOF

# Manual backup
kubectl create job --from=cronjob/neo4j-backup neo4j-backup-manual -n baggage-ai

# View backup logs
kubectl logs job/neo4j-backup-manual -n baggage-ai
```

### Restore from Backup

```bash
# List available backups
aws s3 ls s3://copa-baggage-ai-backups/neo4j/

# Restore from specific backup
kubectl run neo4j-restore --image=baggage-ai/backup:latest -it --rm --restart=Never -- \
  /scripts/neo4j-restore.sh s3://copa-baggage-ai-backups/neo4j/neo4j_full_20251114_020000.backup.tar.gz --force

# Verify restore
kubectl exec -it neo4j-core1-0 -n baggage-ai -- \
  cypher-shell -u neo4j -p <PASSWORD> "MATCH (n) RETURN count(n);"
```

---

## Scaling & Performance

### Horizontal Pod Autoscaling

```bash
# View HPA status
kubectl get hpa -n baggage-ai

# Scale manually (override HPA temporarily)
kubectl scale deployment api-gateway --replicas=10 -n baggage-ai

# Stress test to trigger autoscaling
kubectl run -it --rm load-generator --image=busybox --restart=Never -- \
  sh -c "while true; do wget -q -O- http://api-gateway:8000/health; done"

# Watch pods scale
kubectl get pods -n baggage-ai -w
```

### Performance Tuning

```bash
# Update resource limits
kubectl set resources deployment api-gateway \
  --limits=cpu=4,memory=8Gi \
  --requests=cpu=2,memory=4Gi \
  -n baggage-ai

# Update JVM settings for Neo4j
kubectl set env statefulset/neo4j-cluster \
  NEO4J_dbms_memory_heap_max__size=4G \
  NEO4J_dbms_memory_pagecache_size=2G \
  -n baggage-ai
```

---

## Troubleshooting

### Common Issues

#### Pods not starting

```bash
# Check pod events
kubectl describe pod <POD_NAME> -n baggage-ai

# Check logs
kubectl logs <POD_NAME> -n baggage-ai --previous

# Check resource constraints
kubectl top nodes
kubectl top pods -n baggage-ai
```

#### Neo4j cluster not forming

```bash
# Check cluster status
kubectl exec neo4j-core1-0 -n baggage-ai -- \
  cypher-shell -u neo4j -p <PASSWORD> "SHOW SERVERS;"

# Check connectivity between nodes
kubectl exec neo4j-core1-0 -n baggage-ai -- ping neo4j-core2-0.neo4j

# View Neo4j logs
kubectl logs neo4j-core1-0 -n baggage-ai
```

#### High API latency

```bash
# Check metrics
kubectl port-forward svc/api-gateway 8000:8000 -n baggage-ai
curl http://localhost:8000/metrics | grep http_request_duration

# Check database connection pool
curl http://localhost:8000/debug/pool-stats

# Scale up API Gateway
kubectl scale deployment api-gateway --replicas=10 -n baggage-ai
```

### Support Contacts

- **Copa Airlines IT**: it-support@copaair.com
- **Baggage AI DevOps**: baggage-ai-ops@copaair.com
- **Emergency Hotline**: +507-XXXX-XXXX

---

## Maintenance Windows

- **Backups**: Daily at 2:00 AM UTC
- **Security Patches**: Sundays 1:00-3:00 AM UTC
- **Major Updates**: First Sunday of month, 1:00-5:00 AM UTC

---

## License

Copyright © 2024 Copa Airlines. All rights reserved.

---

**Document Version**: 1.0.0
**Last Review**: 2025-11-14
**Next Review**: 2025-12-14
