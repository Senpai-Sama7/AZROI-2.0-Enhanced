#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/core_orchestration/hardware_audit.py

import os
import platform
import socket
import json
import logging
import psutil
import time
import shutil
import subprocess
from typing import Dict, Any, List, Optional, Tuple
import threading
import importlib.util

logger = logging.getLogger("ai-architect-backend.hardware_audit")

class HardwareAuditError(Exception):
    """
    Custom exception class for hardware audit related errors.
    Provides additional context for debugging and error handling.
    """
    def __init__(self, message: str, component: Optional[str] = None, severity: str = "error"):
        """
        Initialize with enhanced error information.
        
        Args:
            message: The error message.
            component: The component where the error occurred.
            severity: The severity level of the error (e.g., "warning", "error", "critical").
        """
        self.component = component or "hardware_audit"
        self.severity = severity
        self.timestamp = time.time()
        
        # Format the message for logging
        full_message = f"[{self.component}] {message}"
        super().__init__(full_message)
        
        # Log the error based on severity
        if severity == "warning":
            logger.warning(full_message)
        elif severity == "critical":
            logger.critical(full_message)
        else:
            logger.error(full_message)

class HardwareAuditSystem:
    """
    Enhanced system for auditing hardware resources and monitoring system performance.
    This is critical for ensuring system stability and preventing resource exhaustion.
    Also determines optimal LLM execution environment based on hardware capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, metrics_interval: int = 15, output_file: str = "hw_report.json"):
        """
        Initialize the hardware audit system with runtime configurability.
        
        Args:
            config: Configuration dictionary that overrides default settings.
            metrics_interval: Interval in seconds for collecting metrics (used if not in config).
            output_file: Path to output the hardware report JSON file (used if not in config).
        """
        # Load config or use provided config
        self.config = config or {}
        
        # Set parameters from config with fallback to arguments
        self.metrics_interval = self.config.get("metrics_interval", metrics_interval)
        self.output_file = self.config.get("output_file", output_file)
        self.max_history_points = self.config.get("max_history_points", 1000)
        self.collect_docker_metrics = self.config.get("collect_docker_metrics", True)
        self.gpu_detection_enabled = self.config.get("gpu_detection_enabled", True)
        
        # Runtime state
        self.running = False
        self.metrics_thread = None
        self.metrics_lock = threading.RLock()  # Thread-safe lock for metrics operations
        
        # Initialize metrics history storage
        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": [],
            "docker": []
        }
        
        # System information and assessment results
        self.system_info = None
        self.llm_capability_assessment = None
        
        # Collect system info on initialization unless disabled
        if not self.config.get("disable_init_collection", False):
            self._collect_system_info()
    
    @classmethod
    def from_config_loader(cls, config_loader):
        """
        Create a HardwareAuditSystem instance using a ConfigLoader.
        
        Args:
            config_loader: A ConfigLoader instance to retrieve configuration from.
            
        Returns:
            A configured HardwareAuditSystem instance.
        """
        # Get monitoring configuration
        monitoring_config = config_loader.get_value("monitoring_config", {})
        if not isinstance(monitoring_config, dict):
            monitoring_config = {}
            
        # Initialize with proper configuration
        hw_audit_config = {
            "metrics_interval": monitoring_config.get("metrics_interval", 15),
            "output_file": monitoring_config.get("hw_report_path", "hw_report.json"),
            "max_history_points": monitoring_config.get("max_history_points", 1000),
            "collect_docker_metrics": monitoring_config.get("collect_docker_metrics", True),
            "gpu_detection_enabled": monitoring_config.get("gpu_detection_enabled", True),
            "disable_init_collection": monitoring_config.get("disable_init_collection", False)
        }
        
        return cls(config=hw_audit_config)

    def _collect_dev_tools_info(self) -> Dict[str, Any]:
        """
        Collect information about key development tools: Poetry, Docker Compose, Terraform.
        """
        tools = {
            "poetry": {"installed": False, "version": None},
            "docker_compose": {"installed": False, "version": None},
            "terraform": {"installed": False, "version": None}
        }
        # Poetry
        poetry_path = shutil.which("poetry")
        if poetry_path:
            tools["poetry"]["installed"] = True
            try:
                result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    tools["poetry"]["version"] = result.stdout.strip()
            except Exception:
                pass
        # Docker Compose
        compose_path = shutil.which("docker-compose") or shutil.which("docker compose")
        if compose_path:
            tools["docker_compose"]["installed"] = True
            try:
                # Try both syntaxes
                result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
                if result.returncode != 0:
                    result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
                if result.returncode == 0:
                    tools["docker_compose"]["version"] = result.stdout.strip()
            except Exception:
                pass
        # Terraform
        terraform_path = shutil.which("terraform")
        if terraform_path:
            tools["terraform"]["installed"] = True
            try:
                result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
                if result.returncode == 0:
                    tools["terraform"]["version"] = result.stdout.strip().split("\n")[0]
            except Exception:
                pass
        return tools

    def _collect_system_info(self):
        """
        Collect comprehensive information about the system hardware.
        Respects configuration settings for what information to collect.
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
                "disk_partitions": [],
            }
            
            # Get Docker info if enabled
            if self.collect_docker_metrics:
                self.system_info["docker_info"] = self._get_docker_info()
            
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
                        
            # Enhanced CPU info
            self.system_info["cpu_details"] = self._get_detailed_cpu_info()
                        
            # GPU information (if enabled and available)
            if self.gpu_detection_enabled:
                self.system_info["gpus"] = self._detect_gpus()
            else:
                self.system_info["gpus"] = []
            
            # Assess LLM capabilities based on hardware
            self.llm_capability_assessment = self._assess_llm_capabilities()
            self.system_info["llm_capabilities"] = self.llm_capability_assessment
            
            # Collect development tools info
            self.system_info["dev_tools"] = self._collect_dev_tools_info()
            
        except Exception as e:
            logger.error(f"Error collecting system info: {str(e)}")
            self.system_info = {"error": str(e)}
            
    def _get_docker_info(self) -> Dict[str, Any]:
        """Get information about Docker installation and capabilities."""
        docker_info = {
            "installed": False,
            "version": None,
            "gvisor_available": False,
            "resource_limits": {}
        }
        
        try:
            # Check if Docker is installed
            if shutil.which("docker"):
                docker_info["installed"] = True
                
                # Get Docker version
                result = subprocess.run(['docker', 'version', '--format', '{{.Server.Version}}'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    docker_info["version"] = result.stdout.strip()
                
                # Check for gVisor
                result = subprocess.run(['docker', 'info', '--format', '{{.Runtimes}}'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and "runsc" in result.stdout:
                    docker_info["gvisor_available"] = True
                
                # Check Docker resource limits
                docker_info["resource_limits"] = self._get_docker_resource_limits()
        except Exception as e:
            logger.warning(f"Error getting Docker info: {str(e)}")
            
        return docker_info
            
    def _get_docker_resource_limits(self) -> Dict[str, Any]:
        """Get Docker resource limits if configured."""
        limits = {}
        
        try:
            # Get cgroup info for Docker
            result = subprocess.run(['docker', 'info', '--format', '{{.CgroupDriver}}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                limits["cgroup_driver"] = result.stdout.strip()
                
            # Try to get memory limits
            result = subprocess.run(['docker', 'info', '--format', '{{.MemTotal}}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    mem_bytes = int(result.stdout.strip())
                    limits["memory_total_gb"] = round(mem_bytes / (1024**3), 2)
                except ValueError:
                    pass
        except Exception as e:
            logger.warning(f"Error getting Docker resource limits: {str(e)}")
            
        return limits
    
    def _detect_gpus(self) -> List[Dict[str, Any]]:
        """
        Enhanced GPU detection with support for NVIDIA, AMD, and Intel GPUs.
        Uses robust error handling with custom exceptions.
        """
        gpus = []
        
        if not self.gpu_detection_enabled:
            return gpus
            
        # Try NVIDIA first
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 4:
                            gpus.append({
                                "type": "nvidia",
                                "name": parts[0],
                                "memory_total_mb": float(parts[1]),
                                "memory_used_mb": float(parts[2]),
                                "utilization_percent": float(parts[3]),
                                "vram_sufficient_for_quantized": float(parts[1]) >= 8000
                            })
        except subprocess.TimeoutExpired:
            logger.warning("NVIDIA GPU detection timed out")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"NVIDIA GPU detection failed: {str(e)}")
        except Exception as e:
            raise HardwareAuditError(
                f"Unexpected error during NVIDIA GPU detection: {str(e)}", 
                component="gpu_detector", 
                severity="warning"
            )
            
        # Try AMD GPUs if no NVIDIA GPUs found or even if NVIDIA GPUs were found but detection is enabled
        try:
            result = subprocess.run(['rocm-smi', '--showmeminfo', 'vram', '-f', 'csv'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    for line in lines[1:]:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 3:
                            try:
                                memory_total = float(parts[1]) if len(parts) > 1 else 0
                                memory_used = float(parts[2]) if len(parts) > 2 else 0
                                gpus.append({
                                    "type": "amd",
                                    "name": parts[0] if len(parts) > 0 else "AMD GPU",
                                    "memory_total_mb": memory_total,
                                    "memory_used_mb": memory_used,
                                    "vram_sufficient_for_quantized": memory_total >= 8000
                                })
                            except ValueError as e:
                                logger.warning(f"Error parsing AMD GPU memory values: {str(e)}")
        except subprocess.TimeoutExpired:
            logger.warning("AMD GPU detection timed out")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"AMD GPU detection failed: {str(e)}")
        except Exception as e:
            raise HardwareAuditError(
                f"Unexpected error during AMD GPU detection: {str(e)}", 
                component="gpu_detector", 
                severity="warning"
            )
        
        # Check for Intel GPUs using sycl-ls
        try:
            result = subprocess.run(['sycl-ls'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and "Intel" in result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if "Intel" in line and "GPU" in line:
                        gpu_info = {
                            "type": "intel",
                            "name": line.strip(),
                            "memory_total_mb": "unknown",
                            "memory_used_mb": "unknown",
                            "vram_sufficient_for_quantized": False
                        }
                        # Try to extract memory info if available in the output
                        if "memory" in line.lower() and ":" in line:
                            try:
                                memory_part = line.split("memory", 1)[1].strip()
                                if "MB" in memory_part or "GB" in memory_part:
                                    memory_str = ''.join(c for c in memory_part if c.isdigit() or c == '.')
                                    if memory_str:
                                        memory_val = float(memory_str)
                                        if "GB" in memory_part:
                                            memory_val *= 1024  # Convert GB to MB
                                        gpu_info["memory_total_mb"] = memory_val
                                        gpu_info["vram_sufficient_for_quantized"] = memory_val >= 8000
                            except (ValueError, IndexError) as e:
                                logger.debug(f"Failed to parse Intel GPU memory: {str(e)}")
                        
                        gpus.append(gpu_info)
        except subprocess.TimeoutExpired:
            logger.warning("Intel GPU detection timed out")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Intel GPU detection failed: {str(e)}")
        except Exception as e:
            raise HardwareAuditError(
                f"Unexpected error during Intel GPU detection: {str(e)}", 
                component="gpu_detector", 
                severity="warning"
            )
            
        # Attempt to detect integrated GPUs through lspci if no GPUs found so far
        if not gpus:
            try:
                result = subprocess.run(['lspci', '-v'], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    gpu_markers = ["VGA compatible controller", "Display controller", "3D controller"]
                    gpu_vendors = ["Intel", "AMD", "NVIDIA", "Matrox", "ATI"]
                    
                    lines = result.stdout.split('\n')
                    for i, line in enumerate(lines):
                        if any(marker in line for marker in gpu_markers):
                            # Found a potential GPU
                            name = line
                            for vendor in gpu_vendors:
                                if vendor in line:
                                    vendor_type = vendor.lower()
                                    if vendor == "ATI":
                                        vendor_type = "amd"  # Map ATI to AMD
                                    
                                    gpus.append({
                                        "type": vendor_type,
                                        "name": name.strip(),
                                        "memory_total_mb": "unknown",
                                        "memory_used_mb": "unknown",
                                        "vram_sufficient_for_quantized": False,
                                        "detection_method": "lspci"
                                    })
                                    break
            except subprocess.TimeoutExpired:
                logger.warning("lspci GPU detection timed out")
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.debug(f"lspci GPU detection failed: {str(e)}")
            except Exception as e:
                logger.warning(f"Unexpected error during lspci GPU detection: {str(e)}")
            
        return gpus

    def _get_detailed_cpu_info(self) -> Dict[str, Any]:
        """Get detailed CPU information from lscpu if available."""
        cpu_details = {
            "model_name": platform.processor(),
            "architecture": platform.machine(),
            "features": []
        }
        
        try:
            # Try to get CPU details using lscpu
            result = subprocess.run(['lscpu'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ":" in line:
                        key, value = [x.strip() for x in line.split(':', 1)]
                        if key == "Model name":
                            cpu_details["model_name"] = value
                        elif key == "Architecture":
                            cpu_details["architecture"] = value
                        elif key == "Flags" or key == "CPU Flags":
                            cpu_details["features"] = [f.strip() for f in value.split()]
                            # Check for AVX, AVX2, AVX-512 which are important for LLM inference
                            cpu_details["has_avx"] = "avx" in cpu_details["features"]
                            cpu_details["has_avx2"] = "avx2" in cpu_details["features"]
                            cpu_details["has_avx512f"] = "avx512f" in cpu_details["features"]
        except Exception as e:
            logger.warning(f"Error getting detailed CPU info: {str(e)}")
            
        return cpu_details
        
    def _assess_llm_capabilities(self) -> Dict[str, Any]:
        """
        Assess LLM capabilities based on hardware specifications.
        """
        assessment = {
            "local_inference_capable": False,
            "recommended_model_types": [],
            "max_recommended_model_size": "None",
            "inference_acceleration": "None",
            "vllm_compatible": False,
            "tgi_compatible": False,
            "ollama_compatible": True,  # Ollama works on most systems
            "docker_isolation_level": "basic"
        }
        # Defensive: ensure self.system_info is a dict
        sysinfo = self.system_info if isinstance(self.system_info, dict) else {}
        # Check if there's enough RAM for meaningful LLM inference
        total_mem = sysinfo.get("total_memory_gb", 0)
        try:
            has_sufficient_ram = float(total_mem) >= 16
        except Exception:
            has_sufficient_ram = False
        # Check for GPUs
        gpus = sysinfo.get("gpus", [])
        if not isinstance(gpus, list):
            gpus = []
        def safe_gpu_get(gpu, key, default=None):
            return gpu.get(key, default) if isinstance(gpu, dict) else default
        has_nvidia_gpu = any(safe_gpu_get(gpu, "type") == "nvidia" for gpu in gpus)
        has_large_vram_gpu = any(safe_gpu_get(gpu, "vram_sufficient_for_quantized", False) for gpu in gpus)
        # Check for modern CPU features
        cpu_details = sysinfo.get("cpu_details", {})
        if not isinstance(cpu_details, dict):
            cpu_details = {}
        has_avx2 = cpu_details.get("has_avx2", False)
        has_avx512 = cpu_details.get("has_avx512f", False)
        # Docker capabilities
        docker_info = sysinfo.get("docker_info", {})
        if not isinstance(docker_info, dict):
            docker_info = {}
        has_gvisor = docker_info.get("gvisor_available", False)
        # Set recommended isolation level
        if has_gvisor:
            assessment["docker_isolation_level"] = "gvisor"
        elif docker_info.get("installed", False):
            assessment["docker_isolation_level"] = "seccomp"
        # Determine LLM capabilities
        if has_nvidia_gpu:
            assessment["inference_acceleration"] = "CUDA"
            assessment["local_inference_capable"] = True
            assessment["vllm_compatible"] = True
            assessment["tgi_compatible"] = True
            if has_large_vram_gpu:
                assessment["max_recommended_model_size"] = "13B"
                assessment["recommended_model_types"] = ["Llama-2-13B-chat", "CodeLlama-13B", "Mixtral-8x7B (quantized)"]
            else:
                assessment["max_recommended_model_size"] = "7B"
                assessment["recommended_model_types"] = ["Llama-2-7B-chat", "CodeLlama-7B", "Mistral-7B"]
        elif has_sufficient_ram and has_avx2:
            assessment["local_inference_capable"] = True
            assessment["inference_acceleration"] = "CPU+AVX2"
            if has_avx512:
                assessment["inference_acceleration"] += "+AVX512"
            assessment["max_recommended_model_size"] = "7B"
            assessment["recommended_model_types"] = ["Llama-2-7B-chat-Q4_K_M", "Mistral-7B-Q4_K_M"]
            # Check CPU core count for vLLM capability without GPU
            try:
                physical_cpus = int(sysinfo.get("physical_cpu_count", 0))
            except Exception:
                physical_cpus = 0
            if physical_cpus >= 8 and has_avx512:
                assessment["vllm_compatible"] = True
        return assessment
            
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive hardware report.
        """
        if not self.system_info:
            self._collect_system_info()
            
        report = {
            "system_info": self.system_info,
            "llm_capability_assessment": self.llm_capability_assessment,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "recommended_configuration": self._generate_recommendations()
        }
        
        # Save to file
        try:
            with open(self.output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Hardware report saved to {self.output_file}")
        except Exception as e:
            logger.error(f"Error saving hardware report: {str(e)}")
            
        return report
        
    def _generate_recommendations(self) -> Dict[str, Any]:
        """
        Generate system-specific recommendations based on hardware assessment.
        """
        recommendations = {
            "llm_hosting": "cloud",  # Default to cloud if local capabilities are insufficient
            "recommended_models": [],
            "isolation_recommendations": {
                "recommended_sandbox": "basic_docker",
                "gvisor_setup_needed": False
            },
            "optimization_suggestions": []
        }
        sysinfo = self.system_info if isinstance(self.system_info, dict) else {}
        llm_capabilities = self.llm_capability_assessment or {}
        # LLM Hosting recommendation
        if llm_capabilities.get("local_inference_capable", False):
            if llm_capabilities.get("vllm_compatible", False):
                recommendations["llm_hosting"] = "local_vllm"
                recommendations["optimization_suggestions"].append(
                    "Configure vLLM with GPU acceleration for optimal performance"
                )
            else:
                recommendations["llm_hosting"] = "local_llama_cpp"
                recommendations["optimization_suggestions"].append(
                    "Use quantized models with llama.cpp for memory efficiency"
                )
            # Add recommended models
            recommendations["recommended_models"] = llm_capabilities.get("recommended_model_types", [])
        else:
            recommendations["optimization_suggestions"].append(
                "Use cloud-based LLM APIs for better performance on this hardware"
            )
        # Isolation recommendations
        docker_info = sysinfo.get("docker_info", {})
        if not isinstance(docker_info, dict):
            docker_info = {}
        isolation_level = llm_capabilities.get("docker_isolation_level", "basic")
        if isolation_level == "gvisor":
            recommendations["isolation_recommendations"]["recommended_sandbox"] = "gvisor"
            recommendations["optimization_suggestions"].append(
                "Leverage existing gVisor installation for enhanced security isolation"
            )
        elif docker_info.get("installed", False):
            if isolation_level == "basic":
                recommendations["isolation_recommendations"]["recommended_sandbox"] = "seccomp_docker"
                recommendations["isolation_recommendations"]["gvisor_setup_needed"] = True
                recommendations["optimization_suggestions"].append(
                    "Install gVisor for improved code execution isolation security"
                )
        # Add hardware-specific optimization suggestions
        gpus = sysinfo.get("gpus", [])
        if not isinstance(gpus, list):
            gpus = []
        if gpus:
            first_gpu = gpus[0] if isinstance(gpus[0], dict) else {}
            gpu_type = first_gpu.get('type', 'GPU')
            recommendations["optimization_suggestions"].append(
                f"Configure container runtime to use {gpu_type} acceleration for LLM inference"
            )
        # Memory recommendations
        total_memory = sysinfo.get("total_memory_gb", 0)
        try:
            total_memory_val = float(total_memory)
        except Exception:
            total_memory_val = 0
        if total_memory_val < 16:
            recommendations["optimization_suggestions"].append(
                "Consider increasing system RAM to at least 16GB for better performance with local LLMs"
            )
        return recommendations

    def start_metrics_collection(self):
        """
        Start collecting metrics in a background thread.
        """
        if self.running:
            return
            
        self.running = True
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()
        logger.info("Started hardware metrics collection")
        
    def stop_metrics_collection(self):
        """
        Stop collecting metrics.
        """
        self.running = False
        if self.metrics_thread:
            self.metrics_thread.join(timeout=2)
            logger.info("Stopped hardware metrics collection")
            
    def _metrics_collection_loop(self):
        """
        Continuous metrics collection loop that runs in a background thread.
        Collects system metrics at regular intervals and maintains a rolling history.
        Implements proper error handling to ensure robustness.
        """
        metrics_lock = threading.RLock()  # Use RLock for thread-safe operations
        anomaly_check_interval = max(5, self.metrics_interval * 2)  # Check for anomalies every few intervals
        last_anomaly_check = time.time()
        
        while self.running:
            try:
                # Collect current metrics
                current_metrics = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_io": self._get_disk_io_metrics(),
                    "network_io": self._get_network_io_metrics(),
                    "docker_stats": self._get_docker_container_stats()
                }
                
                # Thread-safe update of metrics history
                with metrics_lock:
                    # Update CPU metrics
                    self.metrics_history["cpu"].append({
                        "timestamp": current_metrics["timestamp"],
                        "percent": current_metrics["cpu_percent"]
                    })
                    # Trim to max history length
                    if len(self.metrics_history["cpu"]) > self.max_history_points:
                        self.metrics_history["cpu"] = self.metrics_history["cpu"][-self.max_history_points:]
                    
                    # Update memory metrics
                    self.metrics_history["memory"].append({
                        "timestamp": current_metrics["timestamp"],
                        "percent": current_metrics["memory_percent"]
                    })
                    if len(self.metrics_history["memory"]) > self.max_history_points:
                        self.metrics_history["memory"] = self.metrics_history["memory"][-self.max_history_points:]
                    
                    # Update disk metrics
                    self.metrics_history["disk"].append(current_metrics["disk_io"])
                    if len(self.metrics_history["disk"]) > self.max_history_points:
                        self.metrics_history["disk"] = self.metrics_history["disk"][-self.max_history_points:]
                    
                    # Update network metrics
                    self.metrics_history["network"].append(current_metrics["network_io"])
                    if len(self.metrics_history["network"]) > self.max_history_points:
                        self.metrics_history["network"] = self.metrics_history["network"][-self.max_history_points:]
                    
                    # Update docker metrics if available
                    if current_metrics["docker_stats"]:
                        self.metrics_history["docker"].append(current_metrics["docker_stats"])
                        if len(self.metrics_history["docker"]) > self.max_history_points:
                            self.metrics_history["docker"] = self.metrics_history["docker"][-self.max_history_points:]
                
                # Log high CPU or memory usage as a warning
                if current_metrics["cpu_percent"] > 90:
                    logger.warning(f"High CPU usage detected: {current_metrics['cpu_percent']}%")
                if current_metrics["memory_percent"] > 90:
                    logger.warning(f"High memory usage detected: {current_metrics['memory_percent']}%")
                
                # Periodically check for resource anomalies
                current_time = time.time()
                if current_time - last_anomaly_check >= anomaly_check_interval:
                    anomalies = self.detect_anomalies()
                    if anomalies["detected"]:
                        logger.warning("Resource anomalies detected:")
                        for anomaly in anomalies["resource_pressure"]:
                            logger.warning(f"  - {anomaly['resource'].upper()} pressure ({anomaly['severity']}): {anomaly['current']}% > {anomaly['threshold']}%")
                        for anomaly in anomalies["bottlenecks"]:
                            logger.warning(f"  - Bottleneck ({anomaly['severity']}): {anomaly['details']}")
                        for recommendation in anomalies["recommendations"]:
                            logger.warning(f"  - Recommendation: {recommendation}")
                    last_anomaly_check = current_time
                
                # Sleep for the configured interval
                time.sleep(self.metrics_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {str(e)}")
                # Don't crash the thread, continue after a short delay
                time.sleep(5)
    
    def _get_disk_io_metrics(self) -> Dict[str, Any]:
        """Get disk I/O metrics for all disks."""
        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
            disk_metrics = {
                "timestamp": time.time(),
                "disks": {}
            }
            
            if io_counters:
                for disk, counters in io_counters.items():
                    disk_metrics["disks"][disk] = {
                        "read_bytes": counters.read_bytes,
                        "write_bytes": counters.write_bytes,
                        "read_count": counters.read_count,
                        "write_count": counters.write_count
                    }
            return disk_metrics
        except Exception as e:
            logger.debug(f"Error getting disk I/O metrics: {str(e)}")
            return {"timestamp": time.time(), "disks": {}, "error": str(e)}
    
    def _get_network_io_metrics(self) -> Dict[str, Any]:
        """Get network I/O metrics for all interfaces."""
        try:
            io_counters = psutil.net_io_counters(pernic=True)
            net_metrics = {
                "timestamp": time.time(),
                "interfaces": {}
            }
            
            if io_counters:
                for interface, counters in io_counters.items():
                    net_metrics["interfaces"][interface] = {
                        "bytes_sent": counters.bytes_sent,
                        "bytes_recv": counters.bytes_recv,
                        "packets_sent": counters.packets_sent,
                        "packets_recv": counters.packets_recv
                    }
            return net_metrics
        except Exception as e:
            logger.debug(f"Error getting network I/O metrics: {str(e)}")
            return {"timestamp": time.time(), "interfaces": {}, "error": str(e)}
    
    def _get_docker_container_stats(self) -> Optional[Dict[str, Any]]:
        """Get resource usage statistics for running Docker containers."""
        if not shutil.which("docker"):
            return None
            
        try:
            result = subprocess.run(["docker", "stats", "--no-stream", "--format", 
                                   "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}}"],
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return None
                
            container_stats = {
                "timestamp": time.time(),
                "containers": {}
            }
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 6:
                    name = parts[0]
                    container_stats["containers"][name] = {
                        "cpu_percent": parts[1].rstrip('%'),
                        "mem_usage": parts[2],
                        "mem_percent": parts[3].rstrip('%'),
                        "net_io": parts[4],
                        "block_io": parts[5]
                    }
                    
            return container_stats
        except Exception as e:
            logger.debug(f"Error getting Docker container stats: {str(e)}")
            return None

    def serialize_metrics_history(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Serialize the metrics history to a JSON file for persistence and reporting.
        
        Args:
            output_file: Optional path to output JSON file. If None, uses a default path.
            
        Returns:
            Dict containing the serialized metrics history.
        """
        if output_file is None:
            # Generate default filename with timestamp if none provided
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_file = f"metrics_history_{timestamp}.json"
            
        # Create a deep copy of metrics with thread safety
        with self.metrics_lock:
            metrics_copy = {
                "timestamp": time.time(),
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "metrics_history": {
                    "cpu": self.metrics_history["cpu"].copy(),
                    "memory": self.metrics_history["memory"].copy(),
                    "disk": self.metrics_history["disk"].copy(),
                    "network": self.metrics_history["network"].copy(),
                    "docker": self.metrics_history["docker"].copy()
                },
                "system_info": self.system_info
            }
            
        # Calculate summary statistics
        metrics_copy["summary"] = self._calculate_metrics_summary(metrics_copy["metrics_history"])
        
        # Save to file if provided
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(metrics_copy, f, indent=2)
                logger.info(f"Metrics history saved to {output_file}")
            except Exception as e:
                raise HardwareAuditError(f"Error saving metrics history: {str(e)}", 
                                       component="metrics_serialization")
                
        return metrics_copy
    
    def _calculate_metrics_summary(self, metrics_history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate summary statistics for metrics history.
        
        Args:
            metrics_history: Dict containing metrics history.
            
        Returns:
            Dict containing summary statistics.
        """
        summary = {
            "cpu": {
                "max": 0.0,
                "min": 100.0,
                "avg": 0.0,
                "last": 0.0,
                "samples": 0
            },
            "memory": {
                "max": 0.0,
                "min": 100.0,
                "avg": 0.0,
                "last": 0.0,
                "samples": 0
            }
        }
        
        # CPU statistics
        if metrics_history.get("cpu"):
            cpu_values = [float(entry.get("percent", 0)) for entry in metrics_history["cpu"] 
                          if isinstance(entry, dict) and "percent" in entry]
            if cpu_values:
                summary["cpu"]["max"] = max(cpu_values)
                summary["cpu"]["min"] = min(cpu_values)
                summary["cpu"]["avg"] = sum(cpu_values) / len(cpu_values)
                summary["cpu"]["last"] = cpu_values[-1] if cpu_values else 0.0
                summary["cpu"]["samples"] = len(cpu_values)
                
        # Memory statistics
        if metrics_history.get("memory"):
            mem_values = [float(entry.get("percent", 0)) for entry in metrics_history["memory"] 
                          if isinstance(entry, dict) and "percent" in entry]
            if mem_values:
                summary["memory"]["max"] = max(mem_values)
                summary["memory"]["min"] = min(mem_values)
                summary["memory"]["avg"] = sum(mem_values) / len(mem_values)
                summary["memory"]["last"] = mem_values[-1] if mem_values else 0.0
                summary["memory"]["samples"] = len(mem_values)
                
        return summary

    def detect_anomalies(self) -> Dict[str, Any]:
        """
        Analyze metrics history to detect resource anomalies and potential bottlenecks.
        
        Returns:
            Dict containing detected anomalies and recommendations.
        """
        anomalies = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detected": False,
            "resource_pressure": [],
            "bottlenecks": [],
            "recommendations": []
        }
        
        # Ensure we have enough data points
        with self.metrics_lock:
            cpu_metrics = self.metrics_history.get("cpu", [])
            memory_metrics = self.metrics_history.get("memory", [])
            disk_metrics = self.metrics_history.get("disk", [])
            
            if len(cpu_metrics) < 3 or len(memory_metrics) < 3:
                return anomalies
            
            # Calculate recent CPU trends
            recent_cpu = [m.get("percent", 0) for m in cpu_metrics[-10:] if isinstance(m, dict)]
            if recent_cpu and len(recent_cpu) >= 3:
                avg_cpu = sum(recent_cpu) / len(recent_cpu)
                max_cpu = max(recent_cpu)
                
                # Detect high CPU usage
                if max_cpu > 90:
                    anomalies["detected"] = True
                    anomalies["resource_pressure"].append({
                        "resource": "cpu",
                        "severity": "critical",
                        "current": max_cpu,
                        "threshold": 90
                    })
                    anomalies["recommendations"].append(
                        "High CPU usage detected. Consider limiting concurrent tasks or increasing CPU resources."
                    )
                elif avg_cpu > 70:
                    anomalies["detected"] = True
                    anomalies["resource_pressure"].append({
                        "resource": "cpu",
                        "severity": "warning",
                        "current": avg_cpu,
                        "threshold": 70
                    })
                    anomalies["recommendations"].append(
                        "Sustained high CPU usage. Optimize CPU-intensive operations or scale resources."
                    )
                
                # Detect CPU trend
                if len(recent_cpu) >= 5:
                    # Simple trend detection - increasing values
                    is_increasing = all(recent_cpu[i] <= recent_cpu[i+1] for i in range(len(recent_cpu)-5, len(recent_cpu)-1))
                    if is_increasing and recent_cpu[-1] > 50:
                        anomalies["detected"] = True
                        anomalies["bottlenecks"].append({
                            "resource": "cpu",
                            "severity": "warning",
                            "details": "CPU usage is on an increasing trend"
                        })
            
            # Check memory trends
            recent_memory = [m.get("percent", 0) for m in memory_metrics[-10:] if isinstance(m, dict)]
            if recent_memory and len(recent_memory) >= 3:
                avg_memory = sum(recent_memory) / len(recent_memory)
                max_memory = max(recent_memory)
                
                # Detect high memory usage
                if max_memory > 90:
                    anomalies["detected"] = True
                    anomalies["resource_pressure"].append({
                        "resource": "memory",
                        "severity": "critical",
                        "current": max_memory,
                        "threshold": 90
                    })
                    anomalies["recommendations"].append(
                        "Critical memory pressure detected. Risk of OOM errors. Reduce memory usage or increase capacity."
                    )
                elif avg_memory > 80:
                    anomalies["detected"] = True
                    anomalies["resource_pressure"].append({
                        "resource": "memory",
                        "severity": "warning",
                        "current": avg_memory,
                        "threshold": 80
                    })
                    anomalies["recommendations"].append(
                        "High memory usage. Consider optimizing memory-intensive operations."
                    )
                
                # Memory leak detection - consistent increase over time
                if len(recent_memory) >= 5:
                    is_steadily_increasing = all(recent_memory[i] < recent_memory[i+1] for i in range(len(recent_memory)-5, len(recent_memory)-1))
                    if is_steadily_increasing:
                        anomalies["detected"] = True
                        anomalies["bottlenecks"].append({
                            "resource": "memory",
                            "severity": "warning",
                            "details": "Memory usage is consistently increasing, possible memory leak"
                        })
                        anomalies["recommendations"].append(
                            "Potential memory leak detected. Investigate long-running processes and object lifecycles."
                        )
        
        return anomalies

# CLI Entrypoint
if __name__ == "__main__":
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Hardware Audit System CLI")
    parser.add_argument("--output", type=str, default="hw_report.json", help="Output JSON file for hardware report")
    parser.add_argument("--config", type=str, help="Path to config.json file")
    parser.add_argument("--interval", type=int, default=15, help="Metrics collection interval in seconds")
    parser.add_argument("--summary", action="store_true", help="Print summary to console")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU detection")
    parser.add_argument("--no-docker", action="store_true", help="Disable Docker metrics collection")
    parser.add_argument("--collect", action="store_true", help="Start metrics collection for the specified duration")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds to collect metrics when --collect is used")
    parser.add_argument("--export-metrics", type=str, help="Export metrics history to the specified file")
    args = parser.parse_args()

    # Determine if we should use config loader or direct initialization
    if args.config:
        # Try to import ConfigLoader
        try:
            # Get the directory of this script
            current_dir = Path(__file__).parent
            # Add parent directory to path to import ConfigLoader
            import sys
            sys.path.append(str(current_dir.parent))
            
            from core_orchestration.config_loader import ConfigLoader
            config_loader = ConfigLoader(config_path=args.config)
            audit = HardwareAuditSystem.from_config_loader(config_loader)
            logger.info(f"Using configuration from {args.config}")
        except (ImportError, Exception) as e:
            logger.warning(f"Error loading config: {str(e)}. Using direct initialization.")
            # Fall back to direct initialization if config_loader fails
            audit = HardwareAuditSystem(
                config={
                    "metrics_interval": args.interval,
                    "output_file": args.output,
                    "gpu_detection_enabled": not args.no_gpu,
                    "collect_docker_metrics": not args.no_docker
                }
            )
    else:
        # Direct initialization with CLI args
        audit = HardwareAuditSystem(
            config={
                "metrics_interval": args.interval,
                "output_file": args.output,
                "gpu_detection_enabled": not args.no_gpu,
                "collect_docker_metrics": not args.no_docker
            }
        )
    
    # Start metrics collection if requested
    if args.collect:
        print(f"Starting metrics collection for {args.duration} seconds...")
        audit.start_metrics_collection()
        # Sleep for the requested duration
        try:
            import time
            time.sleep(args.duration)
        except KeyboardInterrupt:
            print("Metrics collection interrupted by user.")
        finally:
            audit.stop_metrics_collection()
            print("Metrics collection stopped.")
            
            # Export metrics if requested
            if args.export_metrics:
                audit.serialize_metrics_history(args.export_metrics)
                print(f"Metrics exported to {args.export_metrics}")
    elif args.export_metrics:
        print("Error: --export-metrics requires --collect to be specified.")
        sys.exit(1)
    
    # Generate the report
    report = audit.generate_report()
    
    # Print summary if requested
    if args.summary:
        print("\n===== HARDWARE AUDIT SUMMARY =====")
        sysinfo = report.get('system_info', {}) if isinstance(report.get('system_info', {}), dict) else {}
        rec_conf = report.get('recommended_configuration', {}) if isinstance(report.get('recommended_configuration', {}), dict) else {}
        iso = rec_conf.get('isolation_recommendations', {}) if isinstance(rec_conf.get('isolation_recommendations', {}), dict) else {}

        print(f"Hostname:               {sysinfo.get('hostname', 'N/A')}")
        print(f"Platform:               {sysinfo.get('platform', 'N/A')}")
        print(f"CPU:                    {sysinfo.get('cpu_details', {}).get('model_name', 'N/A')}")
        print(f"Physical CPUs:          {sysinfo.get('physical_cpu_count', 'N/A')}")
        print(f"Total RAM:              {sysinfo.get('total_memory_gb', 'N/A')} GB")
        print(f"GPUs:                   {len(sysinfo.get('gpus', []))}")
        
        # Show GPU details if available
        gpus = sysinfo.get('gpus', [])
        if gpus:
            print("\nGPU Information:")
            for i, gpu in enumerate(gpus):
                if isinstance(gpu, dict):
                    print(f"  GPU {i+1}: {gpu.get('name', 'Unknown')} ({gpu.get('type', 'unknown')})")
                    
                    # Show memory info if available
                    mem_total = gpu.get('memory_total_mb')
                    if mem_total not in (None, "unknown"):
                        print(f"    Memory: {mem_total} MB")
                        
                    # Show if suitable for quantized models
                    if gpu.get('vram_sufficient_for_quantized'):
                        print(f"    Suitable for LLM inference: Yes")
                    else:
                        print(f"    Suitable for LLM inference: Limited or No")
        
        print(f"\nDocker:                 {sysinfo.get('docker_info', {}).get('version', 'N/A')}")
        print(f"Poetry:                 {sysinfo.get('dev_tools', {}).get('poetry', {}).get('version', 'N/A')}")
        print(f"Docker Compose:         {sysinfo.get('dev_tools', {}).get('docker_compose', {}).get('version', 'N/A')}")
        print(f"Terraform:              {sysinfo.get('dev_tools', {}).get('terraform', {}).get('version', 'N/A')}")
        
        # LLM recommendations section
        print("\nLLM Deployment Recommendations:")
        print(f"LLM Hosting Recommendation: {rec_conf.get('llm_hosting', 'N/A')}")
        print(f"Recommended Models:     {', '.join(rec_conf.get('recommended_models', ['N/A']))}")
        print(f"Sandbox Recommendation: {iso.get('recommended_sandbox', 'N/A')}")
        
        # Performance Optimization Suggestions
        print("\nOptimization Suggestions:")
        for suggestion in rec_conf.get('optimization_suggestions', []):
            print(f"  - {suggestion}")
        
        print("==================================\n")

# Example agent_config.yaml snippet (for documentation only, not executable code)
# This is for reference/documentation and should not be uncommented in Python files.
# agents:
#   planner:
#     model: "gemini-1.0-pro"
#     max_tokens: 4096
#     temperature: 0.2
#     tools:
#       - plan_decomposition
#       - goal_refinement
