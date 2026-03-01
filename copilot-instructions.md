# PROJECT EXTRACTION INSTRUCTIONS - READ CAREFULLY

## 🚨 CRITICAL CONSTRAINT
**DO NOT ALTER, MODIFY, OR EDIT ANY EXISTING PROJECT FILES OR CODE**
**DO NOT CHANGE A SINGLE CHARACTER OF THE SOURCE CODE**
**PRESERVE ALL FILES EXACTLY AS THEY APPEAR IN THE MARKDOWN SOURCE**

## PRIMARY DIRECTIVE
Extract all project files from the 4 markdown files located in the project root:
- `files-1.md`
- `files-2.md`
- `files-3.md`  
- `files-4.md`

## EXTRACTION RULES

### 1. File Detection
- Identify file paths from markdown headers, code block titles, and directory listings
- Look for patterns: `## **filename.ext**`, `### **path/to/file.ext**`, or code blocks immediately following file references
- Extract the complete file tree structure shown in the documents

### 2. Content Extraction
- Copy the ENTIRE contents of each code block that represents a file
- Preserve exact formatting, indentation, and line endings
- Include shebang lines, comments, and all code exactly as written

### 3. Directory Structure
Create the following directory structure (extracted from the markdown files):
agentic-shell/
├── .github/workflows/
├── .husky/
├── .vscode/
├── analytics/
├── client/src/
│ ├── components/
│ │ ├── feedback/
│ │ └── navigation/
│ ├── contexts/
│ ├── lib/
│ ├── pages/
│ │ ├── admin/
│ │ ├── auth/
│ │ ├── dashboard/
│ │ └── errors/
│ └── styles/
├── configs/
│ ├── consul/
│ ├── grafana/
│ │ ├── dashboards/
│ │ └── datasources/
│ └── prometheus/
├── docs/
├── drizzle/
├── kubernetes/
│ └── overlays/
│ └── production/
├── logging/
├── monitoring/
│ ├── grafana/
│ └── prometheus/
├── patches/
├── scripts/
├── server/
│ └── routers/
├── shared/
├── src/
│ ├── agents/
│ ├── client/
│ ├── orchestrator/
│ │ ├── cache/
│ │ ├── db/
│ │ ├── discovery/
│ │ ├── messaging/
│ │ ├── registry/
│ │ ├── routes/
│ │ ├── services/
│ │ └── models/
│ └── tools/
├── terraform/
├── tests/
│ ├── integration/
│ ├── k6/
│ ├── load/
│ └── unit/
└── uploads/

text

### 4. File Placement
- Place each extracted file in its correct path relative to project root
- Create any missing directories automatically
- Do not overwrite existing files unless they match the extracted content exactly

### 5. Validation
- Verify each extracted file has content (not empty)
- Ensure code blocks are complete (opening and closing tags match)
- Confirm no truncation occurred during extraction

### 6. Execution Order
1. Parse the file tree structure first
2. Create all necessary directories
3. Extract files in order of dependency (configuration files first, then source)
4. Verify final structure matches the documentation

## FILES TO EXTRACT (Partial List - See Markdown for Complete)

### Core Infrastructure
- `README.md` - Project documentation
- `setup.sh` - Installation script
- `install.sh` - One-liner installer
- `Makefile` - Build automation
- `docker-compose.yml` - Container orchestration
- `Dockerfile.orchestrator` - Orchestrator container
- `Dockerfile.worker` - Worker container
- `.env.example` - Environment template
- `pyproject.toml` - Python dependencies
- `requirements.txt` - Dependency list
- `.gitignore` - Git ignore rules

### Orchestrator Module
- `src/orchestrator/main.py` - FastAPI application
- `src/orchestrator/config.py` - Configuration management
- `src/orchestrator/auth.py` - Authentication
- `src/orchestrator/dependencies.py` - DI container
- `src/orchestrator/routes/*.py` - All route handlers
- `src/orchestrator/models/*.py` - Pydantic models
- `src/orchestrator/services/*.py` - Business logic
- `src/orchestrator/db/database.py` - PostgreSQL connection
- `src/orchestrator/cache/redis.py` - Redis client
- `src/orchestrator/messaging/rabbitmq.py` - Message queue
- `src/orchestrator/registry/etcd.py` - Service registry
- `src/orchestrator/discovery/consul.py` - Service discovery

### Agent System
- `src/agents/base.py` - Base agent class
- `src/agents/worker.py` - All 6 specialized agents

### Tool System
- `src/tools/registry.py` - Tool registration
- `src/tools/shell.py` - Shell execution
- `src/tools/kubernetes.py` - K8s management
- `src/tools/docker.py` - Docker operations
- `src/tools/aws.py` - AWS cloud
- `src/tools/github.py` - GitHub operations

### Client
- `src/client/cli.py` - Rich CLI client

### Configuration
- `configs/agent-pool.yml` - Agent configuration
- `configs/tool-registry.yml` - Tool definitions
- `configs/logging.conf` - Logging setup
- `configs/prometheus/prometheus.yml` - Metrics scraping

### Kubernetes Manifests
- `kubernetes/namespace.yaml`
- `kubernetes/configmap.yaml`
- `kubernetes/secrets.yaml`
- `kubernetes/deployment.yaml`
- `kubernetes/service.yaml`
- `kubernetes/ingress.yaml`
- `kubernetes/hpa.yaml`
- `kubernetes/kustomization.yaml`

### Database
- `scripts/init-db.sql` - PostgreSQL schema
- `drizzle/schema.ts` - Drizzle ORM schema

### Server (TypeScript)
- `server/index.ts` - Express server
- `server/pipeline.ts` - LLM pipeline
- `server/providerService.ts` - Provider management
- `server/configService.ts` - Configuration
- `server/logger.ts` - Pino logging
- `server/metrics.ts` - Prometheus metrics
- `server/auth.ts` - Google OAuth
- `server/health.ts` - Health checks
- `server/middleware.ts` - Express middleware
- `server/websocket.ts` - WebSocket server
- `server/jobQueue.ts` - BullMQ queue
- `server/redis.ts` - Redis client
- `server/db.ts` - Database client
- `server/audit.ts` - Audit logging
- `server/tracing.ts` - OpenTelemetry
- `server/rateLimit.ts` - Rate limiting
- `server/encryption.ts` - AES-256-GCM
- `server/worker.ts` - Background worker

### Client (React)
- `client/src/App.tsx` - Main application
- `client/src/index.css` - Brutalist styling
- `client/src/lib/trpc.ts` - tRPC client
- `client/src/contexts/*.tsx` - React contexts
- `client/src/components/*.tsx` - UI components
- `client/src/pages/*.tsx` - Page components

### CI/CD
- `.github/workflows/ci.yml` - GitHub Actions

### Documentation
- `docs/architecture.md`
- `docs/api.md`
- `docs/deployment.md`
- `docs/contributing.md`

## VERIFICATION CHECKLIST
- [ ] All directories created
- [ ] All files extracted
- [ ] No files modified from source
- [ ] File permissions set appropriately (executable for .sh files)
- [ ] Structure matches documentation

## COMPLETION SIGNAL
When finished, output: "✅ PROJECT EXTRACTION COMPLETE: [number] files extracted"