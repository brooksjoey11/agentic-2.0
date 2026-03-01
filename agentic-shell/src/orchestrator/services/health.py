"""
Health Service
Service for checking health of all system components
"""

import asyncio
import psutil
from typing import Dict, Any, List
from datetime import datetime
import socket

from ..config import config
from ..db.database import get_db_pool
from ..cache.redis import get_redis_client
from ..messaging.rabbitmq import get_rabbitmq_connection
from ..registry.etcd import get_etcd_client
from ..discovery.consul import get_consul_client


class HealthService:
    """Service for health checks"""
    
    async def check_all(self) -> Dict[str, Any]:
        """Check health of all components"""
        results = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_rabbitmq(),
            self.check_etcd(),
            self.check_consul(),
            self.check_system_resources(),
            return_exceptions=True
        )
        
        components = {
            "database": results[0] if not isinstance(results[0], Exception) else {"status": "unhealthy", "error": str(results[0])},
            "redis": results[1] if not isinstance(results[1], Exception) else {"status": "unhealthy", "error": str(results[1])},
            "rabbitmq": results[2] if not isinstance(results[2], Exception) else {"status": "unhealthy", "error": str(results[2])},
            "etcd": results[3] if not isinstance(results[3], Exception) else {"status": "unhealthy", "error": str(results[3])},
            "consul": results[4] if not isinstance(results[4], Exception) else {"status": "unhealthy", "error": str(results[4])},
            "system": results[5] if not isinstance(results[5], Exception) else {"status": "unknown", "error": str(results[5])},
        }
        
        # Determine overall status
        overall_status = "healthy"
        degraded_components = []
        
        for name, result in components.items():
            if result.get("status") != "healthy":
                degraded_components.append(name)
                if result.get("status") == "unhealthy":
                    overall_status = "unhealthy"
                elif overall_status != "unhealthy":
                    overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "components": components,
            "degraded_components": degraded_components if degraded_components else None
        }
    
    async def check_essential(self) -> Dict[str, Any]:
        """Check only essential services"""
        results = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            return_exceptions=True
        )
        
        components = {
            "database": results[0] if not isinstance(results[0], Exception) else {"status": "unhealthy", "error": str(results[0])},
            "redis": results[1] if not isinstance(results[1], Exception) else {"status": "unhealthy", "error": str(results[1])},
        }
        
        all_healthy = all(comp.get("status") == "healthy" for comp in components.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "components": components
        }
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        start = datetime.now()
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    latency = (datetime.now() - start).total_seconds() * 1000
                    return {
                        "status": "healthy",
                        "latency_ms": latency
                    }
                return {
                    "status": "unhealthy",
                    "error": "Database query returned unexpected result"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        start = datetime.now()
        try:
            redis = await get_redis_client()
            result = await redis.ping()
            latency = (datetime.now() - start).total_seconds() * 1000
            if result:
                return {
                    "status": "healthy",
                    "latency_ms": latency
                }
            return {
                "status": "unhealthy",
                "error": "Redis ping failed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_rabbitmq(self) -> Dict[str, Any]:
        """Check RabbitMQ connectivity"""
        start = datetime.now()
        try:
            connection = await get_rabbitmq_connection()
            latency = (datetime.now() - start).total_seconds() * 1000
            if connection and not connection.is_closed:
                return {
                    "status": "healthy",
                    "latency_ms": latency
                }
            return {
                "status": "unhealthy",
                "error": "RabbitMQ connection closed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_etcd(self) -> Dict[str, Any]:
        """Check etcd connectivity"""
        start = datetime.now()
        try:
            client = get_etcd_client()
            status = client.client.status(client.client.endpoint)
            latency = (datetime.now() - start).total_seconds() * 1000
            if status:
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                }
            return {
                "status": "unhealthy",
                "error": "etcd status check failed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_consul(self) -> Dict[str, Any]:
        """Check Consul connectivity"""
        start = datetime.now()
        try:
            client = get_consul_client()
            status = client.client.agent.self()
            latency = (datetime.now() - start).total_seconds() * 1000
            if status:
                return {
                    "status": "healthy",
                    "latency_ms": latency
                }
            return {
                "status": "unhealthy",
                "error": "Consul status check failed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = "healthy"
            warnings = []
            
            if cpu_percent > 80:
                status = "degraded"
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 80:
                status = "degraded"
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 80:
                status = "degraded"
                warnings.append(f"High disk usage: {disk.percent}%")
            
            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free // (1024 * 1024 * 1024),
                "warnings": warnings if warnings else None
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e)
            }