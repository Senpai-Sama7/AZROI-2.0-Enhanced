#!/usr/bin/env python3

import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
import hashlib

logger = logging.getLogger("ai-architect-backend.memory_manager")

class MemoryManager:
    """
    Memory Manager using Qdrant vector database for long-term storage
    and Redis for short-term caching of frequently accessed memories.
    
    This class provides unified memory management for all agents, including:
    - Long-term memory for project context and history
    - Working memory for current task execution
    - Caching for performance optimization
    """
    
    def __init__(self, 
               vector_storage=None,
               llm_router=None,
               redis_client=None,
               monitoring_system=None):
        """
        Initialize the memory manager.
        
        Args:
            vector_storage: Vector storage implementation (Qdrant)
            llm_router: LLM router for embeddings generation
            redis_client: Redis client for caching (can be None)
            monitoring_system: Monitoring system for metrics
        """
        self.vector_storage = vector_storage
        self.llm_router = llm_router
        self.redis_client = redis_client
        self.monitoring_system = monitoring_system
        self.initialized = False
        
        # Memory namespaces
        self.namespaces = {
            "project_context": "Project context and requirements",
            "execution_history": "History of executed tasks and their outcomes",
            "agent_interactions": "Records of interactions between agents",
            "code_snippets": "Useful code snippets for reference",
            "tool_usage": "Records of tool usage and outcomes",
            "user_preferences": "User preferences and feedback"
        }
        
        logger.info("Memory manager initialized")
    
    async def initialize(self):
        """
        Initialize the memory manager.
        """
        if self.initialized:
            return
        
        if not self.vector_storage:
            from .vector_storage import VectorStorage
            self.vector_storage = VectorStorage()
        
        # Initialize vector storage if not already initialized
        if not getattr(self.vector_storage, 'initialized', False):
            await self.vector_storage.initialize()
        
        # Set monitoring system for vector storage if available
        if self.monitoring_system and hasattr(self.vector_storage, 'set_monitoring_system'):
            self.vector_storage.set_monitoring_system(self.monitoring_system)
        
        # Create memory namespaces/collections
        for namespace in self.namespaces:
            # We're using the same collection with metadata filtering for namespaces
            # This is more efficient in Qdrant than creating multiple collections
            logger.info(f"Setting up memory namespace: {namespace}")
        
        self.initialized = True
        logger.info("Memory manager fully initialized")
    
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using LLM router.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not self.llm_router:
            raise ValueError("LLM router is required for embedding generation")
        
        embedding = await self.llm_router.get_embedding(text)
        return embedding
    
    def _generate_memory_id(self, content: str) -> str:
        """Generate a deterministic ID for a memory based on its content."""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def store_memory(self, 
                         content: str, 
                         namespace: str = "execution_history",
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a memory.
        
        Args:
            content: Memory content
            namespace: Memory namespace
            metadata: Additional metadata
            
        Returns:
            Memory ID
        """
        if not self.initialized:
            await self.initialize()
        
        if namespace not in self.namespaces:
            raise ValueError(f"Invalid namespace: {namespace}")
        
        try:
            # Generate memory ID
            memory_id = self._generate_memory_id(content)
            
            # Get embedding
            embedding = await self._get_embedding(content)
            
            # Prepare metadata
            meta = metadata or {}
            meta.update({
                "namespace": namespace,
                "timestamp": time.time(),
                "description": self.namespaces[namespace],
            })
            
            # Store in vector database
            await self.vector_storage.add_item(
                item_id=memory_id,
                vector=embedding,
                metadata=meta,
                content=content
            )
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="store", namespace=namespace).inc()
            
            logger.info(f"Stored memory {memory_id} in namespace {namespace}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="store", namespace=namespace).inc()
            raise
    
    async def retrieve_memory(self, 
                            query: str, 
                            namespace: Optional[str] = None,
                            limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve memories by semantic search.
        
        Args:
            query: Search query
            namespace: Optional namespace filter
            limit: Maximum number of results
            
        Returns:
            List of memory items with content and metadata
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Check cache first if Redis is available
            if self.redis_client and namespace:
                cache_key = f"memory:{namespace}:{hashlib.md5(query.encode()).hexdigest()}"
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.info(f"Memory cache hit for query in {namespace}")
                    if self.monitoring_system:
                        self.monitoring_system.memory_cache_counter.labels(
                            result="hit", namespace=namespace or "all").inc()
                    return json.loads(cached)
            
            # Get embedding
            embedding = await self._get_embedding(query)
            
            # Prepare filter
            filter_condition = None
            if namespace:
                filter_condition = {"namespace": namespace}
            
            # Search in vector database
            results = await self.vector_storage.search(
                query_vector=embedding,
                limit=limit,
                filter_condition=filter_condition
            )
            
            # Update cache if Redis is available
            if self.redis_client and namespace:
                await self.redis_client.set(
                    cache_key, 
                    json.dumps(results),
                    expire=300  # 5 minute cache expiry for search results
                )
                if self.monitoring_system:
                    self.monitoring_system.memory_cache_counter.labels(
                        result="miss", namespace=namespace or "all").inc()
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="retrieve", namespace=namespace or "all").inc()
                self.monitoring_system.memory_results_histogram.labels(
                    namespace=namespace or "all").observe(len(results))
            
            logger.info(f"Retrieved {len(results)} memories for query in namespace {namespace or 'all'}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="retrieve", namespace=namespace or "all").inc()
            return []
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory item or None if not found
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Check cache first if Redis is available
            if self.redis_client:
                cache_key = f"memory_id:{memory_id}"
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.info(f"Memory cache hit for ID {memory_id}")
                    if self.monitoring_system:
                        self.monitoring_system.memory_cache_counter.labels(
                            result="hit", namespace="id_lookup").inc()
                    return json.loads(cached)
            
            # Get from vector database
            memory = await self.vector_storage.get_by_id(memory_id)
            
            # Update cache if Redis is available and item found
            if self.redis_client and memory:
                await self.redis_client.set(
                    f"memory_id:{memory_id}", 
                    json.dumps(memory),
                    expire=3600  # 1 hour cache for specific items
                )
                if self.monitoring_system:
                    self.monitoring_system.memory_cache_counter.labels(
                        result="miss", namespace="id_lookup").inc()
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="get_by_id", namespace="id_lookup").inc()
            
            return memory
            
        except Exception as e:
            logger.error(f"Error getting memory by ID: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="get_by_id", namespace="id_lookup").inc()
            return None
    
    async def update_memory(self, 
                          memory_id: str, 
                          content: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update a memory.
        
        Args:
            memory_id: Memory ID
            content: New content (if None, only metadata is updated)
            metadata: New metadata (if None, only content is updated)
            
        Returns:
            Success flag
        """
        if not self.initialized:
            await self.initialize()
        
        if not content and not metadata:
            return False
            
        try:
            # Get current memory
            current = await self.get_memory_by_id(memory_id)
            if not current:
                logger.warning(f"Memory {memory_id} not found for update")
                return False
            
            # Prepare update
            update_data = {}
            
            if content:
                # Get new embedding
                embedding = await self._get_embedding(content)
                update_data["vector"] = embedding
                update_data["content"] = content
            
            if metadata:
                # Merge with existing metadata
                new_meta = current.get("metadata", {}).copy()
                new_meta.update(metadata)
                update_data["metadata"] = new_meta
            
            # Update vector database
            success = await self.vector_storage.update_item(
                item_id=memory_id,
                **update_data
            )
            
            # Invalidate cache if Redis is available
            if self.redis_client:
                await self.redis_client.delete(f"memory_id:{memory_id}")
                # Also invalidate any search caches that might contain this item
                # This is a simple approach - a more sophisticated one would track which
                # search results contain which memories
                namespace = current.get("metadata", {}).get("namespace", "")
                if namespace:
                    pattern = f"memory:{namespace}:*"
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="update", 
                    namespace=current.get("metadata", {}).get("namespace", "unknown")
                ).inc()
            
            logger.info(f"Updated memory {memory_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="update", namespace="unknown").inc()
            return False
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Success flag
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Get memory first (for namespace and cache invalidation)
            memory = await self.get_memory_by_id(memory_id)
            namespace = memory.get("metadata", {}).get("namespace", "") if memory else ""
            
            # Delete from vector database
            success = await self.vector_storage.delete_item(memory_id)
            
            # Invalidate cache if Redis is available
            if self.redis_client:
                await self.redis_client.delete(f"memory_id:{memory_id}")
                # Invalidate namespace searches
                if namespace:
                    pattern = f"memory:{namespace}:*"
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="delete", namespace=namespace or "unknown").inc()
            
            logger.info(f"Deleted memory {memory_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="delete", namespace="unknown").inc()
            return False
    
    async def clear_namespace(self, namespace: str) -> bool:
        """
        Clear all memories in a namespace.
        
        Args:
            namespace: Namespace to clear
            
        Returns:
            Success flag
        """
        if not self.initialized:
            await self.initialize()
        
        if namespace not in self.namespaces:
            raise ValueError(f"Invalid namespace: {namespace}")
            
        try:
            # Delete all items with namespace filter
            filter_condition = {"namespace": namespace}
            success = await self.vector_storage.delete_by_filter(filter_condition)
            
            # Invalidate cache if Redis is available
            if self.redis_client:
                pattern = f"memory:{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="clear_namespace", namespace=namespace).inc()
            
            logger.info(f"Cleared namespace {namespace}")
            return success
            
        except Exception as e:
            logger.error(f"Error clearing namespace: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="clear_namespace", namespace=namespace).inc()
            return False
    
    async def store_execution_history(self, 
                                    goal_id: str,
                                    agent_name: str,
                                    task_id: str,
                                    operation: str,
                                    content: str,
                                    status: str = "completed",
                                    artifacts: Optional[List[str]] = None) -> str:
        """
        Store execution history as a specialized memory function.
        
        Args:
            goal_id: ID of the goal
            agent_name: Name of the agent
            task_id: ID of the task
            operation: Operation performed
            content: Content/result of the operation
            status: Status (completed, failed, etc.)
            artifacts: List of artifact IDs or paths
            
        Returns:
            Memory ID
        """
        metadata = {
            "goal_id": goal_id,
            "agent_name": agent_name,
            "task_id": task_id,
            "operation": operation,
            "status": status,
            "artifacts": artifacts or []
        }
        
        return await self.store_memory(
            content=content,
            namespace="execution_history",
            metadata=metadata
        )
    
    async def get_execution_history(self, 
                                  goal_id: Optional[str] = None,
                                  agent_name: Optional[str] = None,
                                  task_id: Optional[str] = None,
                                  limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get execution history with optional filters.
        
        Args:
            goal_id: Optional goal ID filter
            agent_name: Optional agent name filter
            task_id: Optional task ID filter
            limit: Maximum number of results
            
        Returns:
            List of execution history items
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Prepare filter
            filter_condition = {"namespace": "execution_history"}
            
            if goal_id:
                filter_condition["goal_id"] = goal_id
            if agent_name:
                filter_condition["agent_name"] = agent_name
            if task_id:
                filter_condition["task_id"] = task_id
            
            # Get from vector database
            results = await self.vector_storage.get_by_filter(
                filter_condition=filter_condition,
                limit=limit,
                sort_by="timestamp",
                sort_direction="desc"
            )
            
            # Track metrics
            if self.monitoring_system:
                self.monitoring_system.memory_operation_counter.labels(
                    operation="get_execution_history", 
                    namespace="execution_history"
                ).inc()
            
            logger.info(f"Retrieved {len(results)} execution history items")
            return results
            
        except Exception as e:
            logger.error(f"Error getting execution history: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.memory_error_counter.labels(
                    operation="get_execution_history", 
                    namespace="execution_history"
                ).inc()
            return []