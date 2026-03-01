# Deployment Guide

## Local Development

```bash
# 1. Clone the repository
git clone https://github.com/your-org/agentic-shell.git
cd agentic-shell

# 2. Bootstrap the environment
bash setup.sh

# 3. Edit .env
cp .env.example .env
# fill in your credentials

# 4. Start the stack
make docker-up

# 5. Run migrations / init DB
make init-db

# 6. Start the dev server (hot reload)
make dev
```

## Docker Compose (Staging)

```bash
make docker-build
make docker-up
```

## Kubernetes (Production)

```bash
# Apply all manifests
make k8s-deploy

# Tear down
make k8s-delete
```

### Prerequisites
- `kubectl` configured with cluster access
- A container registry with the `orchestrator` and `worker` images pushed.

### Secrets
Create Kubernetes secrets before deploying:

```bash
kubectl create secret generic agentic-shell-secrets \
  --from-literal=SECRET_KEY=<value> \
  --from-literal=DATABASE_URL=<value> \
  -n agentic-shell
```

## Environment Variables

See [`.env.example`](../.env.example) for the full list of configurable variables.
