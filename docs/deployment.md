# Deployment Guide

## Prerequisites

- **Docker** 20.10+ and Docker Compose
- **Kubernetes** 1.24+ (for production deployment)
- **Helm** 3.8+ (optional)
- **Python** 3.11+ (for local development)
- **PostgreSQL** 15+ (if running without Docker)
- **Redis** 7+ (if running without Docker)
- **RabbitMQ** 3.12+ (if running without Docker)
- **etcd** 3.5+ (if running without Docker)
- **Consul** 1.15+ (if running without Docker)

## Environment Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MISTRAL_API_KEY` | Mistral AI API key | `your-api-key` |
| `AGENT_ID` | Mistral agent ID | `ag_019ca619014874dfbef495f2174d390d` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `secure-password` |
| `RABBITMQ_PASS` | RabbitMQ password | `secure-password` |
| `JWT_SECRET` | JWT signing secret | `random-32-byte-string` |
| `ENCRYPTION_KEY` | AES-256-GCM encryption key | `base64-32-byte-key` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Orchestrator HTTP port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARN, ERROR) |
| `LOG_FORMAT` | `json` | Log format (json, text) |
| `PLANNER_REPLICAS` | `3` | Number of planner replicas |
| `EXECUTOR_REPLICAS` | `5` | Number of executor replicas |
| `CODER_REPLICAS` | `4` | Number of coder replicas |
| `DEBUGGER_REPLICAS` | `2` | Number of debugger replicas |
| `OPTIMIZER_REPLICAS` | `2` | Number of optimizer replicas |
| `REFLECTOR_REPLICAS` | `1` | Number of reflector replicas |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `FREE_TIER_LIMIT` | `5` | Free tier daily limit |
| `PRO_TIER_LIMIT` | `100` | Pro tier daily limit |
| `ENTERPRISE_TIER_LIMIT` | `1000` | Enterprise tier daily limit |

## Deployment Options

### Option 1: Local Development with Docker Compose

```bash
# Clone repository
git clone https://github.com/yourorg/agentic-shell.git
cd agentic-shell

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down
```

Services started:

· orchestrator (port 8000)
· planner (3 replicas)
· executor (5 replicas)
· coder (4 replicas)
· debugger (2 replicas)
· optimizer (2 replicas)
· reflector (1 replica)
· postgres (port 5432)
· redis (port 6379)
· rabbitmq (ports 5672, 15672)
· etcd (port 2379)
· consul (port 8500)
· prometheus (port 9090)
· grafana (port 3000)

Option 2: Production with Kubernetes

Prerequisites

· Kubernetes cluster (minimum 3 nodes, 8GB RAM each)
· kubectl configured
· Helm 3.8+ (optional)

Deploy with kubectl

```bash
# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Create secrets (edit first!)
kubectl create secret generic agentic-shell-secrets \
  --namespace agentic-shell \
  --from-literal=MISTRAL_API_KEY=your-key \
  --from-literal=POSTGRES_PASSWORD=secure-password \
  --from-literal=RABBITMQ_PASS=secure-password \
  --from-literal=JWT_SECRET=random-32-byte-string \
  --from-literal=GITHUB_TOKEN=your-token

# Deploy config maps
kubectl apply -f kubernetes/configmap.yaml

# Deploy services
kubectl apply -f kubernetes/service.yaml

# Deploy deployments
kubectl apply -f kubernetes/deployment.yaml

# Deploy HPA
kubectl apply -f kubernetes/hpa.yaml

# Deploy ingress (optional)
kubectl apply -f kubernetes/ingress.yaml

# Check status
kubectl get all -n agentic-shell
kubectl get hpa -n agentic-shell
```

Deploy with Kustomize

```bash
# Deploy all resources
kubectl apply -k kubernetes/

# Override image tags
kubectl apply -k kubernetes/overlays/production
```

Deploy with Helm

```bash
# Add repository
helm repo add agentic-shell https://charts.agentic-shell.io

# Install with custom values
helm upgrade --install agentic-shell agentic-shell/agentic-shell \
  --namespace agentic-shell \
  --create-namespace \
  --set mistral.apiKey=your-key \
  --set postgres.password=secure-password \
  --set rabbitmq.password=secure-password \
  --set jwt.secret=random-32-byte-string \
  --set replicas.planner=5 \
  --set replicas.executor=10 \
  --set ingress.enabled=true \
  --set ingress.host=shell.agentic.ai
```

Option 3: Manual Installation (Bare Metal)

```bash
# Clone repository
git clone https://github.com/yourorg/agentic-shell.git
cd agentic-shell

# Install system dependencies
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql redis-server rabbitmq-server etcd consul

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Initialize database
psql -U postgres -c "CREATE DATABASE agentic;"
psql -U postgres -c "CREATE USER agentic WITH PASSWORD 'agentic123';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE agentic TO agentic;"
cat scripts/init-db.sql | psql -U agentic -d agentic

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services (use systemd or process manager)
# PostgreSQL, Redis, RabbitMQ, etcd, Consul should be running

# Start orchestrator
python -m src.orchestrator.main &

# Start agents (one per type)
AGENT_TYPE=planner python -m src.agents.worker &
AGENT_TYPE=executor python -m src.agents.worker &
AGENT_TYPE=coder python -m src.agents.worker &
AGENT_TYPE=debugger python -m src.agents.worker &
AGENT_TYPE=optimizer python -m src.agents.worker &
AGENT_TYPE=reflector python -m src.agents.worker &
```

Scaling

Horizontal Scaling

The system scales horizontally by adding more replicas of stateless components:

· Orchestrator: Scales based on CPU and request rate
· Agents: Scales based on queue depth (configured via HPA)

```bash
# Scale with kubectl
kubectl scale deployment orchestrator --replicas=5 -n agentic-shell
kubectl scale deployment executor --replicas=20 -n agentic-shell

# Scale with docker-compose
docker-compose up -d --scale planner=5 --scale executor=10
```

Auto-scaling with HPA

The Kubernetes deployment includes HPA configurations:

· Orchestrator: Scales at 70% CPU or 80% memory, or queue depth > 10
· Planner: Scales at 70% CPU or queue depth > 5
· Executor: Scales at 70% CPU or queue depth > 10

Database Scaling

PostgreSQL can be scaled vertically (larger instances) or horizontally with read replicas:

```yaml
# docker-compose with read replica
postgres-master:
  image: postgres:15

postgres-replica:
  image: postgres:15
  command: |
    postgres -c 'wal_level=replica' \
             -c 'max_wal_senders=10' \
             -c 'hot_standby=on'
```

Monitoring

Prometheus Metrics

Metrics are exposed at /metrics on port 8000 (orchestrator) and port 8001 (agents).

Key metrics:

· orchestrator_requests_total - Request count by endpoint/method/status
· orchestrator_response_time_seconds - Request latency
· agent_requests_total - Agent task count by type/status
· agent_processing_time_seconds - Agent processing latency
· queue_depth - Current queue depth by agent type
· tool_executions_total - Tool executions by tool/status

Grafana Dashboards

Pre-built dashboards are available in configs/grafana/:

```bash
# Import dashboards
kubectl port-forward service/grafana 3000:3000 -n agentic-shell
# Access http://localhost:3000 (admin/admin)
# Import JSON files from configs/grafana/dashboards/
```

Logging

Logs are structured JSON with correlation IDs:

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "service": "orchestrator",
  "correlation_id": "req_123",
  "message": "Request processed",
  "method": "POST",
  "path": "/tools/shell/execute",
  "duration_ms": 234,
  "status": 200
}
```

Tracing

OpenTelemetry tracing is enabled for distributed tracing:

```python
# Configure exporters
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
```

Backup and Recovery

Database Backup

```bash
# Manual backup
./scripts/backup.sh

# Scheduled backup (cron)
0 2 * * * /opt/agentic-shell/scripts/backup.sh
```

Database Restore

```bash
# Restore from backup
gunzip -c backups/agentic-shell-20240101_020000.sql.gz | psql -U agentic -d agentic
```

Disaster Recovery

1. Database failure: Promote read replica, restore from backup
2. Orchestrator failure: Kubernetes automatically restarts
3. Agent failure: Kubernetes automatically restarts, messages remain in queue
4. Message queue failure: Messages persist on disk, services reconnect
5. Region failure: Multi-region deployment with failover DNS

Security Hardening

Production Checklist

· Set strong JWT_SECRET (32+ random bytes)
· Set strong ENCRYPTION_KEY (32+ random bytes)
· Enable TLS for all external endpoints
· Configure network policies in Kubernetes
· Enable audit logging
· Set up rate limiting per tier
· Configure database connection limits
· Enable Prometheus authentication
· Set up Grafana authentication
· Rotate secrets regularly
· Run security scans (Trivy, Snyk)

Network Security

```yaml
# Kubernetes network policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agentic-shell-network-policy
spec:
  podSelector:
    matchLabels:
      app: orchestrator
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: client
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

Secret Management

```bash
# Use Kubernetes secrets
kubectl create secret generic agentic-shell-secrets \
  --from-literal=MISTRAL_API_KEY=$(aws secretsmanager get-secret-value --secret-id MISTRAL_API_KEY --query SecretString --output text)

# Or use HashiCorp Vault
vault kv put secret/agentic-shell MISTRAL_API_KEY=your-key
```

Troubleshooting

Common Issues

Connection refused to PostgreSQL

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection string
psql "postgresql://agentic:agentic123@localhost:5432/agentic"

# Verify network connectivity
nc -zv postgres 5432
```

RabbitMQ connection errors

```bash
# Check RabbitMQ status
docker exec agentic-rabbitmq rabbitmqctl status

# Verify credentials
docker exec agentic-rabbitmq rabbitmqctl list_users

# Check queue existence
docker exec agentic-rabbitmq rabbitmqctl list_queues
```

Agents not processing messages

```bash
# Check agent logs
kubectl logs -l agent-type=executor -n agentic-shell

# Check queue depth
kubectl exec -it orchestrator-xxx -- curl localhost:8000/agents/queue/depth

# Restart agent
kubectl delete pod -l agent-type=executor -n agentic-shell
```

High latency

```bash
# Check resource usage
kubectl top pods -n agentic-shell

# Check queue depths
curl localhost:8000/metrics | grep queue_depth

# Scale up if needed
kubectl scale deployment executor --replicas=10 -n agentic-shell
```

Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run client in debug mode
agentic-shell --debug

# Check trace logs
kubectl logs -l app=orchestrator --tail=100 -f | grep trace_id
```

Performance Tuning

Database Tuning

```sql
-- Increase connection limits
ALTER SYSTEM SET max_connections = 200;

-- Tune shared buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '4GB';

-- Enable query logging for slow queries
ALTER SYSTEM SET log_min_duration_statement = 1000;
```

Redis Tuning

```bash
# Configure max memory
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

RabbitMQ Tuning

```bash
# Set high watermark
rabbitmqctl set_vm_memory_high_watermark 0.8

# Increase queue length limit
rabbitmqctl set_policy queue-length-limit ".*" '{"max-length":10000}' --apply-to queues
```

Agent Tuning

```yaml
# configs/agent-pool.yml
agents:
  executor:
    max_concurrent: 20  # Increase concurrency
    timeout_seconds: 120  # Increase timeout
```

Rollback Procedures

Application Rollback

```bash
# Kubernetes rollback
kubectl rollout undo deployment/orchestrator -n agentic-shell

# Docker rollback
docker-compose pull orchestrator:previous-tag
docker-compose up -d orchestrator
```

Database Rollback

```bash
# Restore from backup
./scripts/restore-db.sh backups/agentic-shell-20240101_020000.sql.gz
```

Canary Deployments

```yaml
# kubernetes/canary.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator-canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orchestrator
      track: canary
  template:
    metadata:
      labels:
        app: orchestrator
        track: canary
    spec:
      containers:
      - name: orchestrator
        image: agentic-shell/orchestrator:canary
```

Route 10% of traffic to canary:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
spec:
  selector:
    app: orchestrator
  ports:
  - port: 8000
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: orchestrator
spec:
  hosts:
  - orchestrator
  http:
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: orchestrator-canary
        port:
          number: 8000
      weight: 100
  - route:
    - destination:
        host: orchestrator
        port:
          number: 8000
      weight: 90
    - destination:
        host: orchestrator-canary
        port:
          number: 8000
      weight: 10
```

Capacity Planning

Resource Estimates

Component CPU Memory Storage Replicas
Orchestrator 0.5 core 512 MB 1 GB 3-5
Planner 1 core 1 GB 1 GB 3-10
Executor 1 core 1 GB 1 GB 5-20
Coder 1 core 1 GB 1 GB 4-15
Debugger 1 core 1 GB 1 GB 2-8
Optimizer 1 core 1 GB 1 GB 2-6
Reflector 1 core 2 GB 10 GB 1-3
PostgreSQL 4 cores 16 GB 100 GB 1 master + replicas
Redis 2 cores 8 GB 20 GB 3
RabbitMQ 2 cores 4 GB 50 GB 3
etcd 1 core 2 GB 10 GB 3
Consul 1 core 2 GB 10 GB 3

Scaling Formulas

· Orchestrator replicas = max(3, ceil(requests_per_second / 200))
· Executor replicas = max(5, ceil(queue_depth / 10))
· Planner replicas = max(3, ceil(queue_depth / 5))
· Database connections = (orchestrator_replicas * 10) + (agent_replicas * 5)

