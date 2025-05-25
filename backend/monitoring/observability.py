"""
Production-ready monitoring and observability system for AZROI Autonomous AI Architect.
Implements comprehensive logging, metrics, tracing, and health monitoring.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import psutil
import aioredis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'azroi_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'azroi_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'azroi_active_connections',
    'Number of active WebSocket connections'
)

AGENT_EXECUTIONS = Counter(
    'azroi_agent_executions_total',
    'Total agent executions',
    ['agent_type', 'status']
)

AGENT_DURATION = Histogram(
    'azroi_agent_execution_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_type']
)

SYSTEM_MEMORY = Gauge(
    'azroi_system_memory_usage_bytes',
    'System memory usage in bytes',
    ['type']
)

SYSTEM_CPU = Gauge(
    'azroi_system_cpu_percent',
    'System CPU usage percentage'
)

DATABASE_CONNECTIONS = Gauge(
    'azroi_database_connections',
    'Number of database connections',
    ['state']
)

REDIS_CONNECTIONS = Gauge(
    'azroi_redis_connections',
    'Number of Redis connections'
)

@dataclass
class HealthCheckResult:
    """Health check result data structure."""
    service: str
    status: str
    timestamp: datetime
    response_time_ms: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SystemMetricsCollector:
    """Collects and reports system-level metrics."""
    
    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the metrics collection task."""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._collect_metrics())
            logger.info("System metrics collector started")
    
    async def stop(self):
        """Stop the metrics collection task."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("System metrics collector stopped")
    
    async def _collect_metrics(self):
        """Continuously collect system metrics."""
        while self.is_running:
            try:
                # Memory metrics
                memory = psutil.virtual_memory()
                SYSTEM_MEMORY.labels(type='total').set(memory.total)
                SYSTEM_MEMORY.labels(type='available').set(memory.available)
                SYSTEM_MEMORY.labels(type='used').set(memory.used)
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                SYSTEM_CPU.set(cpu_percent)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error

class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self, db_session, redis_client):
        self.db_session = db_session
        self.redis_client = redis_client
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'system': self._check_system,
            'agents': self._check_agents
        }
    
    async def check_health(self, check_name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """Perform health checks."""
        results = {}
        
        if check_name and check_name in self.checks:
            checks_to_run = {check_name: self.checks[check_name]}
        else:
            checks_to_run = self.checks
        
        for name, check_func in checks_to_run.items():
            start_time = time.time()
            try:
                result = await check_func()
                response_time = (time.time() - start_time) * 1000
                
                results[name] = HealthCheckResult(
                    service=name,
                    status='healthy',
                    timestamp=datetime.utcnow(),
                    response_time_ms=response_time,
                    details=result
                )
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                results[name] = HealthCheckResult(
                    service=name,
                    status='unhealthy',
                    timestamp=datetime.utcnow(),
                    response_time_ms=response_time,
                    error=str(e)
                )
                logger.error(f"Health check failed for {name}", error=str(e))
        
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        async with self.db_session() as session:
            start_time = time.time()
            result = await session.execute("SELECT 1")
            query_time = (time.time() - start_time) * 1000
            
            # Check connection pool status
            pool = session.bind.pool
            pool_status = {
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid()
            }
            
            DATABASE_CONNECTIONS.labels(state='active').set(pool.checkedout())
            DATABASE_CONNECTIONS.labels(state='idle').set(pool.checkedin())
            
            return {
                'query_time_ms': query_time,
                'pool_status': pool_status
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        await self.redis_client.ping()
        ping_time = (time.time() - start_time) * 1000
        
        info = await self.redis_client.info()
        memory_usage = info.get('used_memory', 0)
        connected_clients = info.get('connected_clients', 0)
        
        REDIS_CONNECTIONS.set(connected_clients)
        
        return {
            'ping_time_ms': ping_time,
            'memory_usage_bytes': memory_usage,
            'connected_clients': connected_clients,
            'version': info.get('redis_version', 'unknown')
        }
    
    async def _check_system(self) -> Dict[str, Any]:
        """Check system resources."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent
            },
            'disk': {
                'total': disk.total,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            },
            'cpu_percent': cpu_percent
        }
    
    async def _check_agents(self) -> Dict[str, Any]:
        """Check agent system status."""
        # This would check the agent orchestrator status
        # Implementation depends on your agent system
        return {
            'orchestrator_status': 'running',
            'agent_types_available': 8,
            'active_sessions': 0  # Would get from session manager
        }

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract route pattern for metrics
        route = request.url.path
        method = request.method
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=method,
            endpoint=route,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=route
        ).observe(duration)
        
        # Log request
        logger.info(
            "HTTP request processed",
            method=method,
            path=route,
            status_code=response.status_code,
            duration_ms=duration * 1000,
            user_agent=request.headers.get('user-agent', ''),
            remote_addr=request.client.host if request.client else ''
        )
        
        return response

class TracingSetup:
    """OpenTelemetry tracing configuration."""
    
    @staticmethod
    def setup_tracing(service_name: str, environment: str, azure_connection_string: Optional[str] = None):
        """Set up distributed tracing with Jaeger and Azure Monitor."""
        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        # Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        # Azure Monitor exporter (if configured)
        exporters = [jaeger_exporter]
        if azure_connection_string:
            azure_exporter = AzureMonitorTraceExporter(
                connection_string=azure_connection_string
            )
            exporters.append(azure_exporter)
        
        # Add span processors
        for exporter in exporters:
            span_processor = BatchSpanProcessor(exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
        
        # Instrument frameworks
        FastAPIInstrumentor.instrument()
        SQLAlchemyInstrumentor.instrument()
        RedisInstrumentor.instrument()
        
        logger.info(f"Tracing setup completed for service: {service_name}")

class AlertManager:
    """Manages alerts and notifications for system events."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.alert_rules = {
            'high_cpu': {'threshold': 80, 'duration': 300},  # 80% for 5 minutes
            'low_memory': {'threshold': 90, 'duration': 300},  # 90% for 5 minutes
            'high_error_rate': {'threshold': 0.05, 'duration': 300},  # 5% for 5 minutes
            'slow_response': {'threshold': 5000, 'duration': 300}  # 5 seconds for 5 minutes
        }
    
    async def check_alert_conditions(self, metrics: Dict[str, float]):
        """Check if any alert conditions are met."""
        current_time = time.time()
        
        for rule_name, rule_config in self.alert_rules.items():
            if await self._should_trigger_alert(rule_name, metrics, rule_config, current_time):
                await self._trigger_alert(rule_name, metrics[rule_name])
    
    async def _should_trigger_alert(self, rule_name: str, metrics: Dict[str, float], 
                                   rule_config: Dict, current_time: float) -> bool:
        """Check if alert should be triggered based on rule configuration."""
        if rule_name not in metrics:
            return False
        
        current_value = metrics[rule_name]
        threshold = rule_config['threshold']
        duration = rule_config['duration']
        
        # Check if current value exceeds threshold
        if current_value <= threshold:
            # Clear any existing alert state
            await self.redis_client.delete(f"alert:{rule_name}:start_time")
            return False
        
        # Check how long the condition has been true
        start_time_key = f"alert:{rule_name}:start_time"
        start_time = await self.redis_client.get(start_time_key)
        
        if start_time is None:
            # First time exceeding threshold
            await self.redis_client.set(start_time_key, current_time, ex=duration + 60)
            return False
        
        # Check if duration threshold is met
        if current_time - float(start_time) >= duration:
            return True
        
        return False
    
    async def _trigger_alert(self, alert_name: str, current_value: float):
        """Trigger an alert notification."""
        alert_data = {
            'alert_name': alert_name,
            'current_value': current_value,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'warning'
        }
        
        # Store alert in Redis for notification processing
        await self.redis_client.lpush('alerts:queue', json.dumps(alert_data))
        
        logger.warning(
            "Alert triggered",
            alert_name=alert_name,
            current_value=current_value
        )

# Monitoring initialization function
async def setup_monitoring(app: FastAPI, config):
    """Set up comprehensive monitoring for the application."""
    # Initialize Redis for monitoring
    redis_client = aioredis.from_url(config.redis.url)
    
    # Initialize health checker
    health_checker = HealthChecker(None, redis_client)  # Pass actual db_session
    
    # Initialize system metrics collector
    metrics_collector = SystemMetricsCollector()
    await metrics_collector.start()
    
    # Initialize alert manager
    alert_manager = AlertManager(redis_client)
    
    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware)
    
    # Set up tracing
    TracingSetup.setup_tracing(
        service_name="azroi-autonomous-ai-architect",
        environment=config.environment,
        azure_connection_string=getattr(config.monitoring, 'azure_connection_string', None)
    )
    
    # Add shutdown handler
    @app.on_event("shutdown")
    async def shutdown_monitoring():
        await metrics_collector.stop()
        await redis_client.close()
    
    # Store components for use in routes
    app.state.health_checker = health_checker
    app.state.metrics_collector = metrics_collector
    app.state.alert_manager = alert_manager
    app.state.monitoring_redis = redis_client
    
    logger.info("Monitoring system initialized successfully")

# Health check endpoints
async def health_endpoint(app: FastAPI):
    """Health check endpoint handler."""
    health_checker = app.state.health_checker
    results = await health_checker.check_health()
    
    overall_status = "healthy" if all(
        result.status == "healthy" for result in results.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {name: asdict(result) for name, result in results.items()}
    }

async def metrics_endpoint():
    """Prometheus metrics endpoint handler."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
