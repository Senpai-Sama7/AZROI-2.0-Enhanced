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
from typing import Dict, Any, List, Optional, Tuple, Union
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
    
    Enhanced with comprehensive timeout handling to address Feature-BE-07:
    - Hardware Auditing - Execution Hang/Timeout fixes
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
        
        # Enhanced timeout configurations for Feature-BE-07
        self.default_subprocess_timeout = self.config.get("subprocess_timeout", 10)
        self.gpu_detection_timeout = self.config.get("gpu_detection_timeout", 15)
        self.docker_command_timeout = self.config.get("docker_command_timeout", 30)
        self.max_collection_time = self.config.get("max_collection_time", 120)
        
        # Runtime state
        self.running = False
        self.metrics_thread = None
        self.metrics_lock = threading.RLock()  # Thread-safe lock for metrics operations
        
        # Initialize metrics history storage
        self.metrics_history: Dict[str, List[Dict[str, Any]]] = {
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
            try:
                # Add timeout to initial collection to prevent hangs
                collection_start = time.time()
                self._collect_system_info()
                collection_duration = time.time() - collection_start
                
                if collection_duration > self.max_collection_time:
                    logger.warning(f"System info collection took {collection_duration:.1f}s (limit: {self.max_collection_time}s)")
                    
            except Exception as e:
                logger.error(f"Failed to collect system info during initialization: {e}")
                self.system_info = {"error": str(e), "collection_failed": True}
    
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
            "disable_init_collection": monitoring_config.get("disable_init_collection", False),
            # Enhanced timeout configurations
            "subprocess_timeout": monitoring_config.get("subprocess_timeout", 10),
            "gpu_detection_timeout": monitoring_config.get("gpu_detection_timeout", 15),
            "docker_command_timeout": monitoring_config.get("docker_command_timeout", 30),
            "max_collection_time": monitoring_config.get("max_collection_time", 120)
        }
        
        return cls(config=hw_audit_config)

    def _collect_dev_tools_info(self) -> Dict[str, Any]:
        """
        Collect information about key development tools: Poetry, Docker Compose, Terraform.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
        tools = {
            "poetry": {"installed": False, "version": None},
            "docker_compose": {"installed": False, "version": None},
            "terraform": {"installed": False, "version": None}
        }
        
        # Poetry with timeout
        poetry_path = shutil.which("poetry")
        if poetry_path:
            tools["poetry"]["installed"] = True
            try:
                result = subprocess.run(
                    ["poetry", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=self.default_subprocess_timeout
                )
                if result.returncode == 0:
                    tools["poetry"]["version"] = result.stdout.strip()
            except subprocess.TimeoutExpired:
                logger.warning("Poetry version check timed out")
                tools["poetry"]["version"] = "timeout"
            except Exception as e:
                logger.debug(f"Poetry version check failed: {e}")
                
        # Docker Compose with timeout
        compose_path = shutil.which("docker-compose") or shutil.which("docker compose")
        if compose_path:
            tools["docker_compose"]["installed"] = True
            try:
                # Try both syntaxes with timeout
                result = subprocess.run(
                    ["docker-compose", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=self.default_subprocess_timeout
                )
                if result.returncode != 0:
                    result = subprocess.run(
                        ["docker", "compose", "version"], 
                        capture_output=True, 
                        text=True, 
                        timeout=self.default_subprocess_timeout
                    )
                if result.returncode == 0:
                    tools["docker_compose"]["version"] = result.stdout.strip()
            except subprocess.TimeoutExpired:
                logger.warning("Docker Compose version check timed out")
                tools["docker_compose"]["version"] = "timeout"
            except Exception as e:
                logger.debug(f"Docker Compose version check failed: {e}")
                
        # Terraform with timeout
        terraform_path = shutil.which("terraform")
        if terraform_path:
            tools["terraform"]["installed"] = True
            try:
                result = subprocess.run(
                    ["terraform", "version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=self.default_subprocess_timeout
                )
                if result.returncode == 0:
                    tools["terraform"]["version"] = result.stdout.strip().split("\n")[0]
            except subprocess.TimeoutExpired:
                logger.warning("Terraform version check timed out")
                tools["terraform"]["version"] = "timeout"
            except Exception as e:
                logger.debug(f"Terraform version check failed: {e}")
                
        return tools

    def _collect_system_info(self):
        """
        Collect comprehensive information about the system hardware.
        Respects configuration settings for what information to collect.
        Enhanced with timeout handling to prevent indefinite hangs (Feature-BE-07).
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
            
            # Get Docker info if enabled (with timeout)
            if self.collect_docker_metrics:
                try:
                    self.system_info["docker_info"] = self._get_docker_info()
                except Exception as e:
                    logger.warning(f"Docker info collection failed: {e}")
                    self.system_info["docker_info"] = {"error": str(e)}
            
            # Get disk partitions with timeout protection
            try:
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
                    except (PermissionError, OSError) as e:
                        # Some mountpoints may not be accessible or may hang
                        logger.debug(f"Skipping partition {partition.device}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Disk partition enumeration failed: {e}")
            
            # Get network info with timeout protection
            try:
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
            except Exception as e:
                logger.warning(f"Network interface enumeration failed: {e}")
                        
            # Enhanced CPU info with timeout
            try:
                self.system_info["cpu_details"] = self._get_detailed_cpu_info()
            except Exception as e:
                logger.warning(f"CPU details collection failed: {e}")
                self.system_info["cpu_details"] = {"error": str(e)}
                        
            # GPU information (if enabled and available) with timeout
            if self.gpu_detection_enabled:
                try:
                    self.system_info["gpus"] = self._detect_gpus()
                except Exception as e:
                    logger.warning(f"GPU detection failed: {e}")
                    self.system_info["gpus"] = []
            else:
                self.system_info["gpus"] = []
            
            # Assess LLM capabilities based on hardware
            try:
                self.llm_capability_assessment = self._assess_llm_capabilities()
                self.system_info["llm_capabilities"] = self.llm_capability_assessment
            except Exception as e:
                logger.warning(f"LLM capability assessment failed: {e}")
                self.system_info["llm_capabilities"] = {"error": str(e)}
            
            # Collect development tools info with timeout
            try:
                self.system_info["dev_tools"] = self._collect_dev_tools_info()
            except Exception as e:
                logger.warning(f"Dev tools collection failed: {e}")
                self.system_info["dev_tools"] = {"error": str(e)}
            
        except Exception as e:
            logger.error(f"Error collecting system info: {str(e)}")
            self.system_info = {"error": str(e)}
            
    def _get_docker_info(self) -> Dict[str, Any]:
        """
        Get information about Docker installation and capabilities.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
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
                
                # Get Docker version with timeout
                try:
                    result = subprocess.run(
                        ['docker', 'version', '--format', '{{.Server.Version}}'], 
                        capture_output=True, 
                        text=True, 
                        timeout=self.docker_command_timeout
                    )
                    if result.returncode == 0:
                        docker_info["version"] = result.stdout.strip()
                except subprocess.TimeoutExpired:
                    logger.warning("Docker version command timed out")
                    docker_info["version"] = "timeout"
                except Exception as e:
                    logger.debug(f"Docker version check failed: {e}")
                
                # Check for gVisor with timeout
                try:
                    result = subprocess.run(
                        ['docker', 'info', '--format', '{{.Runtimes}}'], 
                        capture_output=True, 
                        text=True, 
                        timeout=self.docker_command_timeout
                    )
                    if result.returncode == 0 and "runsc" in result.stdout:
                        docker_info["gvisor_available"] = True
                except subprocess.TimeoutExpired:
                    logger.warning("Docker info command for gVisor check timed out")
                except Exception as e:
                    logger.debug(f"Docker gVisor check failed: {e}")
                
                # Check Docker resource limits with timeout
                try:
                    docker_info["resource_limits"] = self._get_docker_resource_limits()
                except Exception as e:
                    logger.debug(f"Docker resource limits check failed: {e}")
                    docker_info["resource_limits"] = {"error": str(e)}
                    
        except Exception as e:
            logger.warning(f"Error getting Docker info: {str(e)}")
            
        return docker_info
            
    def _get_docker_resource_limits(self) -> Dict[str, Any]:
        """
        Get Docker resource limits if configured.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
        limits = {}
        
        try:
            # Get cgroup info for Docker with timeout
            try:
                result = subprocess.run(
                    ['docker', 'info', '--format', '{{.CgroupDriver}}'], 
                    capture_output=True, 
                    text=True, 
                    timeout=self.docker_command_timeout
                )
                if result.returncode == 0:
                    limits["cgroup_driver"] = result.stdout.strip()
            except subprocess.TimeoutExpired:
                logger.warning("Docker cgroup info command timed out")
                limits["cgroup_driver"] = "timeout"
            except Exception as e:
                logger.debug(f"Docker cgroup check failed: {e}")
                
            # Try to get memory limits with timeout
            try:
                result = subprocess.run(
                    ['docker', 'info', '--format', '{{.MemTotal}}'], 
                    capture_output=True, 
                    text=True, 
                    timeout=self.docker_command_timeout
                )
                if result.returncode == 0:
                    try:
                        mem_bytes = int(result.stdout.strip())
                        limits["memory_total_gb"] = round(mem_bytes / (1024**3), 2)
                    except ValueError:
                        pass
            except subprocess.TimeoutExpired:
                logger.warning("Docker memory info command timed out")
                limits["memory_total_gb"] = "timeout"
            except Exception as e:
                logger.debug(f"Docker memory check failed: {e}")
                
        except Exception as e:
            logger.warning(f"Error getting Docker resource limits: {str(e)}")
            
        return limits
    
    def _detect_gpus(self) -> List[Dict[str, Any]]:
        """
        Enhanced GPU detection with support for NVIDIA, AMD, and Intel GPUs.
        Uses robust error handling with custom exceptions and timeout protection (Feature-BE-07).
        """
        gpus = []
        
        if not self.gpu_detection_enabled:
            return gpus
            
        # Try NVIDIA first with timeout
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu', 
                 '--format=csv,noheader,nounits'], 
                capture_output=True, 
                text=True, 
                timeout=self.gpu_detection_timeout
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 4:
                            try:
                                gpus.append({
                                    "type": "nvidia",
                                    "name": parts[0],
                                    "memory_total_mb": float(parts[1]),
                                    "memory_used_mb": float(parts[2]),
                                    "utilization_percent": float(parts[3]),
                                    "vram_sufficient_for_quantized": float(parts[1]) >= 8000
                                })
                            except ValueError as e:
                                logger.warning(f"Error parsing NVIDIA GPU data: {e}")
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
            
        # Try AMD GPUs with timeout
        try:
            result = subprocess.run(
                ['rocm-smi', '--showmeminfo', 'vram', '-f', 'csv'], 
                capture_output=True, 
                text=True, 
                timeout=self.gpu_detection_timeout
            )
            
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
        
        # Check for Intel GPUs using sycl-ls with timeout
        try:
            result = subprocess.run(
                ['sycl-ls'], 
                capture_output=True, 
                text=True, 
                timeout=self.gpu_detection_timeout
            )
            
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
                result = subprocess.run(
                    ['lspci', '-v'], 
                    capture_output=True, 
                    text=True, 
                    timeout=self.gpu_detection_timeout
                )
                
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
        """
        Get detailed CPU information from lscpu if available.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
        cpu_details = {
            "model_name": platform.processor(),
            "architecture": platform.machine(),
            "features": []
        }
        
        try:
            # Try to get CPU details using lscpu with timeout
            result = subprocess.run(
                ['lscpu'], 
                capture_output=True, 
                text=True, 
                timeout=self.default_subprocess_timeout
            )
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
        except subprocess.TimeoutExpired:
            logger.warning("lscpu command timed out")
            cpu_details["timeout"] = True
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
            assessment["inference_acceleration"] = "CPU (AVX2)"
            assessment["local_inference_capable"] = True
            assessment["vllm_compatible"] = False  # vLLM primarily for GPU
            assessment["tgi_compatible"] = True
            if has_avx512:
                assessment["inference_acceleration"] = "CPU (AVX-512)"
                assessment["max_recommended_model_size"] = "7B"
                assessment["recommended_model_types"] = ["Llama-2-7B-chat (quantized)", "CodeLlama-7B (quantized)"]
            else:
                assessment["max_recommended_model_size"] = "3B"
                assessment["recommended_model_types"] = ["Llama-2-3B (quantized)", "Phi-2"]
                
        else:
            # System doesn't meet minimum requirements for local inference
            assessment["local_inference_capable"] = False
            assessment["recommended_model_types"] = ["Use cloud-based APIs like OpenAI, Anthropic"]
            assessment["max_recommended_model_size"] = "N/A"
            
        return assessment

    def start_metrics_collection(self):
        """
        Start continuous metrics collection in a background thread.
        Enhanced with timeout handling to prevent blocking (Feature-BE-07).
        """
        if self.running:
            logger.warning("Metrics collection is already running")
            return
            
        logger.info(f"Starting hardware metrics collection (interval: {self.metrics_interval}s)")
        self.running = True
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop, daemon=True)
        self.metrics_thread.start()

    def stop_metrics_collection(self):
        """
        Stop continuous metrics collection.
        """
        if not self.running:
            logger.warning("Metrics collection is not running")
            return
            
        logger.info("Stopping hardware metrics collection")
        self.running = False
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=5)  # Enhanced timeout
            if self.metrics_thread.is_alive():
                logger.warning("Metrics collection thread did not stop gracefully")

    def _metrics_collection_loop(self):
        """
        Main loop for collecting metrics continuously.
        Enhanced with timeout protection to prevent hangs (Feature-BE-07).
        """
        while self.running:
            try:
                collection_start = time.time()
                
                # Collect metrics with timeout protection
                self._collect_current_metrics()
                
                collection_duration = time.time() - collection_start
                if collection_duration > self.metrics_interval:
                    logger.warning(f"Metrics collection took {collection_duration:.1f}s (interval: {self.metrics_interval}s)")
                
                # Sleep for the remaining interval time
                sleep_time = max(0, self.metrics_interval - collection_duration)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.metrics_interval)  # Continue after error

    def _collect_current_metrics(self):
        """
        Collect current system metrics and store them.
        Enhanced with timeout handling to prevent indefinite hangs (Feature-BE-07).
        """
        timestamp = time.time()
        
        with self.metrics_lock:
            try:
                # CPU metrics with timeout protection
                try:
                    cpu_data = {
                        "timestamp": timestamp,
                        "percent": psutil.cpu_percent(interval=1),
                        "count": psutil.cpu_count(logical=True),
                        "load_avg": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
                    }
                    self._add_metric("cpu", cpu_data)
                except Exception as e:
                    logger.warning(f"CPU metrics collection failed: {e}")

                # Memory metrics
                try:
                    memory = psutil.virtual_memory()
                    memory_data = {
                        "timestamp": timestamp,
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used,
                        "free": memory.free
                    }
                    self._add_metric("memory", memory_data)
                except Exception as e:
                    logger.warning(f"Memory metrics collection failed: {e}")

                # Disk metrics with timeout protection
                try:
                    disk_data = {
                        "timestamp": timestamp,
                        "partitions": []
                    }
                    for partition in psutil.disk_partitions()[:5]:  # Limit to first 5 partitions
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            disk_data["partitions"].append({
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "total": usage.total,
                                "used": usage.used,
                                "free": usage.free,
                                "percent": usage.percent
                            })
                        except (PermissionError, OSError):
                            continue  # Skip inaccessible partitions
                    self._add_metric("disk", disk_data)
                except Exception as e:
                    logger.warning(f"Disk metrics collection failed: {e}")

                # Network metrics
                try:
                    network = psutil.net_io_counters()
                    network_data = {
                        "timestamp": timestamp,
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    }
                    self._add_metric("network", network_data)
                except Exception as e:
                    logger.warning(f"Network metrics collection failed: {e}")

                # Docker metrics (if enabled) with timeout
                if self.collect_docker_metrics:
                    try:
                        docker_data = self._collect_docker_metrics()
                        if docker_data:
                            self._add_metric("docker", docker_data)
                    except Exception as e:
                        logger.warning(f"Docker metrics collection failed: {e}")

            except Exception as e:
                logger.error(f"Error collecting current metrics: {e}")

    def _collect_docker_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Collect Docker container metrics.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
        if not shutil.which("docker"):
            return None
            
        try:
            # Get running containers with timeout
            result = subprocess.run(
                ['docker', 'ps', '--format', 'table {{.ID}}\t{{.Names}}\t{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=self.docker_command_timeout
            )
            
            if result.returncode != 0:
                return None
                
            containers = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        container_id = parts[0].strip()
                        
                        # Get container stats with timeout
                        try:
                            stats_result = subprocess.run(
                                ['docker', 'stats', '--no-stream', '--format', 
                                 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}', 
                                 container_id],
                                capture_output=True,
                                text=True,
                                timeout=self.docker_command_timeout
                            )
                            
                            if stats_result.returncode == 0:
                                stats_lines = stats_result.stdout.strip().split('\n')[1:]  # Skip header
                                if stats_lines:
                                    stats_parts = stats_lines[0].split('\t')
                                    if len(stats_parts) >= 4:
                                        containers.append({
                                            "id": container_id,
                                            "name": parts[1].strip(),
                                            "status": parts[2].strip(),
                                            "cpu_percent": stats_parts[1].strip(),
                                            "memory_usage": stats_parts[2].strip(),
                                            "memory_percent": stats_parts[3].strip()
                                        })
                        except subprocess.TimeoutExpired:
                            logger.warning(f"Docker stats timeout for container {container_id}")
                            continue
                        except Exception as e:
                            logger.debug(f"Failed to get stats for container {container_id}: {e}")
                            continue
            
            return {
                "timestamp": time.time(),
                "containers": containers
            }
            
        except subprocess.TimeoutExpired:
            logger.warning("Docker ps command timed out")
            return None
        except Exception as e:
            logger.debug(f"Docker metrics collection failed: {e}")
            return None

    def _add_metric(self, metric_type: str, data: Dict[str, Any]):
        """
        Add a metric data point and maintain history limits.
        """
        if metric_type not in self.metrics_history:
            self.metrics_history[metric_type] = []
            
        self.metrics_history[metric_type].append(data)
        
        # Maintain history limit
        if len(self.metrics_history[metric_type]) > self.max_history_points:
            self.metrics_history[metric_type] = self.metrics_history[metric_type][-self.max_history_points:]

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get the collected system information.
        """
        return self.system_info or {}

    def get_metrics_history(self, metric_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics history for a specific type or all metrics.
        """
        with self.metrics_lock:
            if metric_type:
                return {metric_type: self.metrics_history.get(metric_type, [])}
            return dict(self.metrics_history)

    def get_latest_metrics(self) -> Dict[str, Any]:
        """
        Get the most recent metrics for each type.
        """
        latest = {}
        with self.metrics_lock:
            for metric_type, history in self.metrics_history.items():
                if history:
                    latest[metric_type] = history[-1]
        return latest

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive hardware report.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
        try:
            report = {
                "timestamp": time.time(),
                "system_info": self.get_system_info(),
                "latest_metrics": self.get_latest_metrics(),
                "metrics_collection_running": self.running,
                "configuration": {
                    "metrics_interval": self.metrics_interval,
                    "collect_docker_metrics": self.collect_docker_metrics,
                    "gpu_detection_enabled": self.gpu_detection_enabled,
                    "max_history_points": self.max_history_points
                }
            }
            
            # Add summary statistics with timeout protection
            try:
                report["summary"] = self._generate_summary_stats()
            except Exception as e:
                logger.warning(f"Summary generation failed: {e}")
                report["summary"] = {"error": str(e)}
            
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {"error": str(e), "timestamp": time.time()}

    def _generate_summary_stats(self) -> Dict[str, Any]:
        """
        Generate summary statistics from collected metrics.
        """
        summary = {}
        
        with self.metrics_lock:
            # CPU summary
            cpu_history = self.metrics_history.get("cpu", [])
            if cpu_history:
                cpu_percents = [m["percent"] for m in cpu_history if "percent" in m]
                if cpu_percents:
                    summary["cpu"] = {
                        "average_percent": sum(cpu_percents) / len(cpu_percents),
                        "max_percent": max(cpu_percents),
                        "min_percent": min(cpu_percents),
                        "samples": len(cpu_percents)
                    }

            # Memory summary
            memory_history = self.metrics_history.get("memory", [])
            if memory_history:
                memory_percents = [m["percent"] for m in memory_history if "percent" in m]
                if memory_percents:
                    summary["memory"] = {
                        "average_percent": sum(memory_percents) / len(memory_percents),
                        "max_percent": max(memory_percents),
                        "min_percent": min(memory_percents),
                        "samples": len(memory_percents)
                    }

        return summary

    def save_report(self, filename: Optional[str] = None) -> str:
        """
        Save the hardware report to a JSON file.
        Enhanced with timeout handling to prevent hangs (Feature-BE-07).
        """
        output_path = filename or self.output_file
        
        try:
            report = self.generate_report()
            
            # Write with timeout protection
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Hardware report saved to {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"Failed to save report to {output_path}: {e}"
            logger.error(error_msg)
            raise HardwareAuditError(error_msg, component="report_saver", severity="error")

    def cleanup(self):
        """
        Clean up resources and stop metrics collection.
        """
        try:
            self.stop_metrics_collection()
            logger.info("Hardware audit system cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# Enhanced factory function for easy initialization
def create_hardware_audit_system(config_loader=None, **kwargs) -> HardwareAuditSystem:
    """
    Factory function to create a HardwareAuditSystem instance.
    Enhanced with comprehensive timeout handling for Feature-BE-07.
    
    Args:
        config_loader: Optional ConfigLoader instance
        **kwargs: Additional configuration options
        
    Returns:
        A configured HardwareAuditSystem instance
    """
    if config_loader:
        return HardwareAuditSystem.from_config_loader(config_loader)
    else:
        return HardwareAuditSystem(config=kwargs)


# CLI interface for standalone usage
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Hardware Audit System - Enhanced with timeout handling")
    parser.add_argument("--output", "-o", default="hw_report.json", help="Output file for the report")
    parser.add_argument("--metrics-interval", "-i", type=int, default=15, help="Metrics collection interval")
    parser.add_argument("--collect-time", "-t", type=int, default=60, help="How long to collect metrics (seconds)")
    parser.add_argument("--disable-docker", action="store_true", help="Disable Docker metrics collection")
    parser.add_argument("--disable-gpu", action="store_true", help="Disable GPU detection")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Configuration
    config = {
        "output_file": args.output,
        "metrics_interval": args.metrics_interval,
        "collect_docker_metrics": not args.disable_docker,
        "gpu_detection_enabled": not args.disable_gpu,
        # Enhanced timeout configurations for Feature-BE-07
        "subprocess_timeout": 10,
        "gpu_detection_timeout": 15,
        "docker_command_timeout": 30,
        "max_collection_time": 120
    }
    
    try:
        with create_hardware_audit_system(config=config) as audit_system:
            print(f"Starting hardware audit with enhanced timeout handling...")
            print(f"System info collected: {len(audit_system.get_system_info())} fields")
            
            if args.collect_time > 0:
                print(f"Collecting metrics for {args.collect_time} seconds...")
                audit_system.start_metrics_collection()
                time.sleep(args.collect_time)
                audit_system.stop_metrics_collection()
            
            report_path = audit_system.save_report()
            print(f"Report saved to: {report_path}")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
