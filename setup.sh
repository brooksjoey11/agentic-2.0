#!/usr/bin/env bash
# setup.sh — bootstrap the agentic-shell development environment
set -euo pipefail

echo "==> Checking Python version..."
python3 --version

echo "==> Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -

echo "==> Installing project dependencies..."
poetry install

echo "==> Copying environment file..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created .env from .env.example — edit it before running the stack."
fi

echo "==> Setup complete. Run 'make dev' to start the development server."
