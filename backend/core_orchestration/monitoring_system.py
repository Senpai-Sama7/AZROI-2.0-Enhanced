#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/core_orchestration/monitoring_system.py

import time
import logging
import threading
from typing import Dict, Any, List, Optional
from prometheus_client import Counter, Gauge, Histogram, REGISTRY, CollectorRegistry

logger = logging.getLogger("ai-architect-backend.monitoring")

# Global Prometheus metrics
PROM_METRICS = {}

def register_monitoring_metrics():
    """
    Register all Prometheus metrics for the application.
    This function should be called once at application startup.
    """
    global PROM_METRICS
    
    # Task metrics
    PROM_METRICS["task_counter"] = Counter(
        "ai_architect_tasks_total", 
        "Total number of AI architect tasks submitted"
    )
    
    PROM_METRICS["tasks_completed"] = Counter(
        "ai_architect_tasks_completed_total", 
        "Total number of AI architect tasks completed"
    )
    
    PROM_METRICS["tasks_failed"] = Counter(
        "ai_architect_tasks_failed_total", 
        "Total number of AI architect tasks that failed"
    )
    
    PROM_METRICS["active_tasks"] = Gauge(
        "ai_architect_active_tasks", 
        "Currently active AI architect tasks"
    )
    
    # Agent metrics
    PROM_METRICS["agent_calls"] = Counter(
        "ai_architect_agent_calls_total", 
        "Total number of agent calls", 
        ["agent_type"]
    )
    
    PROM_METRICS["agent_errors"] = Counter(
        "ai_architect_agent_errors_total", 
        "Total number of agent errors", 
        ["agent_type"]
    )
    
    PROM_METRICS["agent_duration"] = Histogram(
        "ai_architect_agent_duration_seconds", 
        "Duration of agent operations in seconds", 
        ["agent_type"],
        buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
    )
    
    # LLM metrics
    PROM_METRICS["llm_requests"] = Counter(
        "ai_architect_llm_requests_total", 
        "Total number of LLM API requests", 
        ["model"]
    )
    
    PROM_METRICS["llm_tokens"] = Counter(
        "ai_architect_llm_tokens_total", 
        "Total number of tokens consumed by LLM", 
        ["model", "type"]  # type = prompt, completion
    )
    
    PROM_METRICS["llm_cache_hits"] = Counter(
        "ai_architect_llm_cache_hits_total", 
        "Total number of LLM cache hits"
    )
    
    PROM_METRICS["llm_cache_misses"] = Counter(
        "ai_architect_llm_cache_misses_total", 
        "Total number of LLM cache misses"
    )
    
    PROM_METRICS["llm_errors"] = Counter(
        "ai_architect_llm_errors_total", 
        "Total number of LLM API errors", 
        ["model", "error_type"]
    )
    
    # System metrics
    PROM_METRICS["system_memory_usage"] = Gauge(
        "ai_architect_system_memory_usage_bytes", 
        "System memory usage in bytes"
    )
    
    PROM_METRICS["system_cpu_usage"] = Gauge(
        "ai_architect_system_cpu_usage_percent", 
        "System CPU usage percentage",
        ["cpu"]  # "total" or "cpu0", "cpu1", etc.
    )
    
    PROM_METRICS["system_disk_usage"] = Gauge(
        "ai_architect_system_disk_usage_bytes", 
        "System disk usage in bytes", 
        ["mountpoint", "type"]  # "type" is "used", "free", or "total"
    )
    
    # Container metrics
    PROM_METRICS["containers_running"] = Gauge(
        "ai_architect_containers_running", 
        "Number of containers running"
    )
    
    # Sandbox metrics
    PROM_METRICS["sandbox_operations"] = Counter(
        "ai_architect_sandbox_operations_total", 
        "Total number of sandbox operations", 
        ["operation_type"]
    )
    
    PROM_METRICS["sandbox_errors"] = Counter(
        "ai_architect_sandbox_errors_total", 
        "Total number of sandbox errors", 
        ["error_type"]
    )
    
    # Vector store metrics
    PROM_METRICS["vector_store_operations"] = Counter(
        "ai_architect_vector_store_operations_total", 
        "Total number of vector store operations", 
        ["operation_type"]
    )
    
    PROM_METRICS["vector_store_items"] = Gauge(
        "ai_architect_vector_store_items", 
        "Number of items in vector store", 
        ["collection"]
    )
    
    logger.info("Prometheus metrics registered")

class MonitoringSystem:
    """
    Monitoring system for tracking application metrics and performance.
    Integrates with Prometheus for metrics collection and visualization.
    """
    
    def __init__(self, metrics_interval: int = 15):
        """
        Initialize the monitoring system.
        
        Args:
            metrics_interval: Interval in seconds for collecting system metrics.
        """
        self.metrics_interval = metrics_interval
        self.running = False
        self.metrics_thread = None
        
        # Ensure metrics are registered
        global PROM_METRICS
        if not PROM_METRICS:
            register_monitoring_metrics()
    
    def start(self):
        """
        Start the monitoring system and background metrics collection.
        """
        if self.running:
            return
        
        self.running = True
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        self.metrics_thread.start()
        logger.info(f"Started monitoring system metrics collection (interval: {self.metrics_interval}s)")
    
    def stop(self):
        """
        Stop the monitoring system.
        """
        self.running = False
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=5)
        logger.info("Stopped monitoring system")
    
    def _metrics_collection_loop(self):
        """
        Background thread function for collecting system metrics.
        """
        try:
            import psutil
        except ImportError:
            logger.error("psutil not installed - system metrics collection disabled")
            return
        
        while self.running:
            try:
                # Sleep for the metrics interval
                time.sleep(self.metrics_interval)
                
                # Collect and update system metrics
                self._update_system_metrics()
                
                # Update container metrics
                self._update_container_metrics()
                
                # Update vector store metrics
                self._update_vector_store_metrics()
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {str(e)}")
    
    def _update_system_metrics(self):
        """
        Update Prometheus metrics for system resources.
        """
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            PROM_METRICS["system_cpu_usage"].labels(cpu="total").set(cpu_percent)
            
            per_cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
            for i, percent in enumerate(per_cpu_percent):
                PROM_METRICS["system_cpu_usage"].labels(cpu=f"cpu{i}").set(percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            PROM_METRICS["system_memory_usage"].set(memory.used)
            
            # Disk metrics
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    PROM_METRICS["system_disk_usage"].labels(
                        mountpoint=partition.mountpoint, 
                        type="used"
                    ).set(usage.used)
                    PROM_METRICS["system_disk_usage"].labels(
                        mountpoint=partition.mountpoint, 
                        type="free"
                    ).set(usage.free)
                    PROM_METRICS["system_disk_usage"].labels(
                        mountpoint=partition.mountpoint, 
                        type="total"
                    ).set(usage.total)
                except PermissionError:
                    # Some mountpoints may not be accessible
                    pass
        except Exception as e:
            logger.error(f"Error updating system metrics: {str(e)}")
    
    def _update_container_metrics(self):
        """
        Update container-related metrics.
        """
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list()
            PROM_METRICS["containers_running"].set(len(containers))
        except Exception as e:
            # Docker might not be available or accessible
            pass
    
    def _update_vector_store_metrics(self):
        """
        Update vector store metrics.
        """
        # This would be implemented when the vector store is in place
        pass
    
    def record_task_submitted(self, goal_id: str):
        """
        Record a new task submission.
        
        Args:
            goal_id: ID of the submitted goal/task.
        """
        PROM_METRICS["task_counter"].inc()
        PROM_METRICS["active_tasks"].inc()
        logger.info(f"Recorded new task submission: {goal_id}")
    
    def record_task_completed(self, goal_id: str):
        """
        Record a task completion.
        
        Args:
            goal_id: ID of the completed goal/task.
        """
        PROM_METRICS["tasks_completed"].inc()
        PROM_METRICS["active_tasks"].dec()
        logger.info(f"Recorded task completion: {goal_id}")
    
    def record_task_failed(self, goal_id: str):
        """
        Record a task failure.
        
        Args:
            goal_id: ID of the failed goal/task.
        """
        PROM_METRICS["tasks_failed"].inc()
        PROM_METRICS["active_tasks"].dec()
        logger.info(f"Recorded task failure: {goal_id}")
    
    def record_agent_call(self, agent_type: str):
        """
        Record an agent call.
        
        Args:
            agent_type: Type of agent being called.
        """
        PROM_METRICS["agent_calls"].labels(agent_type=agent_type).inc()
    
    def record_agent_error(self, agent_type: str):
        """
        Record an agent error.
        
        Args:
            agent_type: Type of agent that encountered an error.
        """
        PROM_METRICS["agent_errors"].labels(agent_type=agent_type).inc()
    
    def start_agent_timer(self, agent_type: str):
        """
        Start a timer for an agent operation.
        
        Args:
            agent_type: Type of agent being timed.
            
        Returns:
            Start time for the operation.
        """
        return time.time()
    
    def stop_agent_timer(self, agent_type: str, start_time: float):
        """
        Stop a timer for an agent operation and record the duration.
        
        Args:
            agent_type: Type of agent being timed.
            start_time: Start time from start_agent_timer.
        """
        duration = time.time() - start_time
        PROM_METRICS["agent_duration"].labels(agent_type=agent_type).observe(duration)
    
    def record_llm_request(self, model: str):
        """
        Record an LLM API request.
        
        Args:
            model: LLM model being used.
        """
        PROM_METRICS["llm_requests"].labels(model=model).inc()
    
    def record_llm_tokens(self, model: str, token_type: str, count: int):
        """
        Record tokens used by an LLM request.
        
        Args:
            model: LLM model being used.
            token_type: Type of tokens (prompt or completion).
            count: Number of tokens.
        """
        PROM_METRICS["llm_tokens"].labels(model=model, type=token_type).inc(count)
    
    def record_llm_error(self, model: str, error_type: str):
        """
        Record an LLM API error.
        
        Args:
            model: LLM model being used.
            error_type: Type of error encountered.
        """
        PROM_METRICS["llm_errors"].labels(model=model, error_type=error_type).inc()
    
    def record_cache_hit(self):
        """Record an LLM cache hit."""
        PROM_METRICS["llm_cache_hits"].inc()
    
    def record_cache_miss(self):
        """Record an LLM cache miss."""
        PROM_METRICS["llm_cache_misses"].inc()
    
    def record_sandbox_operation(self, operation_type: str):
        """
        Record a sandbox operation.
        
        Args:
            operation_type: Type of sandbox operation.
        """
        PROM_METRICS["sandbox_operations"].labels(operation_type=operation_type).inc()
    
    def record_sandbox_error(self, error_type: str):
        """
        Record a sandbox error.
        
        Args:
            error_type: Type of sandbox error.
        """
        PROM_METRICS["sandbox_errors"].labels(error_type=error_type).inc()
    
    def record_vector_store_operation(self, operation_type: str):
        """
        Record a vector store operation.
        
        Args:
            operation_type: Type of vector store operation.
        """
        PROM_METRICS["vector_store_operations"].labels(operation_type=operation_type).inc()
    
    def update_vector_store_items(self, collection: str, count: int):
        """
        Update the count of items in a vector store collection.
        
        Args:
            collection: Name of the collection.
            count: Number of items in the collection.
        """
        PROM_METRICS["vector_store_items"].labels(collection=collection).set(count)
