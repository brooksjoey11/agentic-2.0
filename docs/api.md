# API Reference

## Base URL
`http://localhost:8000`

## Authentication
All endpoints (except `/health`) require a Bearer token in the `Authorization` header.

---

## Health

### `GET /health/`
Returns orchestrator health status.

**Response**
```json
{ "status": "ok" }
```

### `GET /health/ready`
Returns readiness status.

---

## Sessions

### `GET /sessions/`
List all sessions.

### `POST /sessions/`
Create a new session.

**Body**
```json
{ "name": "my-session", "description": "optional" }
```

### `GET /sessions/{session_id}`
Get a session by ID.

### `DELETE /sessions/{session_id}`
Delete a session.

---

## Agents

### `GET /agents/`
List all agents.

### `POST /agents/`
Register a new agent.

**Body**
```json
{ "name": "my-agent", "type": "worker", "config": {} }
```

### `GET /agents/{agent_id}`
Get an agent by ID.

### `DELETE /agents/{agent_id}`
Delete an agent.

---

## Tools

### `GET /tools/`
List all tools.

### `POST /tools/`
Register a new tool.

### `GET /tools/{tool_id}`
Get a tool by ID.

---

## Metrics

### `GET /metrics/`
Prometheus metrics endpoint.
