#!/usr/bin/env bash
# install.sh — install system-level dependencies and the project
set -euo pipefail

echo "==> Updating system packages..."
if command -v apt-get &>/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y python3 python3-pip curl git
elif command -v brew &>/dev/null; then
  brew install python git
fi

echo "==> Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

echo "==> Installing Python dependencies..."
poetry install --no-dev

echo "==> Install complete."
