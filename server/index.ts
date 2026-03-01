import express from 'express';
import { createServer } from 'http';
import { config } from './configService.js';
import { logger } from './logger.js';
import { metricsMiddleware } from './metrics.js';
import { setupTRPC } from './routers/index.js';
import { setupAuth } from './auth.js';
import { setupHealthChecks } from './health.js';
import { setupMiddleware } from './middleware.js';
import { setupWebSocket } from './websocket.js';
import { setupJobQueue } from './jobQueue.js';
import { setupRedis } from './redis.js';
import { setupDatabase } from './db.js';
import { setupAudit } from './audit.js';
import { setupTracing } from './tracing.js';
import { setupRateLimit } from './rateLimit.js';

async function bootstrap() {
  // Initialize tracing
  const tracer = setupTracing('ai-to-production');
  
  // Create Express app
  const app = express();
  const server = createServer(app);
  
  // Connect to services
  await setupDatabase();
  const redis = await setupRedis();
  const queue = setupJobQueue(redis);
  
  // Setup middleware
  setupMiddleware(app);
  app.use(metricsMiddleware);
  
  // Setup authentication
  const auth = setupAuth();
  
  // Setup rate limiting
  const rateLimiter = setupRateLimit(redis);
  app.use(rateLimiter);
  
  // Setup health checks
  setupHealthChecks(app, { redis, queue });
  
  // Setup tRPC
  const trpcRouter = setupTRPC({ auth, redis, queue, tracer });
  app.use('/trpc', trpcRouter);
  
  // Setup audit logging
  setupAudit(app);
  
  // Setup WebSocket
  setupWebSocket(server, { auth, queue });
  
  // Start server
  const port = config.PORT || 3000;
  server.listen(port, () => {
    logger.info(`🚀 Server running on http://localhost:${port}`);
    logger.info(`📊 Metrics available at http://localhost:${port}/metrics`);
    logger.info(`🔧 Health check at http://localhost:${port}/health`);
  });
  
  // Graceful shutdown
  const shutdown = async () => {
    logger.info('Shutting down gracefully...');
    await queue.close();
    await redis.quit();
    server.close(() => process.exit(0));
  };
  
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

bootstrap().catch((error) => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});