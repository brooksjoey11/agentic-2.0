"""
Production Database Connection Pool
Validates connections, handles reconnection, and provides metrics.
"""

import asyncio
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
from prometheus_client import Gauge, Counter

from ..config import config

logger = logging.getLogger(__name__)

# Metrics
DB_POOL_SIZE = Gauge('db_pool_size', 'Current database pool size')
DB_POOL_AVAILABLE = Gauge('db_pool_available', 'Available database connections')
DB_POOL_USED = Gauge('db_pool_used', 'Used database connections')
DB_QUERY_COUNT = Counter('db_queries_total', 'Total database queries', ['type'])
DB_QUERY_ERRORS = Counter('db_query_errors_total', 'Database query errors', ['type'])
DB_CONNECTION_ERRORS = Counter('db_connection_errors_total', 'Database connection errors')


@dataclass
class PoolConfig:
    """Connection pool configuration"""
    min_size: int = 5
    max_size: int = 20
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0
    command_timeout: int = 60
    connection_timeout: int = 10


class DatabasePool:
    """
    PostgreSQL connection pool with health checks and automatic reconnection.
    
    Single source of truth for database connections.
    All database access must go through this pool.
    """
    
    def __init__(self, config: PoolConfig = None):
        self.config = config or PoolConfig()
        self._pool = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize connection pool with validation."""
        if self._initialized:
            return
        
        import asyncpg
            
        try:
            self._pool = await asyncpg.create_pool(
                host=config.database.host,
                port=config.database.port,
                database=config.database.database,
                user=config.database.user,
                password=config.database.password,
                min_size=self.config.min_size,
                max_size=self.config.max_size,
                max_queries=self.config.max_queries,
                max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                command_timeout=self.config.command_timeout,
                timeout=self.config.connection_timeout,
                
                # Connection setup hook
                init=self._init_connection,
                
                # Connection validation
                setup=self._validate_connection,
            )
            
            # Verify we can actually query
            async with self.acquire() as conn:
                await conn.fetchval("SELECT 1")
                
            self._initialized = True
            logger.info("Database pool initialized successfully")
            
            # Start background health checker
            asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            DB_CONNECTION_ERRORS.inc()
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _init_connection(self, conn):
        """Initialize a new connection with required settings."""
        await conn.execute("SET TIME ZONE 'UTC'")
        await conn.execute("SET statement_timeout = '30s'")
    
    async def _validate_connection(self, conn):
        """Validate a connection before returning it to the pool."""
        try:
            await conn.execute("SELECT 1")
        except Exception:
            return False
        return True
    
    def _update_metrics(self):
        """Update Prometheus metrics for pool state."""
        if self._pool:
            DB_POOL_SIZE.set(self._pool.get_size())
            DB_POOL_AVAILABLE.set(self._pool.get_available())
            DB_POOL_USED.set(self._pool.get_size() - self._pool.get_available())
    
    async def _health_check_loop(self):
        """Periodically check pool health."""
        while True:
            await asyncio.sleep(30)
            try:
                async with self.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                self._update_metrics()
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                DB_CONNECTION_ERRORS.inc()
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool with automatic release."""
        if not self._pool or not self._initialized:
            await self.initialize()
            
        conn = await self._pool.acquire()
        try:
            yield conn
        finally:
            await self._pool.release(conn)
            self._update_metrics()
    
    async def execute(self, query: str, *args):
        """Execute a query and return result."""
        DB_QUERY_COUNT.labels(type='execute').inc()
        try:
            async with self.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            DB_QUERY_ERRORS.labels(type='execute').inc()
            logger.error(f"Query execution failed: {e}", exc_info=True)
            raise
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        DB_QUERY_COUNT.labels(type='fetch').inc()
        try:
            async with self.acquire() as conn:
                return await conn.fetch(query, *args)
        except Exception as e:
            DB_QUERY_ERRORS.labels(type='fetch').inc()
            logger.error(f"Query fetch failed: {e}", exc_info=True)
            raise
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row."""
        DB_QUERY_COUNT.labels(type='fetchrow').inc()
        try:
            async with self.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            DB_QUERY_ERRORS.labels(type='fetchrow').inc()
            logger.error(f"Query fetchrow failed: {e}", exc_info=True)
            raise
    
    async def fetchval(self, query: str, *args):
        """Fetch single value."""
        DB_QUERY_COUNT.labels(type='fetchval').inc()
        try:
            async with self.acquire() as conn:
                return await conn.fetchval(query, *args)
        except Exception as e:
            DB_QUERY_ERRORS.labels(type='fetchval').inc()
            logger.error(f"Query fetchval failed: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close all connections in the pool."""
        if self._pool:
            await self._pool.close()
            self._initialized = False
            logger.info("Database pool closed")


# Singleton instance
_db_pool: Optional[DatabasePool] = None


async def get_db_pool() -> DatabasePool:
    """Get or create database pool singleton."""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
        await _db_pool.initialize()
    return _db_pool
