#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/core_orchestration/hardware_audit.py

import os
import platform
import socket
import json
import logging
import psutil
import time
from typing import Dict, Any, List, Optional
import threading

logger = logging.getLogger("ai-architect-backend.hardware_audit")

class HardwareAuditSystem:
    """
    System for auditing hardware resources and monitoring system performance.
    This is critical for ensuring system stability and preventing resource exhaustion.
    """
    
    def __init__(self, metrics_interval: int = 15):
        """
        Initialize the hardware audit system.
        
        Args:
            metrics_interval: Interval in seconds for collecting metrics.
        """
        self.metrics_interval = metrics_interval
        self.running = False
        self.metrics_thread = None
        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
        self.system_info = None
        self.max_history_points = 1000  # Maximum number of history points to keep
        self._collect_system_info()  # Collect system info on initialization
    
    def _collect_system_info(self):
        """
        Collect comprehensive information about the system hardware.
        """
        try:
            # Basic system info
            self.system_info = {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "architecture": platform.architecture(),
                "cpu_count": psutil.cpu_count(logical=True),
                "physical_cpu_count": psutil.cpu_count(logical=False),
                "total_memory_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "disk_partitions": []
            }
            
            # Get disk partitions
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self.system_info["disk_partitions"].append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024 ** 3), 2),
                        "used_gb": round(usage.used / (1024 ** 3), 2),
                        "percent_used": usage.percent
                    })
                except PermissionError:
                    # Some mountpoints may not be accessible
                    pass
            
            # Get network info
            if hasattr(psutil, "net_if_addrs"):
                self.system_info["network_interfaces"] = {}
                for interface, addresses in psutil.net_if_addrs().items():
                    self.system_info["network_interfaces"][interface] = []
                    for addr in addresses:
                        addr_info = {
                            "family": str(addr.family),
                            "address": addr.address
                        }
                        if addr.netmask:
                            addr_info["netmask"] = addr.netmask
                        if addr.broadcast:
                            addr_info["broadcast"] = addr.broadcast
                        self.system_info["network_interfaces"][interface].append(addr_info)
            
            # GPU information (if available)
            try:
                # Try to detect NVIDIA GPUs using nvidia-smi
                import subprocess
                result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu', 
                                       '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True, check=True)
                
                self.system_info["gpus"] = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 4:
                            self.system_info["gpus"].append({
                                "name": parts[0],
                                "memory_total_gb": float(parts[1]) / 1024,  # MB to GB
                                "memory_used_gb": float(parts[2]) / 1024,
                                "utilization_percent": float(parts[3])
                            })
            except (ImportError, subprocess.SubprocessError, FileNotFoundError):
                # No NVIDIA GPUs or nvidia-smi not available
                self.system_info["gpus"] = []
            
            logger.info("System information collected successfully")
        except Exception as e:
            logger.error(f"Error collecting system information: {str(e)}")
            self.system_info = {"error": str(e)}
    
    def start_metrics_collection(self):
        """
        Start collecting metrics in a background thread.
        """
        if self.running:
            return
        
        self.running = True
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        self.metrics_thread.start()
        logger.info(f"Started hardware metrics collection thread (interval: {self.metrics_interval}s)")
    
    def stop_metrics_collection(self):
        """
        Stop the metrics collection thread.
        """
        self.running = False
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=5)
        logger.info("Stopped hardware metrics collection")
    
    def _metrics_collection_loop(self):
        """
        Background thread function for collecting metrics.
        """
        last_network_io = self._get_network_io()
        last_time = time.time()
        
        while self.running:
            try:
                # Sleep for the metrics interval
                time.sleep(self.metrics_interval)
                
                # Collect current metrics
                current_time = time.time()
                elapsed = current_time - last_time
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                per_cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_data = {
                    "total_gb": memory.total / (1024 ** 3),
                    "available_gb": memory.available / (1024 ** 3),
                    "used_gb": memory.used / (1024 ** 3),
                    "percent": memory.percent
                }
                
                # Disk usage
                disk_data = {}
                for part in self.system_info.get("disk_partitions", []):
                    mountpoint = part["mountpoint"]
                    try:
                        usage = psutil.disk_usage(mountpoint)
                        disk_data[mountpoint] = {
                            "total_gb": usage.total / (1024 ** 3),
                            "used_gb": usage.used / (1024 ** 3),
                            "free_gb": usage.free / (1024 ** 3),
                            "percent": usage.percent
                        }
                    except (PermissionError, FileNotFoundError):
                        pass
                
                # Network I/O
                current_network_io = self._get_network_io()
                network_data = {
                    "bytes_sent": current_network_io["bytes_sent"],
                    "bytes_recv": current_network_io["bytes_recv"],
                    "bytes_sent_per_sec": (current_network_io["bytes_sent"] - last_network_io["bytes_sent"]) / elapsed,
                    "bytes_recv_per_sec": (current_network_io["bytes_recv"] - last_network_io["bytes_recv"]) / elapsed,
                }
                last_network_io = current_network_io
                last_time = current_time
                
                # Add metrics to history
                timestamp = time.time()
                
                self.metrics_history["cpu"].append({
                    "timestamp": timestamp,
                    "total_percent": cpu_percent,
                    "per_cpu_percent": per_cpu_percent
                })
                
                self.metrics_history["memory"].append({
                    "timestamp": timestamp,
                    "data": memory_data
                })
                
                self.metrics_history["disk"].append({
                    "timestamp": timestamp,
                    "data": disk_data
                })
                
                self.metrics_history["network"].append({
                    "timestamp": timestamp,
                    "data": network_data
                })
                
                # Trim history if needed
                for key in self.metrics_history:
                    if len(self.metrics_history[key]) > self.max_history_points:
                        self.metrics_history[key] = self.metrics_history[key][-self.max_history_points:]
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {str(e)}")
    
    def _get_network_io(self) -> Dict[str, int]:
        """
        Get current network I/O counters.
        
        Returns:
            Dict with bytes_sent and bytes_recv.
        """
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        }
    
    def get_basic_metrics(self) -> Dict[str, Any]:
        """
        Get current basic metrics (CPU, memory, disk).
        
        Returns:
            Dict containing current metrics.
        """
        try:
            metrics = {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
            
            # Add Docker metrics if Docker is running
            try:
                import docker
                client = docker.from_env()
                containers = client.containers.list()
                
                metrics["docker"] = {
                    "running_containers": len(containers),
                    "container_info": []
                }
                
                for container in containers[:5]:  # Limit to 5 containers for performance
                    stats = container.stats(stream=False)
                    metrics["docker"]["container_info"].append({
                        "id": container.short_id,
                        "name": container.name,
                        "status": container.status
                    })
            except:
                metrics["docker"] = {"status": "unavailable"}
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting basic metrics: {str(e)}")
            return {"error": str(e)}
    
    def get_full_system_info(self) -> Dict[str, Any]:
        """
        Get full system information.
        
        Returns:
            Dict containing system info.
        """
        if not self.system_info:
            self._collect_system_info()
        
        return self.system_info
    
    def get_metrics_history(self, 
                           metric_type: Optional[str] = None,
                           limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get metrics history.
        
        Args:
            metric_type: Type of metric to get (cpu, memory, disk, network). If None, get all.
            limit: Maximum number of history points to return.
            
        Returns:
            Dict containing metrics history.
        """
        if not self.running:
            self.start_metrics_collection()
        
        if metric_type:
            if metric_type in self.metrics_history:
                return {
                    metric_type: self.metrics_history[metric_type][-limit:]
                }
            else:
                return {}
        
        # Return all metrics types, limited by count
        result = {}
        for k, v in self.metrics_history.items():
            result[k] = v[-limit:]
        
        return result
    
    def get_resource_recommendations(self) -> Dict[str, Any]:
        """
        Get resource recommendations based on current system state.
        
        Returns:
            Dict with recommendations.
        """
        if not self.metrics_history["cpu"] or not self.metrics_history["memory"]:
            return {"message": "Not enough metrics collected to make recommendations."}
        
        # Get average metrics from the last 10 readings
        cpu_readings = self.metrics_history["cpu"][-10:]
        memory_readings = self.metrics_history["memory"][-10:]
        
        avg_cpu = sum(cr["total_percent"] for cr in cpu_readings) / len(cpu_readings)
        avg_memory_percent = sum(mr["data"]["percent"] for mr in memory_readings) / len(memory_readings)
        
        recommendations = {
            "current_avg_cpu_percent": avg_cpu,
            "current_avg_memory_percent": avg_memory_percent,
            "recommendations": []
        }
        
        # CPU recommendations
        if avg_cpu > 85:
            recommendations["recommendations"].append({
                "priority": "high",
                "resource": "cpu",
                "message": "CPU usage is very high. Consider optimizing CPU-intensive operations or scaling to a system with more CPU resources."
            })
        elif avg_cpu > 70:
            recommendations["recommendations"].append({
                "priority": "medium",
                "resource": "cpu",
                "message": "CPU usage is elevated. Monitor for potential performance impacts."
            })
        
        # Memory recommendations
        if avg_memory_percent > 85:
            recommendations["recommendations"].append({
                "priority": "high",
                "resource": "memory",
                "message": "Memory usage is very high. Consider adding more memory, reducing batch sizes, or optimizing memory-intensive operations."
            })
        elif avg_memory_percent > 70:
            recommendations["recommendations"].append({
                "priority": "medium",
                "resource": "memory",
                "message": "Memory usage is elevated. Monitor for potential performance impacts."
            })
        
        # Disk recommendations
        for part_data in self.metrics_history["disk"][-1]["data"].values():
            if part_data["percent"] > 90:
                recommendations["recommendations"].append({
                    "priority": "high",
                    "resource": "disk",
                    "message": f"Disk usage is very high ({part_data['percent']}%). Clear unused files or add more storage."
                })
                break  # Just report one high disk alert
        
        return recommendations
