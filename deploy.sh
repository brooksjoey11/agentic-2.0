#!/bin/bash
set -euo pipefail

echo "🚀 Deploying Agentic 2.0 Production Stack"

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Create directories
mkdir -p {logs,certs,data,backups}

# Generate certs if missing
if [ ! -f certs/server.key ]; then
    echo "🔐 Generating certificates..."
    openssl req -x509 -newkey rsa:4096 \
        -keyout certs/server.key \
        -out certs/server.crt \
        -days 365 -nodes \
        -subj "/CN=agentic.local"
fi

# Pull latest images
echo "📦 Pulling images..."
docker-compose pull

# Build local images
echo "🏗️ Building services..."
docker-compose build --parallel

# Stop existing stack
echo "🛑 Stopping existing stack..."
docker-compose down --remove-orphans

# Start infrastructure
echo "▶️ Starting infrastructure..."
docker-compose up -d postgres redis rabbitmq etcd consul prometheus grafana

# Wait for dependencies
echo "⏳ Waiting for dependencies..."
sleep 10

# Initialize database
echo "🗄️ Initializing database..."
max_retries=30
counter=0
until docker-compose exec -T postgres pg_isready -U postgres; do
    if [ $counter -eq $max_retries ]; then
        echo "❌ Database failed to start"
        exit 1
    fi
    echo "Waiting for database... $counter/$max_retries"
    sleep 2
    counter=$((counter + 1))
done

# Run migrations
echo "🔄 Running migrations..."
docker-compose exec -T postgres psql -U postgres -d agentic -f /docker-entrypoint-initdb.d/init.sql

# Start application services
echo "🚀 Starting application services..."
docker-compose up -d orchestrator worker client

# Health check
echo "🏥 Running health checks..."
sleep 5
services=("orchestrator:8080/health" "worker:8081/health" "client:8082/health")
for service in "${services[@]}"; do
    if curl -sf "http://$service"; then
        echo "✅ $service healthy"
    else
        echo "⚠️ $service unhealthy"
    fi
done

echo "✅ Deployment complete"
echo "📊 Grafana: http://localhost:3000 (admin/admin)"
echo "📈 Prometheus: http://localhost:9090"
echo "🔧 Consul: http://localhost:8500"
echo "📨 RabbitMQ: http://localhost:15672 (rabbitmq/rabbitmq)"
