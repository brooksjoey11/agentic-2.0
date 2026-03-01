#!/bin/bash
# setup-dev.sh - Development environment setup

set -e

echo "🚀 AI to Production - Development Setup"
echo "========================================"

# Check prerequisites
echo "🔍 Checking prerequisites..."

command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed." >&2; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "❌ pnpm is required but not installed. Install with: npm install -g pnpm" >&2; exit 1; }
command -v mysql >/dev/null 2>&1 || echo "⚠️ MySQL client not found. Install if you need to manage the database locally."
command -v redis-cli >/dev/null 2>&1 || echo "⚠️ Redis client not found. Install if you need to manage Redis locally."

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo "❌ Node.js 20+ required (found $(node -v))"
    exit 1
fi

echo "✅ Prerequisites checked"

# Install dependencies
echo "📦 Installing dependencies..."
pnpm install

# Setup git hooks
echo "🔧 Setting up git hooks..."
pnpm prepare

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️ Please edit .env with your configuration"
else
    echo "✅ .env file already exists"
fi

# Setup database
echo "🗄️ Setting up database..."
if command -v mysql >/dev/null 2>&1; then
    read -p "Create database? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mysql -e "CREATE DATABASE IF NOT EXISTS ai2prod;" 2>/dev/null || echo "⚠️ Could not create database. Ensure MySQL is running."
    fi
fi

# Run migrations
echo "🔄 Running database migrations..."
pnpm db:migrate || echo "⚠️ Migrations failed. Ensure database is configured in .env"

# Seed database
echo "🌱 Seeding database..."
pnpm db:seed || echo "⚠️ Seeding failed"

# Create uploads directory
mkdir -p uploads
mkdir -p logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Start development server: make dev"
echo "  3. Open http://localhost:3000"
echo ""
echo "Happy coding! 🎉"