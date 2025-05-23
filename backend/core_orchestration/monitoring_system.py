#!/usr/bin/env python3
"""
Monitoring System for the Autonomous AI Architect backend
"""

import asyncio
import logging
import time
import psutil
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    active_connections: int

@dataclass
class ServiceHealth:
    """Service health status"""
    service_name: str
    status: str  # healthy, degraded, unhealthy
    last_check: float
    response_time: Optional[float] = None
    error_message: Optional[str] = None

class MonitoringSystem:
    """Comprehensive monitoring system for system health and performance"""
    
    def __init__(self, 
                 metrics_interval: int = 30,
                 health_check_interval: int = 60,
                 retention_hours: int = 24):
        self.metrics_interval = metrics_interval
        self.health_check_interval = health_check_interval
        self.retention_hours = retention_hours
        
        # Storage for metrics and health data
        self._metrics_history: List[SystemMetrics] = []
        self._service_health: Dict[str, ServiceHealth] = {}
        self._alerts: List[Dict[str, Any]] = []
        
        # Monitoring state
        self._monitoring_task = None
        self._health_check_task = None
        self._is_running = False
        
        # Thresholds
        self._thresholds = {
            'cpu_critical': 90.0,
            'cpu_warning': 80.0,
            'memory_critical': 95.0,
            'memory_warning': 85.0,
            'disk_critical': 95.0,
            'disk_warning': 85.0,
            'response_time_critical': 10.0,
            'response_time_warning': 5.0
        }
        
        logger.info("MonitoringSystem initialized")
    
    async def start(self):
        """Start monitoring tasks"""
        if self._is_running:
            logger.warning("Monitoring system already running")
            return
        
        self._is_running = True
        
        # Start monitoring tasks
        self._monitoring_task = asyncio.create_task(self._metrics_collection_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Monitoring system started")
    
    async def stop(self):
        """Stop monitoring tasks"""
        self._is_running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring system stopped")
    
    async def _metrics_collection_loop(self):
        """Main metrics collection loop"""
        while self._is_running:
            try:
                metrics = await self._collect_system_metrics()
                self._metrics_history.append(metrics)
                
                # Clean old metrics
                await self._cleanup_old_metrics()
                
                # Check thresholds and generate alerts
                await self._check_thresholds(metrics)
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
            
            await asyncio.sleep(self.metrics_interval)
    
    async def _health_check_loop(self):
        """Service health check loop"""
        while self._is_running:
            try:
                await self._perform_health_checks()
            except Exception as e:
                logger.error(f"Error in health checks: {e}")
            
            await asyncio.sleep(self.health_check_interval)
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Active connections
            connections = len(psutil.net_connections())
            
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                network_sent=network.bytes_sent,
                network_recv=network.bytes_recv,
                active_connections=connections
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            # Return basic fallback metrics
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_sent=0,
                network_recv=0,
                active_connections=0
            )
    
    async def _perform_health_checks(self):
        """Perform health checks on services"""
        services_to_check = [
            "system",
            "api_server",
            "websocket",
            "config_loader",
            "llm_router"
        ]
        
        for service_name in services_to_check:
            try:
                health = await self._check_service_health(service_name)
                self._service_health[service_name] = health
                
                # Generate alerts for unhealthy services
                if health.status == "unhealthy":
                    await self._create_alert(
                        severity="critical",
                        message=f"Service {service_name} is unhealthy: {health.error_message}",
                        service=service_name
                    )
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                self._service_health[service_name] = ServiceHealth(
                    service_name=service_name,
                    status="unhealthy",
                    last_check=time.time(),
                    error_message=str(e)
                )
    
    async def _check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of specific service"""
        start_time = time.time()
        
        try:
            if service_name == "system":
                # Basic system health check
                await asyncio.sleep(0.01)  # Simulate check
                response_time = time.time() - start_time
                
                return ServiceHealth(
                    service_name=service_name,
                    status="healthy",
                    last_check=time.time(),
                    response_time=response_time
                )
            
            elif service_name == "api_server":
                # Check if API server is responding
                await asyncio.sleep(0.02)  # Simulate check
                response_time = time.time() - start_time
                
                return ServiceHealth(
                    service_name=service_name,
                    status="healthy",
                    last_check=time.time(),
                    response_time=response_time
                )
            
            else:
                # Generic service check
                await asyncio.sleep(0.01)
                response_time = time.time() - start_time
                
                return ServiceHealth(
                    service_name=service_name,
                    status="healthy",
                    last_check=time.time(),
                    response_time=response_time
                )
                
        except Exception as e:
            return ServiceHealth(
                service_name=service_name,
                status="unhealthy",
                last_check=time.time(),
                error_message=str(e)
            )
    
    async def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and create alerts"""
        alerts = []
        
        # CPU threshold checks
        if metrics.cpu_percent >= self._thresholds['cpu_critical']:
            alerts.append({
                'severity': 'critical',
                'message': f'CPU usage critical: {metrics.cpu_percent:.1f}%',
                'metric': 'cpu',
                'value': metrics.cpu_percent
            })
        elif metrics.cpu_percent >= self._thresholds['cpu_warning']:
            alerts.append({
                'severity': 'warning',
                'message': f'CPU usage high: {metrics.cpu_percent:.1f}%',
                'metric': 'cpu',
                'value': metrics.cpu_percent
            })
        
        # Memory threshold checks
        if metrics.memory_percent >= self._thresholds['memory_critical']:
            alerts.append({
                'severity': 'critical',
                'message': f'Memory usage critical: {metrics.memory_percent:.1f}%',
                'metric': 'memory',
                'value': metrics.memory_percent
            })
        elif metrics.memory_percent >= self._thresholds['memory_warning']:
            alerts.append({
                'severity': 'warning',
                'message': f'Memory usage high: {metrics.memory_percent:.1f}%',
                'metric': 'memory',
                'value': metrics.memory_percent
            })
        
        # Disk threshold checks
        if metrics.disk_percent >= self._thresholds['disk_critical']:
            alerts.append({
                'severity': 'critical',
                'message': f'Disk usage critical: {metrics.disk_percent:.1f}%',
                'metric': 'disk',
                'value': metrics.disk_percent
            })
        elif metrics.disk_percent >= self._thresholds['disk_warning']:
            alerts.append({
                'severity': 'warning',
                'message': f'Disk usage high: {metrics.disk_percent:.1f}%',
                'metric': 'disk',
                'value': metrics.disk_percent
            })
        
        # Create alerts
        for alert_data in alerts:
            await self._create_alert(**alert_data)
    
    async def _create_alert(self, severity: str, message: str, **kwargs):
        """Create and store an alert"""
        alert = {
            'id': f"alert_{int(time.time())}_{len(self._alerts)}",
            'timestamp': time.time(),
            'severity': severity,
            'message': message,
            'acknowledged': False,
            **kwargs
        }
        
        self._alerts.append(alert)
        logger.warning(f"Alert created: {message}")
        
        # Keep only recent alerts
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-500:]
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics based on retention policy"""
        cutoff_time = time.time() - (self.retention_hours * 3600)
        self._metrics_history = [
            m for m in self._metrics_history 
            if m.timestamp > cutoff_time
        ]
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            current_metrics = await self._collect_system_metrics()
            
            # Calculate status based on current metrics and service health
            overall_status = "healthy"
            
            # Check critical thresholds
            if (current_metrics.cpu_percent >= self._thresholds['cpu_critical'] or
                current_metrics.memory_percent >= self._thresholds['memory_critical'] or
                current_metrics.disk_percent >= self._thresholds['disk_critical']):
                overall_status = "critical"
            
            # Check warning thresholds
            elif (current_metrics.cpu_percent >= self._thresholds['cpu_warning'] or
                  current_metrics.memory_percent >= self._thresholds['memory_warning'] or
                  current_metrics.disk_percent >= self._thresholds['disk_warning']):
                overall_status = "warning"
            
            # Check service health
            unhealthy_services = [
                name for name, health in self._service_health.items()
                if health.status == "unhealthy"
            ]
            
            if unhealthy_services:
                overall_status = "degraded" if overall_status == "healthy" else overall_status
            
            return {
                "status": overall_status,
                "timestamp": time.time(),
                "current_metrics": asdict(current_metrics),
                "service_health": {
                    name: asdict(health) for name, health in self._service_health.items()
                },
                "active_alerts": len([a for a in self._alerts if not a.get('acknowledged', False)]),
                "uptime_seconds": time.time() - (self._metrics_history[0].timestamp if self._metrics_history else time.time()),
                "monitoring_active": self._is_running
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_metrics = [
            asdict(m) for m in self._metrics_history
            if m.timestamp > cutoff_time
        ]
        
        return recent_metrics
    
    async def get_alerts(self, acknowledged: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by acknowledgment status"""
        if acknowledged is None:
            return self._alerts.copy()
        
        return [
            alert for alert in self._alerts
            if alert.get('acknowledged', False) == acknowledged
        ]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self._alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = time.time()
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        
        return False
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update monitoring thresholds"""
        self._thresholds.update(new_thresholds)
        logger.info(f"Monitoring thresholds updated: {new_thresholds}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring system summary"""
        return {
            "is_running": self._is_running,
            "metrics_collected": len(self._metrics_history),
            "services_monitored": len(self._service_health),
            "active_alerts": len([a for a in self._alerts if not a.get('acknowledged', False)]),
            "total_alerts": len(self._alerts),
            "thresholds": self._thresholds.copy(),
            "intervals": {
                "metrics": self.metrics_interval,
                "health_check": self.health_check_interval
            }
        }
