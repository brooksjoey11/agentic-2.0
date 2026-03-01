# Contributing

Thank you for your interest in contributing to agentic-shell!

## Getting Started

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Make your changes following the guidelines below.
4. Run tests and linting: `make test && make lint`.
5. Open a pull request.

## Code Style

- Python code is formatted with **Black** and **isort**.
- Type hints are required for all public functions and methods.
- Run `make fmt` before committing.

## Testing

- Unit tests live in `tests/unit/`.
- Integration tests live in `tests/integration/`.
- Load tests live in `tests/load/`.
- All new features must include tests.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new agent type
fix: correct session expiry logic
docs: update API reference
```

## Pull Requests

- Keep PRs focused on a single concern.
- Reference the related issue: `Closes #123`.
- Ensure CI is green before requesting a review.

## Reporting Issues

Open an issue with a clear description, reproduction steps, and the expected vs. actual behaviour.
