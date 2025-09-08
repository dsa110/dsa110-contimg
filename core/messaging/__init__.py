# core/messaging/__init__.py
"""
Message queue system for DSA-110 pipeline.

This package provides message queue capabilities for inter-service
communication using Redis as the backend.
"""

from .message_queue import (
    MessageQueue, MessageQueueManager, Message, MessageType, MessagePriority,
    get_message_queue_manager, initialize_message_queues
)

__all__ = [
    'MessageQueue', 'MessageQueueManager', 'Message', 'MessageType', 'MessagePriority',
    'get_message_queue_manager', 'initialize_message_queues'
]
