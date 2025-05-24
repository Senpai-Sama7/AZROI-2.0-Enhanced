"""
Comprehensive monitoring and metrics system for AZROI
"""
import time
import psutil
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import threading
from enum import Enum

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, Summary,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
        start_http_server
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from ..config.settings import get_monitoring_config
from ..logging.structured_logging import get_component_logger


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"


@dataclass
class MetricPoint:
    """A single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    disk_total_gb: float
    network_sent_mb: float
    network_recv_mb: float
    load_average: List[float]
    process_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class AgentMetrics:
    """Agent-specific metrics"""
    agent_id: str
    agent_type: str
    status: str
    tasks_completed: int
    tasks_failed: int
    average_execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    last_activity: datetime
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CrewMetrics:
    """Crew-specific metrics"""
    crew_id: str
    crew_name: str
    status: str
    agent_count: int
    tasks_completed: int
    tasks_in_progress: int
    tasks_failed: int
    total_execution_time: float
    average_task_time: float
    created_at: datetime
    last_activity: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class MetricsCollector:
    """Base metrics collector"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_component_logger(f"metrics.{name}")
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._max_points = 10000  # Maximum points to keep in memory
    
    def record_metric(self, metric_name: str, value: float, 
                     labels: Dict[str, str] = None, 
                     metadata: Dict[str, Any] = None):
        """Record a metric value"""
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self._metrics[metric_name].append(point)
        
        # Trim old points if we exceed max
        if len(self._metrics[metric_name]) > self._max_points:
            self._metrics[metric_name] = self._metrics[metric_name][-self._max_points:]
        
        self.logger.debug(
            f"Metric recorded: {metric_name}",
            metric_name=metric_name,
            value=value,
            labels=labels,
            metadata=metadata
        )
    
    def get_metric_history(self, metric_name: str, 
                          since: Optional[datetime] = None) -> List[MetricPoint]:
        """Get metric history"""
        points = self._metrics.get(metric_name, [])
        
        if since:
            points = [p for p in points if p.timestamp >= since]
        
        return points
    
    def get_latest_metric(self, metric_name: str) -> Optional[MetricPoint]:
        """Get the latest value for a metric"""
        points = self._metrics.get(metric_name, [])
        return points[-1] if points else None
    
    def get_metric_summary(self, metric_name: str, 
                          since: Optional[datetime] = None) -> Dict[str, float]:
        """Get metric summary statistics"""
        points = self.get_metric_history(metric_name, since)
        
        if not points:
            return {}
        
        values = [p.value for p in points]
        
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1]
        }
    
    def clear_metrics(self, metric_name: Optional[str] = None):
        """Clear metrics"""
        if metric_name:
            self._metrics.pop(metric_name, None)
        else:
            self._metrics.clear()


class SystemMetricsCollector(MetricsCollector):
    """System performance metrics collector"""
    
    def __init__(self):
        super().__init__("system")
        self._collecting = False
        self._collection_task: Optional[asyncio.Task] = None
        self._network_counters = None
    
    async def start_collection(self, interval: int = 15):
        """Start collecting system metrics"""
        if self._collecting:
            return
        
        self._collecting = True
        self._collection_task = asyncio.create_task(self._collect_loop(interval))
        self.logger.info("System metrics collection started", interval=interval)
    
    async def stop_collection(self):
        """Stop collecting system metrics"""
        self._collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("System metrics collection stopped")
    
    async def _collect_loop(self, interval: int):
        """Main collection loop"""
        while self._collecting:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error collecting system metrics", error=e)
                await asyncio.sleep(interval)
    
    async def collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.record_metric("cpu_usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_metric("memory_usage_percent", memory.percent)
            self.record_metric("memory_used_gb", memory.used / (1024**3))
            self.record_metric("memory_total_gb", memory.total / (1024**3))
            self.record_metric("memory_available_gb", memory.available / (1024**3))
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            self.record_metric("disk_usage_percent", disk_usage_percent)
            self.record_metric("disk_free_gb", disk.free / (1024**3))
            self.record_metric("disk_total_gb", disk.total / (1024**3))
            
            # Network metrics
            net_io = psutil.net_io_counters()
            if self._network_counters:
                sent_mb = (net_io.bytes_sent - self._network_counters.bytes_sent) / (1024**2)
                recv_mb = (net_io.bytes_recv - self._network_counters.bytes_recv) / (1024**2)
                self.record_metric("network_sent_mb_delta", sent_mb)
                self.record_metric("network_recv_mb_delta", recv_mb)
            
            self.record_metric("network_sent_mb_total", net_io.bytes_sent / (1024**2))
            self.record_metric("network_recv_mb_total", net_io.bytes_recv / (1024**2))
            self._network_counters = net_io
            
            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()
                self.record_metric("load_average_1m", load_avg[0])
                self.record_metric("load_average_5m", load_avg[1])
                self.record_metric("load_average_15m", load_avg[2])
            except (AttributeError, OSError):
                # getloadavg not available on Windows
                pass
            
            # Process count
            process_count = len(psutil.pids())
            self.record_metric("process_count", process_count)
            
            # Create SystemMetrics object
            metrics = SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_total_gb=memory.total / (1024**3),
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk.free / (1024**3),
                disk_total_gb=disk.total / (1024**3),
                network_sent_mb=net_io.bytes_sent / (1024**2),
                network_recv_mb=net_io.bytes_recv / (1024**2),
                load_average=list(load_avg) if 'load_avg' in locals() else [],
                process_count=process_count
            )
            
            self.logger.debug("System metrics collected", **metrics.to_dict())
            
        except Exception as e:
            self.logger.error("Failed to collect system metrics", error=e)
    
    def get_current_system_metrics(self) -> Optional[SystemMetrics]:
        """Get current system metrics as a structured object"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()
            
            try:
                load_avg = list(psutil.getloadavg())
            except (AttributeError, OSError):
                load_avg = []
            
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_total_gb=memory.total / (1024**3),
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_free_gb=disk.free / (1024**3),
                disk_total_gb=disk.total / (1024**3),
                network_sent_mb=net_io.bytes_sent / (1024**2),
                network_recv_mb=net_io.bytes_recv / (1024**2),
                load_average=load_avg,
                process_count=len(psutil.pids())
            )
        except Exception as e:
            self.logger.error("Failed to get current system metrics", error=e)
            return None


class AgentMetricsCollector(MetricsCollector):
    """Agent-specific metrics collector"""
    
    def __init__(self):
        super().__init__("agent")
        self._agent_metrics: Dict[str, AgentMetrics] = {}
        self._agent_timers: Dict[str, List[float]] = defaultdict(list)
    
    def register_agent(self, agent_id: str, agent_type: str):
        """Register a new agent"""
        self._agent_metrics[agent_id] = AgentMetrics(
            agent_id=agent_id,
            agent_type=agent_type,
            status="idle",
            tasks_completed=0,
            tasks_failed=0,
            average_execution_time=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            last_activity=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        
        self.logger.info("Agent registered", agent_id=agent_id, agent_type=agent_type)
    
    def update_agent_status(self, agent_id: str, status: str):
        """Update agent status"""
        if agent_id in self._agent_metrics:
            self._agent_metrics[agent_id].status = status
            self._agent_metrics[agent_id].last_activity = datetime.now(timezone.utc)
            
            self.record_metric(
                "agent_status_change",
                1,
                labels={"agent_id": agent_id, "status": status}
            )
    
    def record_task_completion(self, agent_id: str, execution_time: float, success: bool):
        """Record task completion"""
        if agent_id not in self._agent_metrics:
            return
        
        metrics = self._agent_metrics[agent_id]
        
        if success:
            metrics.tasks_completed += 1
        else:
            metrics.tasks_failed += 1
        
        # Update execution time average
        self._agent_timers[agent_id].append(execution_time)
        if len(self._agent_timers[agent_id]) > 100:  # Keep last 100 times
            self._agent_timers[agent_id] = self._agent_timers[agent_id][-100:]
        
        metrics.average_execution_time = sum(self._agent_timers[agent_id]) / len(self._agent_timers[agent_id])
        metrics.last_activity = datetime.now(timezone.utc)
        
        # Record metrics
        self.record_metric(
            "agent_task_completion",
            1,
            labels={"agent_id": agent_id, "success": str(success)}
        )
        
        self.record_metric(
            "agent_task_duration",
            execution_time,
            labels={"agent_id": agent_id}
        )
    
    def update_agent_resources(self, agent_id: str, memory_mb: float, cpu_percent: float):
        """Update agent resource usage"""
        if agent_id in self._agent_metrics:
            self._agent_metrics[agent_id].memory_usage_mb = memory_mb
            self._agent_metrics[agent_id].cpu_usage_percent = cpu_percent
            
            self.record_metric(
                "agent_memory_usage",
                memory_mb,
                labels={"agent_id": agent_id}
            )
            
            self.record_metric(
                "agent_cpu_usage",
                cpu_percent,
                labels={"agent_id": agent_id}
            )
    
    def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent"""
        return self._agent_metrics.get(agent_id)
    
    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents"""
        return self._agent_metrics.copy()
    
    def remove_agent(self, agent_id: str):
        """Remove agent from tracking"""
        self._agent_metrics.pop(agent_id, None)
        self._agent_timers.pop(agent_id, None)
        self.logger.info("Agent removed from metrics", agent_id=agent_id)


class CrewMetricsCollector(MetricsCollector):
    """Crew-specific metrics collector"""
    
    def __init__(self):
        super().__init__("crew")
        self._crew_metrics: Dict[str, CrewMetrics] = {}
        self._crew_timers: Dict[str, List[float]] = defaultdict(list)
    
    def register_crew(self, crew_id: str, crew_name: str):
        """Register a new crew"""
        self._crew_metrics[crew_id] = CrewMetrics(
            crew_id=crew_id,
            crew_name=crew_name,
            status="idle",
            agent_count=0,
            tasks_completed=0,
            tasks_in_progress=0,
            tasks_failed=0,
            total_execution_time=0.0,
            average_task_time=0.0,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc)
        )
        
        self.logger.info("Crew registered", crew_id=crew_id, crew_name=crew_name)
    
    def update_crew_status(self, crew_id: str, status: str):
        """Update crew status"""
        if crew_id in self._crew_metrics:
            self._crew_metrics[crew_id].status = status
            self._crew_metrics[crew_id].last_activity = datetime.now(timezone.utc)
            
            self.record_metric(
                "crew_status_change",
                1,
                labels={"crew_id": crew_id, "status": status}
            )
    
    def update_crew_agents(self, crew_id: str, agent_count: int):
        """Update crew agent count"""
        if crew_id in self._crew_metrics:
            self._crew_metrics[crew_id].agent_count = agent_count
            
            self.record_metric(
                "crew_agent_count",
                agent_count,
                labels={"crew_id": crew_id}
            )
    
    def record_crew_task(self, crew_id: str, task_duration: float, success: bool):
        """Record crew task completion"""
        if crew_id not in self._crew_metrics:
            return
        
        metrics = self._crew_metrics[crew_id]
        
        if success:
            metrics.tasks_completed += 1
        else:
            metrics.tasks_failed += 1
        
        metrics.total_execution_time += task_duration
        
        # Update average
        self._crew_timers[crew_id].append(task_duration)
        if len(self._crew_timers[crew_id]) > 100:
            self._crew_timers[crew_id] = self._crew_timers[crew_id][-100:]
        
        metrics.average_task_time = sum(self._crew_timers[crew_id]) / len(self._crew_timers[crew_id])
        metrics.last_activity = datetime.now(timezone.utc)
        
        # Record metrics
        self.record_metric(
            "crew_task_completion",
            1,
            labels={"crew_id": crew_id, "success": str(success)}
        )
        
        self.record_metric(
            "crew_task_duration",
            task_duration,
            labels={"crew_id": crew_id}
        )
    
    def get_crew_metrics(self, crew_id: str) -> Optional[CrewMetrics]:
        """Get metrics for a specific crew"""
        return self._crew_metrics.get(crew_id)
    
    def get_all_crew_metrics(self) -> Dict[str, CrewMetrics]:
        """Get metrics for all crews"""
        return self._crew_metrics.copy()
    
    def remove_crew(self, crew_id: str):
        """Remove crew from tracking"""
        self._crew_metrics.pop(crew_id, None)
        self._crew_timers.pop(crew_id, None)
        self.logger.info("Crew removed from metrics", crew_id=crew_id)


class PrometheusMetrics:
    """Prometheus metrics exporter"""
    
    def __init__(self):
        self.config = get_monitoring_config()
        self.logger = get_component_logger("prometheus")
        
        if not PROMETHEUS_AVAILABLE:
            self.logger.warning("Prometheus client not available")
            return
        
        self.registry = CollectorRegistry()
        self._setup_metrics()
        self._server_started = False
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # System metrics
        self.cpu_usage = Gauge(
            'azroi_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'azroi_memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )
        
        self.disk_usage = Gauge(
            'azroi_disk_usage_percent',
            'Disk usage percentage',
            registry=self.registry
        )
        
        # Agent metrics
        self.agent_tasks_total = Counter(
            'azroi_agent_tasks_total',
            'Total number of agent tasks',
            ['agent_id', 'agent_type', 'status'],
            registry=self.registry
        )
        
        self.agent_task_duration = Histogram(
            'azroi_agent_task_duration_seconds',
            'Agent task duration in seconds',
            ['agent_id', 'agent_type'],
            registry=self.registry
        )
        
        # Crew metrics
        self.crew_tasks_total = Counter(
            'azroi_crew_tasks_total',
            'Total number of crew tasks',
            ['crew_id', 'crew_name', 'status'],
            registry=self.registry
        )
        
        self.crew_task_duration = Histogram(
            'azroi_crew_task_duration_seconds',
            'Crew task duration in seconds',
            ['crew_id', 'crew_name'],
            registry=self.registry
        )
        
        # API metrics
        self.http_requests_total = Counter(
            'azroi_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'azroi_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
    
    def start_server(self):
        """Start Prometheus metrics server"""
        if not PROMETHEUS_AVAILABLE or self._server_started:
            return
        
        try:
            start_http_server(self.config.prometheus_port, registry=self.registry)
            self._server_started = True
            self.logger.info(
                "Prometheus metrics server started",
                port=self.config.prometheus_port
            )
        except Exception as e:
            self.logger.error("Failed to start Prometheus server", error=e)
    
    def update_system_metrics(self, metrics: SystemMetrics):
        """Update system metrics in Prometheus"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.cpu_usage.set(metrics.cpu_usage_percent)
        self.memory_usage.set(metrics.memory_usage_percent)
        self.disk_usage.set(metrics.disk_usage_percent)
    
    def record_agent_task(self, agent_id: str, agent_type: str, duration: float, success: bool):
        """Record agent task metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        status = "success" if success else "failed"
        self.agent_tasks_total.labels(
            agent_id=agent_id,
            agent_type=agent_type,
            status=status
        ).inc()
        
        self.agent_task_duration.labels(
            agent_id=agent_id,
            agent_type=agent_type
        ).observe(duration)
    
    def record_crew_task(self, crew_id: str, crew_name: str, duration: float, success: bool):
        """Record crew task metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        status = "success" if success else "failed"
        self.crew_tasks_total.labels(
            crew_id=crew_id,
            crew_name=crew_name,
            status=status
        ).inc()
        
        self.crew_task_duration.labels(
            crew_id=crew_id,
            crew_name=crew_name
        ).observe(duration)
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        if not PROMETHEUS_AVAILABLE:
            return ""
        
        return generate_latest(self.registry).decode('utf-8')


class HealthChecker:
    """System health checker"""
    
    def __init__(self):
        self.config = get_monitoring_config()
        self.logger = get_component_logger("health")
        self._checks: Dict[str, Callable] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check"""
        self._checks[name] = check_func
        self.logger.info("Health check registered", check_name=name)
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_healthy = True
        
        for name, check_func in self._checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await asyncio.wait_for(
                        check_func(),
                        timeout=self.config.health_check_timeout
                    )
                else:
                    result = check_func()
                
                duration = time.time() - start_time
                
                results[name] = {
                    "healthy": bool(result),
                    "duration_seconds": duration,
                    "details": result if isinstance(result, dict) else None
                }
                
                if not result:
                    overall_healthy = False
                
            except asyncio.TimeoutError:
                results[name] = {
                    "healthy": False,
                    "error": "Health check timeout",
                    "duration_seconds": self.config.health_check_timeout
                }
                overall_healthy = False
                
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                    "duration_seconds": time.time() - start_time
                }
                overall_healthy = False
        
        return {
            "healthy": overall_healthy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": results
        }


class MonitoringManager:
    """Main monitoring manager that coordinates all monitoring components"""
    
    def __init__(self):
        self.config = get_monitoring_config()
        self.logger = get_component_logger("monitoring")
        
        # Initialize collectors
        self.system_collector = SystemMetricsCollector()
        self.agent_collector = AgentMetricsCollector()
        self.crew_collector = CrewMetricsCollector()
        
        # Initialize Prometheus if available
        self.prometheus = PrometheusMetrics() if PROMETHEUS_AVAILABLE else None
        
        # Initialize health checker
        self.health_checker = HealthChecker()
        
        # Setup default health checks
        self._setup_default_health_checks()
        
        self._started = False
    
    def _setup_default_health_checks(self):
        """Setup default health checks"""
        def check_memory():
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Less than 90% memory usage
        
        def check_disk():
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) < 0.9  # Less than 90% disk usage
        
        async def check_system_responsive():
            # Simple responsiveness check
            start = time.time()
            await asyncio.sleep(0.01)
            return (time.time() - start) < 0.1
        
        self.health_checker.register_check("memory", check_memory)
        self.health_checker.register_check("disk", check_disk)
        self.health_checker.register_check("responsive", check_system_responsive)
    
    async def start(self):
        """Start monitoring"""
        if self._started:
            return
        
        self.logger.info("Starting monitoring system")
        
        # Start system metrics collection
        if self.config.collect_hardware_metrics:
            await self.system_collector.start_collection(self.config.metrics_interval)
        
        # Start Prometheus server
        if self.prometheus and self.config.prometheus_enabled:
            self.prometheus.start_server()
        
        self._started = True
        self.logger.info("Monitoring system started")
    
    async def stop(self):
        """Stop monitoring"""
        if not self._started:
            return
        
        self.logger.info("Stopping monitoring system")
        
        # Stop system metrics collection
        await self.system_collector.stop_collection()
        
        self._started = False
        self.logger.info("Monitoring system stopped")
    
    def get_system_metrics(self) -> Optional[SystemMetrics]:
        """Get current system metrics"""
        return self.system_collector.get_current_system_metrics()
    
    def get_agent_metrics(self, agent_id: str = None) -> Union[AgentMetrics, Dict[str, AgentMetrics], None]:
        """Get agent metrics"""
        if agent_id:
            return self.agent_collector.get_agent_metrics(agent_id)
        return self.agent_collector.get_all_agent_metrics()
    
    def get_crew_metrics(self, crew_id: str = None) -> Union[CrewMetrics, Dict[str, CrewMetrics], None]:
        """Get crew metrics"""
        if crew_id:
            return self.crew_collector.get_crew_metrics(crew_id)
        return self.crew_collector.get_all_crew_metrics()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        return await self.health_checker.run_checks()
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics"""
        if self.prometheus:
            return self.prometheus.get_metrics()
        return ""
    
    @asynccontextmanager
    async def track_operation(self, operation_name: str, **labels):
        """Context manager for tracking operation duration"""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        finally:
            duration = time.time() - start_time
            
            # Log operation
            self.logger.info(
                f"Operation {operation_name} completed",
                operation=operation_name,
                duration_seconds=duration,
                success=success,
                **labels
            )
            
            # Record in collectors
            self.system_collector.record_metric(
                f"operation_duration_{operation_name}",
                duration,
                labels={"success": str(success), **labels}
            )


# Global monitoring manager
_monitoring_manager: Optional[MonitoringManager] = None


def get_monitoring_manager() -> MonitoringManager:
    """Get the global monitoring manager"""
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager()
    return _monitoring_manager


# Convenience functions
def get_system_metrics() -> Optional[SystemMetrics]:
    """Get current system metrics"""
    return get_monitoring_manager().get_system_metrics()


def get_agent_metrics(agent_id: str = None):
    """Get agent metrics"""
    return get_monitoring_manager().get_agent_metrics(agent_id)


def get_crew_metrics(crew_id: str = None):
    """Get crew metrics"""
    return get_monitoring_manager().get_crew_metrics(crew_id)


async def get_health_status() -> Dict[str, Any]:
    """Get system health status"""
    return await get_monitoring_manager().get_health_status()


def track_operation(operation_name: str, **labels):
    """Track operation duration"""
    return get_monitoring_manager().track_operation(operation_name, **labels)
