# Architecture Documentation

## System Overview

Agentic Shell 2.0 is a distributed cognitive architecture that transforms a terminal into a multi-agent AI system. It consists of six specialized agents working in concert, orchestrated by a central FastAPI service, communicating via message queues, and persisting state in PostgreSQL with vector embeddings for RAG capabilities.

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

## Component Architecture

### Orchestrator

The orchestrator is a FastAPI application that:
- Routes client requests to appropriate agents
- Manages WebSocket connections for real-time communication
- Enforces authentication and rate limiting
- Maintains session state
- Exposes metrics and health endpoints

**Key Files:**
- `src/orchestrator/main.py` - Main FastAPI application
- `src/orchestrator/routes/` - API route handlers
- `src/orchestrator/services/` - Business logic services
- `src/orchestrator/models/` - Pydantic models

### Agent Pool

Six specialized agents process messages asynchronously:

| Agent | Responsibility |
|-------|----------------|
| **Planner** | Decomposes complex requests into actionable steps |
| **Executor** | Executes shell commands and tool operations |
| **Coder** | Generates and analyzes code |
| **Debugger** | Diagnoses errors and suggests fixes |
| **Optimizer** | Improves performance and resource usage |
| **Reflector** | Maintains context and learns from history |

**Key Files:**
- `src/agents/base.py` - Base agent class
- `src/agents/worker.py` - Agent worker implementation

### Tool Registry

Tools provide controlled access to external systems:

| Tool | Description |
|------|-------------|
| **Shell** | Execute shell commands with timeout and output capture |
| **Kubernetes** | Manage Kubernetes clusters via kubectl |
| **Docker** | Control Docker containers and images |
| **AWS** | Interact with AWS services (EC2, S3, Lambda) |
| **GitHub** | Manage repositories, PRs, issues via GitHub CLI |

**Key Files:**
- `src/tools/registry.py` - Tool registration system
- `src/tools/*.py` - Individual tool implementations

### Data Layer

| Component | Purpose |
|-----------|---------|
| **PostgreSQL** | Primary datastore with vector embeddings for RAG |
| **Redis** | Caching, rate limiting, session storage |
| **RabbitMQ** | Asynchronous message queue for agent communication |
| **etcd** | Distributed configuration and coordination |
| **Consul** | Service discovery and health checking |

**Key Files:**
- `src/orchestrator/db/database.py` - PostgreSQL connection pool
- `src/orchestrator/cache/redis.py` - Redis client
- `src/orchestrator/messaging/rabbitmq.py` - RabbitMQ client
- `src/orchestrator/registry/etcd.py` - etcd client
- `src/orchestrator/discovery/consul.py` - Consul client

## Communication Flows

### Request Flow

1. Client connects via WebSocket to `/ws/{session_id}`
2. Client sends message → Orchestrator
3. Orchestrator routes message to appropriate agent via RabbitMQ
4. Agent processes message (may execute tools)
5. Agent publishes response to results queue
6. Orchestrator consumes response and forwards to client
7. Response stored in PostgreSQL

### Tool Execution Flow

1. Agent requests tool execution via JSON payload
2. Executor agent receives request
3. Tool executes with timeout and output capture
4. Result returned to agent
5. Execution logged to database for audit

## Deployment Architecture

### Development
- Docker Compose with all services
- Hot reload enabled
- Local volume mounts for code

### Production
- Kubernetes deployment with HPA
- Multiple replicas for high availability
- Service mesh for observability
- Persistent volumes for stateful services

## Security Architecture

- **Authentication**: JWT tokens via Google OAuth 2.0
- **Authorization**: Role-based access control (user/admin)
- **Encryption**: AES-256-GCM for API keys at rest
- **Network**: TLS for all external communications
- **Audit**: Comprehensive audit logging for all admin actions

## Observability

- **Metrics**: Prometheus metrics exposed at `/metrics`
- **Logging**: Structured JSON logs with correlation IDs
- **Tracing**: OpenTelemetry integration for distributed tracing
- **Health**: Comprehensive health checks at `/health`
- **Dashboards**: Grafana dashboards for system monitoring

## Failure Handling

- **Retries**: Exponential backoff with jitter for transient failures
- **Circuit Breaking**: Automatic failure detection and isolation
- **Dead Letter Queue**: Failed messages stored for inspection
- **Idempotency**: Key-based deduplication for critical operations
- **Graceful Degradation**: Fallback strategies for dependency failures

## Performance Characteristics

- **Throughput**: 1000+ requests/second (scales horizontally)
- **Latency**: p95 < 500ms for agent responses
- **Availability**: 99.9% uptime target
- **Scalability**: Linear scaling up to 100+ agent replicas
