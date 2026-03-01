# Contributing Guide

## Welcome

Thank you for considering contributing to Agentic Shell 2.0! This document outlines the process for contributing code, documentation, or issues to the project.

## Code of Conduct

All contributors must adhere to our Code of Conduct. Please read [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) before participating.

## Getting Started

### Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/agentic-shell.git
cd agentic-shell

# Set up development environment
make dev-setup

# Start development services
make dev-up

# Run tests
make test
```

Branch Structure

· main - Production-ready code
· develop - Integration branch for features
· feature/* - New features
· bugfix/* - Bug fixes
· release/* - Release preparation

Development Workflow

1. Find or Create an Issue

Check the issue tracker for existing issues or create a new one. Issues should be:

· Clear: Describe the problem or feature
· Reproducible: Include steps to reproduce bugs
· Actionable: Have a clear definition of done

2. Create a Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

3. Make Changes

Code Style

· Python: Follow PEP 8, use Black for formatting
· TypeScript: Follow ESLint configuration
· Shell scripts: Follow ShellCheck recommendations

```bash
# Format code
make format

# Lint code
make lint
```

Commit Messages

Follow Conventional Commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:

· feat: New feature
· fix: Bug fix
· docs: Documentation
· style: Formatting
· refactor: Code restructuring
· perf: Performance improvement
· test: Testing
· chore: Maintenance

Example:

```
feat(agents): add memory usage tracking to reflector agent

- Add psutil for memory monitoring
- Include memory stats in heartbeat
- Update agent metrics endpoint

Closes #123
```

4. Write Tests

All new code must include tests:

· Unit tests: Test individual functions/classes
· Integration tests: Test component interactions
· Load tests: Test performance characteristics

```bash
# Run unit tests
make test-unit

# Run integration tests
make test-integration

# Run load tests
make test-load

# Check coverage
make test-cov
```

Test Example

```python
# tests/unit/test_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from src.agents.planner import PlannerAgent

@pytest.mark.asyncio
async def test_planner_process_message():
    agent = PlannerAgent()
    agent.mistral = AsyncMock()
    agent.mistral.beta.conversations.start.return_value = Mock(
        outputs=[Mock(text='{"plan": ["step1"]}')]
    )
    
    result = await agent.process({
        "session_id": "test",
        "message": {"content": "Test message"}
    })
    
    assert "content" in result
    assert result["metadata"]["type"] == "plan"
```

5. Update Documentation

· Update README.md for user-facing changes
· Update docs/ for architectural changes
· Add docstrings to new functions/classes
· Update API documentation for endpoint changes

6. Run CI Checks Locally

```bash
# Run all checks
make ci

# This runs:
# - lint
# - typecheck
# - test
# - test-integration
# - build
```

7. Push Changes

```bash
git push origin feature/your-feature-name
```

8. Create Pull Request

· Go to GitHub and create a pull request
· Target the develop branch
· Fill out the PR template
· Link related issues
· Request reviewers

Pull Request Guidelines

PR Requirements

· Tests pass
· Code coverage maintained or improved
· Documentation updated
· No linting errors
· Conventional commit messages
· Branch up to date with develop

PR Description Template

```markdown
## Description
[Describe the changes]

## Related Issues
Fixes #123
Closes #456

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding documentation changes
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally
- [ ] Any dependent changes have been merged and published
```

Review Process

1. Automated checks: CI runs linting, tests, and build
2. Code review: At least one maintainer reviews
3. Feedback: Address review comments
4. Approval: PR approved by maintainer
5. Merge: Squash and merge to develop

Release Process

Versioning

We follow Semantic Versioning:

· MAJOR: Breaking changes
· MINOR: New features (backward compatible)
· PATCH: Bug fixes (backward compatible)

Release Steps

1. Create release branch: release/vX.Y.Z
2. Update version in pyproject.toml and package.json
3. Update CHANGELOG.md
4. Create release PR to main
5. Tag release: vX.Y.Z
6. GitHub Actions builds and publishes artifacts
7. Merge back to develop

Architecture Guidelines

Adding a New Agent

1. Create new agent class in src/agents/
2. Inherit from BaseAgent
3. Implement process() method
4. Add to agents dict in worker.py
5. Add configuration to agent-pool.yml
6. Add tests in tests/unit/
7. Update documentation

Example:

```python
from .base import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__("new-agent")
    
    async def process(self, data: Dict) -> Dict:
        # Implementation
        return {"content": "result"}
```

Adding a New Tool

1. Create new tool class in src/tools/
2. Implement execute() method
3. Register in src/tools/__init__.py
4. Add configuration to tool-registry.yml
5. Add tests in tests/unit/
6. Update documentation

Example:

```python
class Tool:
    def __init__(self):
        self.name = "new-tool"
        self.description = "Does something useful"
    
    async def execute(self, **kwargs) -> Dict:
        # Implementation
        return {"stdout": "result"}
```

Adding a New API Endpoint

1. Add route in src/orchestrator/routes/
2. Add Pydantic model in src/orchestrator/models/
3. Add service method in src/orchestrator/services/
4. Add authentication if needed
5. Add tests in tests/integration/
6. Update API documentation

Testing Guidelines

Unit Tests

· Test individual functions/classes in isolation
· Mock external dependencies
· Aim for >80% coverage

Integration Tests

· Test component interactions
· Use test containers for databases
· Verify message flows

Load Tests

· Use Locust for load testing
· Test under realistic load
· Measure p95/p99 latency

Chaos Tests

· Simulate failures
· Test circuit breakers
· Verify recovery mechanisms

Documentation Guidelines

Docstrings

Use Google style docstrings:

```python
def function(arg1: str, arg2: int = 0) -> bool:
    """Short description.
    
    Longer description with details.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2 (default: 0)
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something goes wrong
    """
```

README Updates

· Keep installation instructions current
· Update examples with real use cases
· Document configuration options
· Include troubleshooting tips

Security Guidelines

· No secrets in code
· Use environment variables for configuration
· Validate all inputs
· Escape all outputs
· Use parameterized queries
· Enable audit logging
· Follow least privilege principle

Performance Guidelines

· Use async/await for I/O operations
· Implement caching where appropriate
· Monitor queue depths
· Set timeouts on all external calls
· Use connection pooling
· Optimize database queries

Getting Help

· Discord: Join our server
· GitHub Issues: Report bugs
· Email: dev@agentic-shell.io

Recognition

Contributors will be:

· Listed in CONTRIBUTORS.md
· Mentioned in release notes
· Invited to maintainer team after significant contributions

Thank you for contributing! 🚀

