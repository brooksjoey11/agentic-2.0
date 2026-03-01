# Architecture

## Overview

agentic-shell is a distributed agentic orchestration platform that coordinates multiple specialised AI agents to perform complex DevOps, coding, and infrastructure tasks.

## Components

### Orchestrator
The FastAPI-based orchestrator exposes a REST API for managing sessions, agents, and tools. It acts as the central control plane.

### Agents
Each agent is a specialised worker that handles a specific category of tasks:
- **PlannerAgent** — decomposes high-level goals into executable steps.
- **ExecutorAgent** — runs planned steps using registered tools.
- **CoderAgent** — generates and reviews code.
- **DebuggerAgent** — diagnoses and fixes errors.
- **OptimizerAgent** — improves performance of code or configurations.
- **ReflectorAgent** — evaluates outcomes and refines strategy.
- **WorkerAgent** — generic queue consumer.

### Tools
Tools are callable modules that wrap external systems:
- Shell, Kubernetes, Docker, AWS, GitHub.

### Infrastructure
- **PostgreSQL** — persistent storage.
- **Redis** — caching and pub/sub.
- **RabbitMQ** — task queuing.
- **etcd** — service registry.
- **Consul** — service discovery.
- **Prometheus** — metrics collection.

## Data Flow

```
Client → Orchestrator → RabbitMQ → Worker Agents → Tools → External Systems
                       ↕
                  PostgreSQL / Redis
```
