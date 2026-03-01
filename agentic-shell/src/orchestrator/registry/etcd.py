"""
etcd Registry Module
Service discovery and configuration storage
"""

import etcd3
from typing import Optional, Dict, Any
from functools import lru_cache
import json

from ..config import config


class EtcdClient:
    """etcd client wrapper"""
    
    def __init__(self):
        self._client: Optional[etcd3.Client] = None
    
    def initialize(self):
        """Initialize etcd connection"""
        self._client = etcd3.client(
            host=config.etcd.host,
            port=config.etcd.port
        )
    
    @property
    def client(self) -> etcd3.Client:
        """Get client (initialized)"""
        if not self._client:
            self.initialize()
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        result = self.client.get(key)
        if result and result[0]:
            return json.loads(result[0].decode())
        return None
    
    def put(self, key: str, value: Any, lease=None):
        """Put key-value pair"""
        self.client.put(key, json.dumps(value), lease)
    
    def delete(self, key: str):
        """Delete key"""
        self.client.delete(key)
    
    def get_prefix(self, prefix: str):
        """Get all keys with prefix"""
        return self.client.get_prefix(prefix)
    
    def watch(self, key: str, callback):
        """Watch key for changes"""
        events_iterator, cancel = self.client.watch(key)
        for event in events_iterator:
            callback(event)
        return cancel
    
    def lease(self, ttl: int):
        """Create a new lease"""
        return self.client.lease(ttl)
    
    def register_service(self, service_name: str, instance_id: str, metadata: Dict[str, Any], ttl: int = 30):
        """Register a service with lease"""
        lease = self.lease(ttl)
        key = f"/services/{service_name}/{instance_id}"
        self.put(key, metadata, lease)
        return lease
    
    def discover_service(self, service_name: str):
        """Discover service instances"""
        instances = []
        for value, metadata in self.get_prefix(f"/services/{service_name}/"):
            instances.append({
                "id": metadata.key.decode().split('/')[-1],
                "metadata": json.loads(value.decode())
            })
        return instances
    
    def get_config(self, key: str):
        """Get configuration value"""
        return self.get(f"/config/{key}")
    
    def set_config(self, key: str, value: Any):
        """Set configuration value"""
        self.put(f"/config/{key}", value)


@lru_cache()
def get_etcd_client() -> EtcdClient:
    """Get etcd client singleton"""
    return EtcdClient()