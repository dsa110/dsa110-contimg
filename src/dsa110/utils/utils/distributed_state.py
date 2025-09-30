# core/utils/distributed_state.py
"""
Distributed state management for DSA-110 pipeline.

This module provides distributed state management capabilities using Redis
as the backend, allowing multiple pipeline instances to share state and
coordinate operations.
"""

import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .logging import get_logger

logger = get_logger(__name__)


class StateType(Enum):
    """Types of state that can be stored."""
    PROCESSING_BLOCK = "processing_block"
    SERVICE_STATUS = "service_status"
    LOCK = "lock"
    METADATA = "metadata"
    QUEUE = "queue"


@dataclass
class StateEntry:
    """A state entry with metadata."""
    key: str
    value: Any
    state_type: StateType
    created_at: datetime
    updated_at: datetime
    ttl: Optional[int] = None  # Time to live in seconds
    owner: Optional[str] = None  # Owner of the state entry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'key': self.key,
            'value': self.value,
            'state_type': self.state_type.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'ttl': self.ttl,
            'owner': self.owner
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateEntry':
        """Create from dictionary."""
        return cls(
            key=data['key'],
            value=data['value'],
            state_type=StateType(data['state_type']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            ttl=data.get('ttl'),
            owner=data.get('owner')
        )


class DistributedStateManager:
    """
    Distributed state manager using Redis as backend.
    
    Provides distributed state management with support for:
    - Key-value storage with TTL
    - Distributed locks
    - Service status tracking
    - Processing block state management
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 namespace: str = "dsa110_pipeline"):
        """
        Initialize the distributed state manager.
        
        Args:
            redis_url: Redis connection URL
            namespace: Namespace prefix for all keys
        """
        self.redis_url = redis_url
        self.namespace = namespace
        self.redis_client = None
        self.instance_id = str(uuid.uuid4())
        
        logger.info(f"Distributed state manager initialized with namespace '{namespace}'")
    
    async def connect(self):
        """Connect to Redis."""
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            
        except ImportError:
            logger.error("Redis client not available. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    def _get_key(self, key: str) -> str:
        """Get namespaced key."""
        return f"{self.namespace}:{key}"
    
    async def set_state(self, key: str, value: Any, state_type: StateType,
                       ttl: Optional[int] = None, owner: Optional[str] = None) -> bool:
        """
        Set a state entry.
        
        Args:
            key: State key
            value: State value
            state_type: Type of state
            ttl: Time to live in seconds
            owner: Owner of the state entry
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            now = datetime.now()
            entry = StateEntry(
                key=key,
                value=value,
                state_type=state_type,
                created_at=now,
                updated_at=now,
                ttl=ttl,
                owner=owner or self.instance_id
            )
            
            redis_key = self._get_key(key)
            serialized_value = json.dumps(entry.to_dict())
            
            if ttl:
                await self.redis_client.setex(redis_key, ttl, serialized_value)
            else:
                await self.redis_client.set(redis_key, serialized_value)
            
            logger.debug(f"Set state: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set state {key}: {e}")
            return False
    
    async def get_state(self, key: str) -> Optional[StateEntry]:
        """
        Get a state entry.
        
        Args:
            key: State key
            
        Returns:
            State entry or None if not found
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            redis_key = self._get_key(key)
            serialized_value = await self.redis_client.get(redis_key)
            
            if serialized_value is None:
                return None
            
            data = json.loads(serialized_value)
            entry = StateEntry.from_dict(data)
            
            logger.debug(f"Retrieved state: {key}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to get state {key}: {e}")
            return None
    
    async def delete_state(self, key: str) -> bool:
        """
        Delete a state entry.
        
        Args:
            key: State key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            redis_key = self._get_key(key)
            result = await self.redis_client.delete(redis_key)
            
            logger.debug(f"Deleted state: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete state {key}: {e}")
            return False
    
    async def list_states(self, state_type: Optional[StateType] = None,
                         pattern: str = "*") -> List[StateEntry]:
        """
        List state entries.
        
        Args:
            state_type: Filter by state type
            pattern: Key pattern to match
            
        Returns:
            List of state entries
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            redis_pattern = self._get_key(pattern)
            keys = await self.redis_client.keys(redis_pattern)
            
            entries = []
            for key in keys:
                # Remove namespace prefix
                state_key = key[len(self.namespace) + 1:]
                entry = await self.get_state(state_key)
                
                if entry and (state_type is None or entry.state_type == state_type):
                    entries.append(entry)
            
            logger.debug(f"Listed {len(entries)} state entries")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to list states: {e}")
            return []
    
    async def acquire_lock(self, lock_key: str, timeout: int = 30,
                          owner: Optional[str] = None) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_key: Lock key
            timeout: Lock timeout in seconds
            owner: Lock owner
            
        Returns:
            True if lock acquired, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            owner = owner or self.instance_id
            redis_key = self._get_key(f"lock:{lock_key}")
            
            # Try to acquire lock with SET NX EX
            result = await self.redis_client.set(redis_key, owner, nx=True, ex=timeout)
            
            if result:
                logger.info(f"Acquired lock: {lock_key}")
                return True
            else:
                logger.debug(f"Failed to acquire lock: {lock_key}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to acquire lock {lock_key}: {e}")
            return False
    
    async def release_lock(self, lock_key: str, owner: Optional[str] = None) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_key: Lock key
            owner: Lock owner
            
        Returns:
            True if lock released, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            owner = owner or self.instance_id
            redis_key = self._get_key(f"lock:{lock_key}")
            
            # Use Lua script to ensure atomic release
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis_client.eval(lua_script, 1, redis_key, owner)
            
            if result:
                logger.info(f"Released lock: {lock_key}")
                return True
            else:
                logger.warning(f"Failed to release lock: {lock_key} (not owner)")
                return False
                
        except Exception as e:
            logger.error(f"Failed to release lock {lock_key}: {e}")
            return False
    
    async def extend_lock(self, lock_key: str, timeout: int,
                         owner: Optional[str] = None) -> bool:
        """
        Extend a distributed lock.
        
        Args:
            lock_key: Lock key
            timeout: New timeout in seconds
            owner: Lock owner
            
        Returns:
            True if lock extended, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            owner = owner or self.instance_id
            redis_key = self._get_key(f"lock:{lock_key}")
            
            # Use Lua script to ensure atomic extension
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            
            result = await self.redis_client.eval(lua_script, 1, redis_key, owner, timeout)
            
            if result:
                logger.debug(f"Extended lock: {lock_key}")
                return True
            else:
                logger.warning(f"Failed to extend lock: {lock_key} (not owner)")
                return False
                
        except Exception as e:
            logger.error(f"Failed to extend lock {lock_key}: {e}")
            return False
    
    async def set_processing_block_state(self, block_id: str, state: str,
                                       metadata: Dict[str, Any] = None) -> bool:
        """
        Set processing block state.
        
        Args:
            block_id: Processing block ID
            state: Block state (pending, processing, completed, failed)
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        state_data = {
            'block_id': block_id,
            'state': state,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        return await self.set_state(
            f"block:{block_id}",
            state_data,
            StateType.PROCESSING_BLOCK,
            ttl=86400,  # 24 hours
            owner=self.instance_id
        )
    
    async def get_processing_block_state(self, block_id: str) -> Optional[Dict[str, Any]]:
        """
        Get processing block state.
        
        Args:
            block_id: Processing block ID
            
        Returns:
            Block state data or None if not found
        """
        entry = await self.get_state(f"block:{block_id}")
        return entry.value if entry else None
    
    async def set_service_status(self, service_name: str, status: str,
                               metadata: Dict[str, Any] = None) -> bool:
        """
        Set service status.
        
        Args:
            service_name: Service name
            status: Service status (healthy, degraded, unhealthy)
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        status_data = {
            'service_name': service_name,
            'status': status,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        return await self.set_state(
            f"service:{service_name}",
            status_data,
            StateType.SERVICE_STATUS,
            ttl=300,  # 5 minutes
            owner=self.instance_id
        )
    
    async def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get service status.
        
        Args:
            service_name: Service name
            
        Returns:
            Service status data or None if not found
        """
        entry = await self.get_state(f"service:{service_name}")
        return entry.value if entry else None
    
    async def get_all_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all service statuses.
        
        Returns:
            Dictionary of service statuses
        """
        entries = await self.list_states(StateType.SERVICE_STATUS)
        return {entry.value['service_name']: entry.value for entry in entries}
    
    async def cleanup_expired_states(self) -> int:
        """
        Clean up expired states.
        
        Returns:
            Number of states cleaned up
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            # Redis automatically handles TTL expiration, but we can clean up
            # any states that might be stale
            all_entries = await self.list_states()
            cleaned_count = 0
            
            for entry in all_entries:
                if entry.ttl and entry.updated_at:
                    age = (datetime.now() - entry.updated_at).total_seconds()
                    if age > entry.ttl:
                        await self.delete_state(entry.key)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired states")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0


# Global distributed state manager instance
_global_state_manager = None


def get_distributed_state_manager() -> DistributedStateManager:
    """Get the global distributed state manager instance."""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = DistributedStateManager()
    return _global_state_manager


async def initialize_distributed_state(redis_url: str = "redis://localhost:6379",
                                     namespace: str = "dsa110_pipeline"):
    """
    Initialize the global distributed state manager.
    
    Args:
        redis_url: Redis connection URL
        namespace: Namespace prefix for all keys
    """
    global _global_state_manager
    _global_state_manager = DistributedStateManager(redis_url, namespace)
    await _global_state_manager.connect()
    logger.info("Global distributed state manager initialized")
