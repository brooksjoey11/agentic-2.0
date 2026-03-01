"""
Consul Discovery Module
Service discovery and health checking
"""

import consul
from typing import Optional, Dict, List, Any
from functools import lru_cache
import socket

from ..config import config


class ConsulClient:
    """Consul client wrapper"""
    
    def __init__(self):
        self._client: Optional[consul.Consul] = None
    
    def initialize(self):
        """Initialize Consul connection"""
        self._client = consul.Consul(
            host=config.consul.host,
            port=config.consul.port
        )
    
    @property
    def client(self) -> consul.Consul:
        """Get client (initialized)"""
        if not self._client:
            self.initialize()
        return self._client
    
    def register_service(
        self,
        name: str,
        instance_id: str,
        address: Optional[str] = None,
        port: int = 0,
        tags: List[str] = None,
        meta: Dict[str, str] = None,
        check: Optional[Dict] = None
    ):
        """Register a service"""
        if not address:
            address = socket.gethostbyname(socket.gethostname())
        
        service_def = {
            "ID": instance_id,
            "Name": name,
            "Address": address,
            "Port": port,
            "Tags": tags or [],
            "Meta": meta or {},
        }
        
        if check:
            service_def["Check"] = check
        
        return self.client.agent.service.register(**service_def)
    
    def deregister_service(self, instance_id: str):
        """Deregister a service"""
        return self.client.agent.service.deregister(instance_id)
    
    def discover_service(self, name: str, passing_only: bool = True):
        """Discover service instances"""
        _, services = self.client.catalog.service(name)
        
        if passing_only:
            services = [s for s in services if self._is_service_healthy(s)]
        
        return [
            {
                "id": s["ServiceID"],
                "name": s["ServiceName"],
                "address": s["ServiceAddress"] or s["Address"],
                "port": s["ServicePort"],
                "tags": s["ServiceTags"],
                "meta": s["ServiceMeta"]
            }
            for s in services
        ]
    
    def _is_service_healthy(self, service: Dict) -> bool:
        """Check if service instance is healthy"""
        _, checks = self.client.health.checks(service["ServiceName"])
        for check in checks:
            if check["ServiceID"] == service["ServiceID"]:
                if check["Status"] != "passing":
                    return False
        return True
    
    def register_check(self, name: str, check_id: str, ttl: int = 30):
        """Register a TTL check"""
        return self.client.agent.check.register(
            name=name,
            check_id=check_id,
            ttl=ttl
        )
    
    def pass_check(self, check_id: str, notes: str = ""):
        """Mark check as passing"""
        return self.client.agent.check.ttl_pass(check_id, notes)
    
    def fail_check(self, check_id: str, notes: str = ""):
        """Mark check as failing"""
        return self.client.agent.check.ttl_fail(check_id, notes)
    
    def get_kv(self, key: str) -> Optional[str]:
        """Get value from KV store"""
        index, data = self.client.kv.get(key)
        if data and data["Value"]:
            return data["Value"].decode()
        return None
    
    def put_kv(self, key: str, value: str):
        """Put value in KV store"""
        return self.client.kv.put(key, value.encode())
    
    def delete_kv(self, key: str):
        """Delete key from KV store"""
        return self.client.kv.delete(key)
    
    def list_services(self):
        """List all registered services"""
        _, services = self.client.catalog.services()
        return services
    
    def get_service_health(self, name: str):
        """Get health status of all instances of a service"""
        _, checks = self.client.health.service(name)
        return checks


@lru_cache()
def get_consul_client() -> ConsulClient:
    """Get Consul client singleton"""
    return ConsulClient()