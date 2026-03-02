# API Reference

The orchestrator exposes a REST API and a WebSocket endpoint.

## Base URL
All endpoints are prefixed with `http://localhost:8000` (configurable via `PORT`).

## Authentication
All REST endpoints except `/health`, `/metrics`, `/docs`, and `/openapi.json` require a JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

## REST Endpoints

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "components": {
    "database": {"status": "healthy", "latency_ms": 12},
    "redis": {"status": "healthy", "latency_ms": 3}
  }
}
```

### Session Management

#### Create Session

```
POST /sessions
```

Request Body:

```json
{
  "user_id": "user-123",
  "metadata": {"client": "cli"},
  "ttl_days": 7
}
```

Response:

```json
{
  "id": "session-456",
  "user_id": "user-123",
  "created_at": "2024-01-01T00:00:00Z",
  "last_active": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-08T00:00:00Z"
}
```

#### Get Session

```
GET /sessions/{session_id}
```

#### Delete Session

```
DELETE /sessions/{session_id}
```

#### List Sessions

```
GET /sessions?skip=0&limit=100
```

### Agent Management

#### List Agents

```
GET /agents
```

Response:

```json
[
  {
    "type": "planner",
    "status": "active",
    "tasks_completed": 1245,
    "tasks_failed": 23,
    "queue_size": 3,
    "memory_usage_mb": 156,
    "cpu_usage_percent": 12.5
  },
  {
    "type": "executor",
    "status": "busy",
    "tasks_completed": 3456,
    "tasks_failed": 67,
    "queue_size": 7,
    "memory_usage_mb": 234,
    "cpu_usage_percent": 45.2
  }
]
```

#### Get Agent Metrics

```
GET /agents/{agent_type}/metrics?hours=24
```

Response:

```json
{
  "agent_type": "planner",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-02T00:00:00Z",
  "tasks_completed": 456,
  "tasks_failed": 12,
  "avg_response_time_ms": 234,
  "p95_response_time_ms": 567,
  "p99_response_time_ms": 890,
  "tokens_used": 15000,
  "cost_estimate": 0.45,
  "error_rate": 2.6
}
```

#### Control Agent (Admin Only)

```
POST /agents/{agent_type}/control
```

Request Body:

```json
{
  "action": "scale",
  "replicas": 5,
  "force": false
}
```

### Tool Management

#### List Tools

```
GET /tools
```

Response:

```json
[
  {
    "name": "shell",
    "type": "system",
    "description": "Execute shell commands",
    "version": "1.0.0",
    "enabled": true,
    "commands": [],
    "rate_limit": null
  },
  {
    "name": "kubernetes",
    "type": "system",
    "description": "Manage Kubernetes clusters",
    "version": "1.0.0",
    "enabled": true,
    "commands": ["get", "describe", "logs", "exec", "apply", "delete"],
    "rate_limit": 100
  }
]
```

#### Execute Tool

```
POST /tools/{tool_name}/execute
```

Request Body:

```json
{
  "cmd": "get pods",
  "namespace": "default"
}
```

Response:

```json
{
  "execution_id": "exec_1704067200_abc123",
  "status": "completed",
  "result": {
    "stdout": "NAME                     READY   STATUS    RESTARTS   AGE\nnginx-6799fc88d8-5xgk2   1/1     Running   0          5d\n",
    "stderr": "",
    "returncode": 0,
    "command": "kubectl get pods -n default -o yaml"
  }
}
```

#### Get Execution History

```
GET /tools/executions/history?tool_name=kubernetes&limit=50
```

### Metrics

#### Prometheus Metrics

```
GET /metrics
```

Returns Prometheus-formatted metrics.

#### System Summary (Admin Only)

```
GET /metrics/summary
```

Response:

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "agents": {
    "planner": {"tasks_completed": 1245, "tasks_failed": 23},
    "executor": {"tasks_completed": 3456, "tasks_failed": 67}
  },
  "tools": {
    "kubernetes": {"total": 456, "successful": 452, "failed": 4},
    "docker": {"total": 234, "successful": 230, "failed": 4}
  },
  "sessions": {
    "total_sessions": 89,
    "active_sessions": 47,
    "avg_messages_per_session": 12.3
  },
  "queues": {
    "planner": 3,
    "executor": 7,
    "coder": 2,
    "debugger": 1,
    "optimizer": 0,
    "reflector": 0
  },
  "errors": {
    "total_requests": 15234,
    "total_errors": 156,
    "error_rate": 1.02
  }
}
```

## WebSocket API

### Connection

```
ws://localhost:8000/ws/{session_id}
```

### Message Format

All messages are JSON objects with a `type` field.

### Client Messages

**User Message:**

```json
{
  "type": "message",
  "role": "user",
  "content": "Deploy my app to Kubernetes",
  "metadata": {
    "session": "workspace-1"
  }
}
```

**Cancel Stream:**

```json
{
  "type": "cancel",
  "streamId": "stream_123"
}
```

**Ping:**

```json
{
  "type": "ping"
}
```

### Server Messages

**Agent Response:**

```json
{
  "type": "agent",
  "session_id": "session-123",
  "message": {
    "id": "msg-456",
    "role": "agent",
    "content": "I'll help you deploy that app.",
    "metadata": {
      "agent_type": "planner",
      "processing_time_ms": 234
    },
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

**Tool Result:**

```json
{
  "type": "tool",
  "execution_id": "exec_123",
  "tool": "kubernetes",
  "result": {
    "stdout": "deployment.apps/nginx created",
    "stderr": "",
    "returncode": 0
  },
  "duration_ms": 1234
}
```

**Token Stream:**

```json
{
  "type": "token",
  "streamId": "stream_123",
  "token": "deploy"
}
```

**Complete:**

```json
{
  "type": "complete",
  "streamId": "stream_123",
  "fullText": "deployment.apps/nginx created\nservice/nginx exposed",
  "usage": {
    "promptTokens": 45,
    "completionTokens": 12,
    "totalTokens": 57
  }
}
```

**Error:**

```json
{
  "type": "error",
  "message": "Tool execution failed: timeout after 30s"
}
```

**Pong:**

```json
{
  "type": "pong",
  "timestamp": 1704067200000
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Unexpected error |
| 502 | Bad Gateway - Upstream service failed |
| 503 | Service Unavailable - System overloaded |
| 504 | Gateway Timeout - Upstream timeout |

## Rate Limiting

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
```

## Pagination

List endpoints support pagination with `skip` and `limit` parameters:

```
GET /sessions?skip=20&limit=10
```
