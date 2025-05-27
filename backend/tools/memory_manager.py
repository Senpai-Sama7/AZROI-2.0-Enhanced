#!/usr/bin/env python3
"""
Enhanced Memory Manager with optimized storage and retrieval
"""

import logging
import time
import json
import pickle
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict, OrderedDict
from pathlib import Path
import tempfile
import threading

logger = logging.getLogger(__name__)

class MemoryManager:
    """High-performance memory manager with caching and persistence"""
    
    def __init__(self, 
                 max_memory_mb: int = 256,
                 cache_dir: Optional[str] = None,
                 enable_persistence: bool = True):
        self.max_memory_mb = max_memory_mb
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "memory_manager"
        self.enable_persistence = enable_persistence
        
        # Thread-safe memory storage
        self._lock = threading.RLock()
        self._memory = OrderedDict()  # LRU cache
        self._metadata = {}
        self._current_size = 0
        
        # Performance tracking
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'stores': 0,
            'retrievals': 0
        }
        
        # Initialize cache directory
        if self.enable_persistence:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"MemoryManager initialized (max: {max_memory_mb}MB, persistence: {enable_persistence})")
    
    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None):
        """Store data in memory with optional persistence"""
        try:
            with self._lock:
                # Serialize value to calculate size
                serialized_value = self._serialize_value(value)
                value_size = len(serialized_value)
                
                # Check if we need to evict items
                await self._ensure_space(value_size)
                
                # Store in memory
                self._memory[key] = value
                self._metadata[key] = {
                    'size': value_size,
                    'timestamp': time.time(),
                    'access_count': 0,
                    'metadata': metadata or {}
                }
                self._current_size += value_size
                self._stats['stores'] += 1
                
                # Move to end (most recently used)
                self._memory.move_to_end(key)
                
                # Persist if enabled
                if self.enable_persistence:
                    await self._persist_to_disk(key, serialized_value)
                
                logger.debug(f"Stored key '{key}' ({value_size} bytes)")
                
        except Exception as e:
            logger.error(f"Failed to store key '{key}': {e}")
            raise
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from memory or disk"""
        try:
            with self._lock:
                # Check memory first
                if key in self._memory:
                    self._stats['hits'] += 1
                    self._metadata[key]['access_count'] += 1
                    self._metadata[key]['last_access'] = time.time()
                    
                    # Move to end (most recently used)
                    self._memory.move_to_end(key)
                    
                    self._stats['retrievals'] += 1
                    return self._memory[key]
                
                # Check disk if persistence enabled
                if self.enable_persistence:
                    disk_value = await self._retrieve_from_disk(key)
                    if disk_value is not None:
                        # Load back into memory
                        await self.store(key, disk_value)
                        self._stats['hits'] += 1
                        self._stats['retrievals'] += 1
                        return disk_value
                
                # Not found
                self._stats['misses'] += 1
                self._stats['retrievals'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve key '{key}': {e}")
            return None
    
    async def _ensure_space(self, needed_bytes: int):
        """Ensure enough space is available, evicting if necessary"""
        while (self._current_size + needed_bytes) > self.max_memory_bytes and self._memory:
            # Evict least recently used item
            oldest_key, oldest_value = self._memory.popitem(last=False)
            
            if oldest_key in self._metadata:
                self._current_size -= self._metadata[oldest_key]['size']
                del self._metadata[oldest_key]
            
            self._stats['evictions'] += 1
            logger.debug(f"Evicted key '{oldest_key}' to free space")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first for simple types
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                return json.dumps(value).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(value)
        except Exception:
            # Fallback to string representation
            return str(value).encode('utf-8')
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                # Try pickle
                return pickle.loads(data)
            except Exception:
                # Fallback to string
                return data.decode('utf-8', errors='ignore')
    
    async def _persist_to_disk(self, key: str, data: bytes):
        """Persist data to disk"""
        try:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            file_path = self.cache_dir / f"{key_hash}.cache"
            
            # Write to temporary file first, then move
            temp_path = file_path.with_suffix('.tmp')
            temp_path.write_bytes(data)
            temp_path.replace(file_path)
            
        except Exception as e:
            logger.debug(f"Failed to persist key '{key}': {e}")
    
    async def _retrieve_from_disk(self, key: str) -> Optional[Any]:
        """Retrieve data from disk"""
        try:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            file_path = self.cache_dir / f"{key_hash}.cache"
            
            if file_path.exists():
                data = file_path.read_bytes()
                return self._deserialize_value(data)
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to retrieve key '{key}' from disk: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics"""
        with self._lock:
            hit_rate = self._stats['hits'] / max(self._stats['retrievals'], 1)
            
            return {
                'memory_usage_bytes': self._current_size,
                'memory_usage_mb': self._current_size / (1024 * 1024),
                'memory_usage_percent': (self._current_size / self.max_memory_bytes) * 100,
                'items_in_memory': len(self._memory),
                'hit_rate': hit_rate,
                'stats': self._stats.copy(),
                'cache_dir': str(self.cache_dir) if self.enable_persistence else None
            }
    
    def clear(self):
        """Clear all memory"""
        with self._lock:
            self._memory.clear()
            self._metadata.clear()
            self._current_size = 0
            logger.info("Memory cleared")
    
    def cleanup_disk_cache(self):
        """Clean up disk cache"""
        if not self.enable_persistence:
            return
        
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Disk cache cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup disk cache: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup()
        except:
            pass

    def cleanup(self):
        """Enhanced cleanup for memory leak prevention (Feature-BE-11)"""
        try:
            with self._lock:
                # Clear all memory structures
                self._memory.clear()
                self._metadata.clear()
                self._current_size = 0
                
                # Reset stats
                self._stats = {
                    'hits': 0,
                    'misses': 0,
                    'evictions': 0,
                    'stores': 0,
                    'retrievals': 0
                }
                
                logger.debug("MemoryManager cleanup completed")
                
        except Exception as e:
            logger.error(f"Error during MemoryManager cleanup: {e}")

    def force_garbage_collection(self):
        """Force garbage collection to free up memory (Feature-BE-11)"""
        import gc
        try:
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            return collected
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
            return 0

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information (Feature-BE-11)"""
        import psutil
        import os
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "cache_memory_bytes": self._current_size,
                "cache_memory_mb": self._current_size / (1024 * 1024),
                "process_memory_rss_mb": memory_info.rss / (1024 * 1024),
                "process_memory_vms_mb": memory_info.vms / (1024 * 1024),
                "cache_items": len(self._memory),
                "metadata_items": len(self._metadata),
                "cache_utilization_percent": (self._current_size / self.max_memory_bytes) * 100
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {"error": str(e)}

    async def periodic_cleanup(self, cleanup_interval: int = 300):
        """Periodic cleanup to prevent memory accumulation (Feature-BE-11)"""
        while True:
            try:
                await asyncio.sleep(cleanup_interval)
                
                # Clean up old entries based on access time
                current_time = time.time()
                old_threshold = current_time - (cleanup_interval * 2)  # Items older than 2 cleanup cycles
                
                with self._lock:
                    keys_to_remove = []
                    for key, metadata in self._metadata.items():
                        last_access = metadata.get('last_access', metadata.get('timestamp', 0))
                        if last_access < old_threshold:
                            keys_to_remove.append(key)
                    
                    # Remove old entries
                    for key in keys_to_remove:
                        if key in self._memory:
                            self._current_size -= self._metadata[key]['size']
                            del self._memory[key]
                            del self._metadata[key]
                    
                    if keys_to_remove:
                        logger.debug(f"Periodic cleanup removed {len(keys_to_remove)} old cache entries")
                
                # Force garbage collection periodically
                self.force_garbage_collection()
                
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
