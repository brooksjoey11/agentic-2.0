# **AGENTIC SHELL 2.0 - PRODUCTION GRADE REPOSITORY**

```
agentic-shell/
├── README.md
├── setup.sh
├── install.sh
├── docker-compose.yml
├── kubernetes/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── src/
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── models/
│   │   └── config.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── coder.py
│   │   ├── debugger.py
│   │   ├── optimizer.py
│   │   └── reflector.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── kubernetes.py
│   │   ├── docker.py
│   │   ├── aws.py
│   │   ├── github.py
│   │   └── shell.py
│   └── client/
│       ├── cli.py
│       ├── rich_ui.py
│       └── websocket.py
├── configs/
│   ├── agent-pool.yml
│   ├── tool-registry.yml
│   ├── logging.conf
│   └── prometheus/
├── scripts/
│   ├── init-db.sql
│   ├── create-admin.sh
│   └── backup.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── deployment.md
│   └── contributing.md
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
├── poetry.lock
├── requirements.txt
├── Dockerfile
└── LICENSE
```

---

## **README.md**

```markdown
# 🤖 Agentic Shell 2.0 - Distributed Cognitive Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/k8s-supported-blue)](https://kubernetes.io)

**Agentic Shell 2.0** is a production-grade, distributed cognitive architecture that transforms your terminal into a multi-agent AI system. Deploy specialized agents that coordinate, execute tools, and learn from interactions across a scalable cloud-native infrastructure.

```ascii
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗     ║
║  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝     ║
║  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║          ║
║  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║          ║
║  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗     ║
║  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝     ║
║                                                               ║
║              SHELL 2.0 - DISTRIBUTED COGNITIVE               ║
╚═══════════════════════════════════════════════════════════════╝
```

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Agent Pool](#-agent-pool)
- [Tool Registry](#-tool-registry)
- [Production Deployment](#-production-deployment)
- [Monitoring](#-monitoring)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 🧠 **Cognitive Architecture**
- **Multi-Agent System** - 6 specialized agents working in concert
- **Dynamic Orchestration** - Intelligent task routing based on intent
- **Distributed Processing** - Scale horizontally across nodes
- **State Persistence** - PostgreSQL with vector embeddings
- **Message Queuing** - RabbitMQ for reliable async communication

### 🔧 **Tool Ecosystem**
- **Kubernetes Integration** - Manage clusters, pods, services
- **Docker Engine** - Build, run, orchestrate containers
- **AWS Cloud** - EC2, S3, Lambda, and more
- **GitHub Actions** - CI/CD pipeline management
- **Shell Execution** - Local and remote command execution
- **Extensible Registry** - Add custom tools dynamically

### 🚀 **Production Features**
- **High Availability** - Multi-replica deployments
- **Auto-scaling** - K8s HPA based on queue depth
- **Service Discovery** - Consul for dynamic registration
- **Metrics & Monitoring** - Prometheus + Grafana
- **Distributed Tracing** - OpenTelemetry support
- **Circuit Breaking** - Resilience4j patterns

### 🎨 **Rich User Experience**
- **WebSocket Streaming** - Real-time agent responses
- **Rich Terminal UI** - Colors, panels, markdown rendering
- **Session Persistence** - Resume conversations anywhere
- **Multi-modal Output** - Text, code, JSON, tables

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   WebSocket     │  │    REST API     │  │    Terminal     │     │
│  │    Client       │  │    Client       │  │     Client      │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
└───────────┼─────────────────────┼─────────────────────┼─────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR LAYER                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Gateway                           │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │    │
│  │  │  Auth    │ │  Router  │ │  Queue   │ │  Cache   │       │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Redis      │  │   RabbitMQ   │  │   Consul     │              │
│  │   Cache      │  │    Queue     │  │   Registry   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  PostgreSQL  │  │    etcd      │  │  Prometheus  │              │
│  │   Storage    │  │   Config     │  │   Metrics    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│    AGENT POOL LAYER   │ │    AGENT POOL LAYER   │ │    AGENT POOL LAYER   │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │   Planner       │  │ │  │   Executor      │  │ │  │    Coder        │  │
│  │   Agent         │  │ │  │   Agent         │  │ │  │    Agent        │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │   Debugger      │  │ │  │   Optimizer     │  │ │  │   Reflector     │  │
│  │   Agent         │  │ │  │   Agent         │  │ │  │   Agent         │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
└───────────┬───────────┘ └───────────┬───────────┘ └───────────┬───────────┘
            │                         │                         │
            ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         TOOL EXECUTION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Kubernetes  │  │   Docker     │  │     AWS      │              │
│  │    Tools     │  │   Tools      │  │    Tools     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   GitHub     │  │    Shell     │  │   Custom     │              │
│  │   Tools      │  │   Tools      │  │   Tools      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourorg/agentic-shell.git
cd agentic-shell

# Run the setup script (detects OS and installs dependencies)
./setup.sh

# Configure your API key
cp .env.example .env
# Edit .env with your Mistral API key

# Start the system
make up

# Connect to the shell
agentic-shell
```

## 📦 Installation

### Prerequisites

- **Linux/macOS/WSL2** (Windows support via Docker)
- **Python 3.11+**
- **Docker 20.10+** & Docker Compose
- **8GB RAM minimum** (16GB recommended)
- **20GB free disk space**

### Option 1: One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/yourorg/agentic-shell/main/install.sh | bash
```

### Option 2: Manual Install

```bash
# 1. Clone
git clone https://github.com/yourorg/agentic-shell.git
cd agentic-shell

# 2. Run setup
chmod +x setup.sh
./setup.sh --production

# 3. Configure
cp .env.example .env
vim .env  # Add your Mistral API key

# 4. Launch
make prod-up
```

### Option 3: Development Install

```bash
# For development with hot-reload
make dev-setup
make dev-up
```

## ⚙️ Configuration

### Environment Variables

```bash
# .env example
MISTRAL_API_KEY=your_api_key_here
AGENT_ID=ag_019ca619014874dfbef495f2174d390d

# Database
POSTGRES_DB=agentic
POSTGRES_USER=agentic
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_USER=agentic
RABBITMQ_PASS=secure_password

# Service Registry
CONSUL_HOST=consul
CONSUL_PORT=8500

# Scaling
PLANNER_REPLICAS=3
EXECUTOR_REPLICAS=5
CODER_REPLICAS=4
DEBUGGER_REPLICAS=2
OPTIMIZER_REPLICAS=2
REFLECTOR_REPLICAS=1
```

### Agent Pool Configuration

```yaml
# configs/agent-pool.yml
agents:
  planner:
    model: mistral-large-latest
    agent_id: ${AGENT_ID}
    specialization: task_decomposition
    system_prompt: |
      You decompose complex requests into actionable steps.
      Output JSON with plan and required tools.
    max_concurrent: 5
    timeout_seconds: 30
    retry_policy:
      max_retries: 3
      backoff: exponential

  executor:
    model: mistral-large-latest
    agent_id: ${AGENT_ID}
    specialization: command_execution
    tools: [shell, kubernetes, docker, aws]
    max_concurrent: 10
    timeout_seconds: 60

  coder:
    model: mistral-large-latest
    agent_id: ${AGENT_ID}
    specialization: code_generation
    languages: [python, bash, go, javascript]
    max_concurrent: 8

  debugger:
    model: mistral-large-latest
    agent_id: ${AGENT_ID}
    specialization: error_analysis
    context_window: 10000
    max_concurrent: 4

  optimizer:
    model: mistral-large-latest
    agent_id: ${AGENT_ID}
    specialization: performance_tuning
    metrics_tools: [prometheus, grafana]
    max_concurrent: 2

  reflector:
    model: mistral-large-latest
    agent_id: ${AGENT_ID}
    specialization: learning_from_history
    memory_size: 1000
    max_concurrent: 1
```

### Tool Registry

```yaml
# configs/tool-registry.yml
tools:
  kubernetes:
    type: system
    command: kubectl
    auth_method: kubeconfig
    kubeconfig_path: ~/.kube/config
    allowed_commands:
      - get
      - describe
      - logs
      - exec
      - apply
      - delete
    rate_limit: 100/minute

  docker:
    type: system
    command: docker
    socket: /var/run/docker.sock
    allowed_commands:
      - run
      - exec
      - build
      - push
      - pull
      - ps
      - images
    rate_limit: 50/minute

  aws:
    type: cloud
    service: ec2,s3,lambda
    auth_method: iam
    profile: default
    region: us-east-1
    rate_limit: 1000/hour

  github:
    type: api
    base_url: https://api.github.com
    auth_method: token
    token_env: GITHUB_TOKEN
    rate_limit: 5000/hour

  shell:
    type: system
    dangerous_commands: []  # Empty = no restrictions
    working_dir: /tmp
    timeout: 300
    env_vars:
      - PATH
      - HOME
```

## 🎮 Usage

### Starting the Client

```bash
# Basic usage
agentic-shell

# Connect to remote orchestrator
agentic-shell --server ws://orchestrator.prod:8000/ws

# Resume specific session
agentic-shell --session my-workspace-123

# Debug mode
agentic-shell --debug
```

### Interactive Commands

```bash
You> /help                    # Show available commands
You> /agents                  # List active agents
You> /stats                   # Show system metrics
You> /history                 # Show conversation history
You> /session save my-project # Save session state
You> /session load my-project # Load saved session
You> /tool list               # List available tools
You> /tool enable kubernetes  # Enable a tool
You> /exit                    # Exit shell
```

### Example Sessions

#### Multi-Agent Coordination

```bash
You> Deploy a web app to Kubernetes with monitoring

🤖 Planner> I'll coordinate this deployment:
  1. Generate deployment manifests (Coder)
  2. Apply to Kubernetes (Executor)
  3. Configure monitoring (Optimizer)
  4. Verify deployment (Debugger)

🤖 Coder> Generating Kubernetes manifests:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
```
```
🤖 Executor> Applying to Kubernetes:
✅ Deployment created
✅ Service exposed on port 80

🤖 Optimizer> Configuring Prometheus monitoring:
✅ ServiceMonitor added
✅ Grafana dashboard imported

🤖 Debugger> Verification complete:
✅ All pods running (3/3)
✅ Service reachable
✅ Metrics flowing
```

#### Complex Tool Chain

```bash
You> Find all large log files and analyze for errors

🤖 Planner> Executing multi-step analysis:
  1. Search filesystem for logs
  2. Filter by size >100MB
  3. Analyze for errors
  4. Generate report

🔧 Executing: find /var/log -type f -size +100M -name "*.log"
Output:
/var/log/syslog.1 (124MB)
/var/log/nginx/access.log (356MB)
/var/log/mysql/slow.log (189MB)

🔧 Analyzing errors in /var/log/nginx/access.log:
Pattern: "500|502|503|504|error"
Found 47 error entries in last hour
Top errors:
  502 Bad Gateway (23 times)
  504 Timeout (15 times)

📊 Report generated:
- Total logs analyzed: 3 files (669MB)
- Error rate: 7.2%
- Recommendations:
  1. Increase PHP-FPM workers
  2. Add Redis caching
  3. Enable nginx buffering
```

## 🏭 Production Deployment

### Docker Compose (Single Node)

```bash
# Production mode
make prod-up

# Scale specific agents
docker-compose up -d --scale planner=5 --scale executor=10

# View logs
docker-compose logs -f orchestrator
```

### Kubernetes (Multi-Node)

```bash
# Deploy to K8s
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml

# Scale
kubectl scale deployment planner --replicas=10
kubectl scale deployment executor --replicas=20

# Expose
kubectl port-forward service/orchestrator 8000:8000
```

### Helm Chart

```bash
# Add repo
helm repo add agentic-shell https://charts.agentic-shell.io

# Install
helm upgrade --install agentic-shell agentic-shell/agentic-shell \
  --set mistral.apiKey=$MISTRAL_API_KEY \
  --set replicas.planner=5 \
  --set replicas.executor=10
```

## 📊 Monitoring

### Prometheus Metrics

```yaml
# Available metrics at /metrics
agentic_requests_total{agent="planner",status="success"} 1245
agentic_requests_total{agent="executor",status="error"} 23
agentic_tool_executions{tool="kubernetes"} 456
agentic_queue_depth{queue="planner"} 3
agentic_response_time_seconds{agent="planner"} 0.234
agentic_session_count{status="active"} 47
```

### Grafana Dashboards

Pre-built dashboards available in `configs/grafana/`:
- **System Overview** - Cluster health, resource usage
- **Agent Performance** - Response times, error rates
- **Tool Usage** - Execution counts, success rates
- **Session Analytics** - Active users, message volume

### Alerts

```yaml
# Prometheus alerts
groups:
  - name: agentic-shell
    rules:
      - alert: HighErrorRate
        expr: rate(agentic_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Error rate >10% for 5 minutes"
      
      - alert: QueueBacklog
        expr: agentic_queue_depth > 100
        for: 2m
        annotations:
          summary: "Queue backlog exceeds 100 messages"
```

## 📚 API Reference

### REST API

```bash
# Health check
GET /health
Response: {"status": "healthy", "version": "2.0.0"}

# Session stats
GET /stats
Response: {
  "active_sessions": 47,
  "total_messages": 15234,
  "avg_response_time": 0.345
}

# Agent status
GET /agents
Response: {
  "planner": {"status": "active", "tasks": 234},
  "executor": {"status": "active", "tasks": 567}
}
```

### WebSocket API

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws/session-123');

// Send message
ws.send(JSON.stringify({
  role: 'user',
  content: 'Deploy my app',
  metadata: { session: 'workspace-1' }
}));

// Receive response
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response.content);
};
```

### Python SDK

```python
from agentic_shell import AgenticClient

client = AgenticClient(
    server="ws://orchestrator.prod:8000/ws",
    api_key="your-key"
)

# Interactive session
async with client.session() as session:
    response = await session.ask("Deploy to Kubernetes")
    print(response.content)
    
    # Tool execution
    result = await session.execute_tool(
        "kubernetes",
        cmd="get pods"
    )
```

## 🛠 Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/yourorg/agentic-shell.git
cd agentic-shell
make dev-setup

# Run tests
make test
make test-integration
make test-load

# Run linters
make lint
make format

# Build
make build
make docker-build
```

### Project Structure

```
agentic-shell/
├── src/
│   ├── orchestrator/     # FastAPI orchestrator
│   ├── agents/           # Agent implementations
│   │   ├── base.py       # Base agent class
│   │   ├── planner.py    # Task decomposition
│   │   ├── executor.py   # Command execution
│   │   ├── coder.py      # Code generation
│   │   ├── debugger.py   # Error analysis
│   │   ├── optimizer.py  # Performance tuning
│   │   └── reflector.py  # Learning from history
│   ├── tools/            # Tool implementations
│   │   ├── registry.py   # Tool registration
│   │   ├── kubernetes.py # K8s operations
│   │   ├── docker.py     # Docker operations
│   │   ├── aws.py        # AWS operations
│   │   └── shell.py      # Shell execution
│   └── client/           # Client SDK
├── tests/                # Test suite
├── docs/                 # Documentation
├── configs/              # Configuration files
├── scripts/              # Utility scripts
└── kubernetes/           # K8s manifests
```

```
