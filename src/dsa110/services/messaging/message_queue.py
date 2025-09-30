# core/messaging/message_queue.py
"""
Message queue system for DSA-110 pipeline.

This module provides message queue capabilities using Redis as the backend,
enabling asynchronous communication between pipeline services.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid

from ..utils.logging import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """Types of messages that can be sent."""
    PROCESSING_REQUEST = "processing_request"
    PROCESSING_RESULT = "processing_result"
    SERVICE_STATUS = "service_status"
    HEALTH_CHECK = "health_check"
    ERROR_NOTIFICATION = "error_notification"
    METRICS_UPDATE = "metrics_update"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Message:
    """A message with metadata."""
    id: str
    type: MessageType
    priority: MessagePriority
    payload: Dict[str, Any]
    sender: str
    recipient: Optional[str] = None
    created_at: datetime = None
    ttl: Optional[int] = None  # Time to live in seconds
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'payload': self.payload,
            'sender': self.sender,
            'recipient': self.recipient,
            'created_at': self.created_at.isoformat(),
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            type=MessageType(data['type']),
            priority=MessagePriority(data['priority']),
            payload=data['payload'],
            sender=data['sender'],
            recipient=data.get('recipient'),
            created_at=datetime.fromisoformat(data['created_at']),
            ttl=data.get('ttl')
        )


class MessageQueue:
    """
    Message queue implementation using Redis.
    
    Provides publish/subscribe and queue-based messaging capabilities
    for inter-service communication.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379",
                 namespace: str = "dsa110_pipeline"):
        """
        Initialize the message queue.
        
        Args:
            redis_url: Redis connection URL
            namespace: Namespace prefix for all keys
        """
        self.redis_url = redis_url
        self.namespace = namespace
        self.redis_client = None
        self.pubsub = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        
        logger.info(f"Message queue initialized with namespace '{namespace}'")
    
    async def connect(self):
        """Connect to Redis."""
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis for message queue")
            
        except ImportError:
            logger.error("Redis client not available. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Disconnected from Redis message queue")
    
    def _get_channel_name(self, channel: str) -> str:
        """Get namespaced channel name."""
        return f"{self.namespace}:channel:{channel}"
    
    def _get_queue_name(self, queue: str) -> str:
        """Get namespaced queue name."""
        return f"{self.namespace}:queue:{queue}"
    
    async def publish(self, channel: str, message: Message) -> bool:
        """
        Publish a message to a channel.
        
        Args:
            channel: Channel name
            message: Message to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            channel_name = self._get_channel_name(channel)
            message_data = json.dumps(message.to_dict())
            
            result = await self.redis_client.publish(channel_name, message_data)
            
            logger.debug(f"Published message {message.id} to channel {channel}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to publish message to channel {channel}: {e}")
            return False
    
    async def subscribe(self, channel: str, callback: Callable[[Message], None]):
        """
        Subscribe to a channel.
        
        Args:
            channel: Channel name
            callback: Callback function to handle messages
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            channel_name = self._get_channel_name(channel)
            
            # Add callback to subscribers
            if channel not in self.subscribers:
                self.subscribers[channel] = []
            self.subscribers[channel].append(callback)
            
            # Subscribe to channel
            await self.pubsub.subscribe(channel_name)
            
            logger.info(f"Subscribed to channel {channel}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            raise
    
    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None):
        """
        Unsubscribe from a channel.
        
        Args:
            channel: Channel name
            callback: Specific callback to remove (if None, removes all)
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            channel_name = self._get_channel_name(channel)
            
            if callback:
                if channel in self.subscribers and callback in self.subscribers[channel]:
                    self.subscribers[channel].remove(callback)
            else:
                self.subscribers[channel] = []
            
            # Unsubscribe from channel if no more callbacks
            if not self.subscribers.get(channel, []):
                await self.pubsub.unsubscribe(channel_name)
                logger.info(f"Unsubscribed from channel {channel}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")
    
    async def enqueue(self, queue: str, message: Message) -> bool:
        """
        Enqueue a message to a queue.
        
        Args:
            queue: Queue name
            message: Message to enqueue
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            queue_name = self._get_queue_name(queue)
            message_data = json.dumps(message.to_dict())
            
            # Use priority-based queuing
            priority_score = message.priority.value
            await self.redis_client.zadd(queue_name, {message_data: priority_score})
            
            logger.debug(f"Enqueued message {message.id} to queue {queue}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue message to queue {queue}: {e}")
            return False
    
    async def dequeue(self, queue: str, timeout: int = 0) -> Optional[Message]:
        """
        Dequeue a message from a queue.
        
        Args:
            queue: Queue name
            timeout: Timeout in seconds (0 for non-blocking)
            
        Returns:
            Message or None if no message available
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            queue_name = self._get_queue_name(queue)
            
            if timeout > 0:
                # Blocking pop with timeout
                result = await self.redis_client.bzpopmax(queue_name, timeout=timeout)
                if result:
                    _, message_data, _ = result
                else:
                    return None
            else:
                # Non-blocking pop
                result = await self.redis_client.zpopmax(queue_name)
                if result:
                    message_data, _ = result[0]
                else:
                    return None
            
            message_dict = json.loads(message_data)
            message = Message.from_dict(message_dict)
            
            logger.debug(f"Dequeued message {message.id} from queue {queue}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to dequeue message from queue {queue}: {e}")
            return None
    
    async def peek(self, queue: str) -> Optional[Message]:
        """
        Peek at the next message in a queue without removing it.
        
        Args:
            queue: Queue name
            
        Returns:
            Message or None if no message available
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            queue_name = self._get_queue_name(queue)
            
            # Get highest priority message without removing it
            result = await self.redis_client.zrevrange(queue_name, 0, 0, withscores=True)
            if result:
                message_data, _ = result[0]
                message_dict = json.loads(message_data)
                message = Message.from_dict(message_dict)
                return message
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to peek at queue {queue}: {e}")
            return None
    
    async def get_queue_length(self, queue: str) -> int:
        """
        Get the length of a queue.
        
        Args:
            queue: Queue name
            
        Returns:
            Number of messages in the queue
        """
        try:
            if not self.redis_client:
                await self.connect()
            
            queue_name = self._get_queue_name(queue)
            return await self.redis_client.zcard(queue_name)
            
        except Exception as e:
            logger.error(f"Failed to get queue length for {queue}: {e}")
            return 0
    
    async def start_message_loop(self):
        """Start the message processing loop."""
        if self.running:
            logger.warning("Message loop is already running")
            return
        
        self.running = True
        logger.info("Started message processing loop")
        
        try:
            while self.running:
                # Process pub/sub messages
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    await self._handle_pubsub_message(message)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in message processing loop: {e}")
        finally:
            self.running = False
            logger.info("Stopped message processing loop")
    
    async def stop_message_loop(self):
        """Stop the message processing loop."""
        self.running = False
        logger.info("Stopping message processing loop")
    
    async def _handle_pubsub_message(self, message):
        """Handle a pub/sub message."""
        try:
            if message['type'] == 'message':
                channel = message['channel']
                data = json.loads(message['data'])
                msg = Message.from_dict(data)
                
                # Find the channel name without namespace
                channel_name = channel.replace(f"{self.namespace}:channel:", "")
                
                # Call all subscribers for this channel
                if channel_name in self.subscribers:
                    for callback in self.subscribers[channel_name]:
                        try:
                            await callback(msg)
                        except Exception as e:
                            logger.error(f"Error in message callback: {e}")
                            
        except Exception as e:
            logger.error(f"Error handling pub/sub message: {e}")
    
    def create_message(self, message_type: MessageType, payload: Dict[str, Any],
                      sender: str, recipient: Optional[str] = None,
                      priority: MessagePriority = MessagePriority.NORMAL,
                      ttl: Optional[int] = None) -> Message:
        """
        Create a new message.
        
        Args:
            message_type: Type of message
            payload: Message payload
            sender: Sender identifier
            recipient: Recipient identifier (optional)
            priority: Message priority
            ttl: Time to live in seconds
            
        Returns:
            Message instance
        """
        return Message(
            id=str(uuid.uuid4()),
            type=message_type,
            priority=priority,
            payload=payload,
            sender=sender,
            recipient=recipient,
            ttl=ttl
        )


class MessageQueueManager:
    """
    Manager for multiple message queues.
    
    Provides a centralized interface for managing multiple message queues
    and routing messages between services.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379",
                 namespace: str = "dsa110_pipeline"):
        """
        Initialize the message queue manager.
        
        Args:
            redis_url: Redis connection URL
            namespace: Namespace prefix for all keys
        """
        self.redis_url = redis_url
        self.namespace = namespace
        self.queues: Dict[str, MessageQueue] = {}
        self.running = False
        
        logger.info(f"Message queue manager initialized with namespace '{namespace}'")
    
    async def get_queue(self, name: str) -> MessageQueue:
        """
        Get or create a message queue.
        
        Args:
            name: Queue name
            
        Returns:
            Message queue instance
        """
        if name not in self.queues:
            queue = MessageQueue(self.redis_url, f"{self.namespace}:{name}")
            await queue.connect()
            self.queues[name] = queue
            
            logger.info(f"Created message queue: {name}")
        
        return self.queues[name]
    
    async def start_all_queues(self):
        """Start all message queues."""
        if self.running:
            logger.warning("Message queues are already running")
            return
        
        self.running = True
        
        # Start message loops for all queues
        tasks = []
        for queue in self.queues.values():
            task = asyncio.create_task(queue.start_message_loop())
            tasks.append(task)
        
        logger.info(f"Started {len(tasks)} message queue loops")
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in message queue loops: {e}")
        finally:
            self.running = False
    
    async def stop_all_queues(self):
        """Stop all message queues."""
        self.running = False
        
        for queue in self.queues.values():
            await queue.stop_message_loop()
            await queue.disconnect()
        
        logger.info("Stopped all message queues")
    
    async def cleanup(self):
        """Clean up all queues."""
        await self.stop_all_queues()
        self.queues.clear()
        logger.info("Cleaned up message queue manager")


# Global message queue manager instance
_global_queue_manager = None


def get_message_queue_manager() -> MessageQueueManager:
    """Get the global message queue manager instance."""
    global _global_queue_manager
    if _global_queue_manager is None:
        _global_queue_manager = MessageQueueManager()
    return _global_queue_manager


async def initialize_message_queues(redis_url: str = "redis://localhost:6379",
                                  namespace: str = "dsa110_pipeline"):
    """
    Initialize the global message queue manager.
    
    Args:
        redis_url: Redis connection URL
        namespace: Namespace prefix for all keys
    """
    global _global_queue_manager
    _global_queue_manager = MessageQueueManager(redis_url, namespace)
    logger.info("Global message queue manager initialized")
