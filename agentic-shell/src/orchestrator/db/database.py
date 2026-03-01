"""
Database Module
PostgreSQL connection pool and query utilities
"""

import asyncpg
from typing import Optional
from functools import lru_cache

from ..config import config


class DatabasePool:
    """PostgreSQL connection pool wrapper"""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize connection pool"""
        self._pool = await asyncpg.create_pool(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password,
            min_size=config.database.min_size,
            max_size=config.database.max_size,
            command_timeout=60,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
    
    async def acquire(self) -> asyncpg.Connection:
        """Acquire connection from pool"""
        if not self._pool:
            await self.initialize()
        return await self._pool.acquire()
    
    async def release(self, conn: asyncpg.Connection):
        """Release connection back to pool"""
        if self._pool:
            await self._pool.release(conn)
    
    async def close(self):
        """Close all connections"""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def execute(self, query: str, *args):
        """Execute query and return result"""
        conn = await self.acquire()
        try:
            return await conn.execute(query, *args)
        finally:
            await self.release(conn)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        conn = await self.acquire()
        try:
            return await conn.fetch(query, *args)
        finally:
            await self.release(conn)
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row"""
        conn = await self.acquire()
        try:
            return await conn.fetchrow(query, *args)
        finally:
            await self.release(conn)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        conn = await self.acquire()
        try:
            return await conn.fetchval(query, *args)
        finally:
            await self.release(conn)
    
    async def transaction(self):
        """Start a transaction"""
        conn = await self.acquire()
        return conn.transaction()


@lru_cache()
def get_db_pool() -> DatabasePool:
    """Get database pool singleton"""
    return DatabasePool()