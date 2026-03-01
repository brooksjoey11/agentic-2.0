# agentic-shell

A distributed agentic orchestration platform for DevOps, coding, and infrastructure automation.

## Quick Start

```bash
# Clone and bootstrap
git clone https://github.com/your-org/agentic-shell.git
cd agentic-shell
bash setup.sh

# Start the full stack
make docker-up

# Run the development server (hot reload)
make dev
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing](docs/contributing.md)

## Project Structure

```
agentic-shell/
├── src/
│   ├── orchestrator/   # FastAPI orchestrator service
│   ├── agents/         # Specialised AI agents
│   ├── tools/          # Tool integrations (shell, k8s, docker, aws, github)
│   └── client/         # CLI and WebSocket client
├── configs/            # Runtime configuration files
├── kubernetes/         # Kubernetes manifests
├── scripts/            # Utility scripts
├── tests/              # Unit, integration, and load tests
└── docs/               # Documentation
```

## License

MIT — see [LICENSE](LICENSE).
