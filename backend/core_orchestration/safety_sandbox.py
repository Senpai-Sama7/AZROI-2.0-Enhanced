#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/core_orchestration/safety_sandbox.py

import os
import json
import logging
import tempfile
import subprocess
import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("ai-architect-backend.safety_sandbox")

class SafetySandbox:
    """
    Safety sandbox for secure code execution.
    Integrates with Open Interpreter and optionally uses gVisor for 
    additional isolation and security.
    """
    
    def __init__(self, 
                use_gvisor: bool = False, 
                isolation_level: str = "high",
                network_enabled: bool = False,
                max_memory_mb: int = 2048,
                cpu_limit: float = 1.0):
        """
        Initialize the safety sandbox.
        
        Args:
            use_gvisor: Whether to use gVisor for sandbox isolation.
            isolation_level: Isolation level (low, medium, high).
            network_enabled: Whether to allow network access from the sandbox.
            max_memory_mb: Maximum memory limit in MB.
            cpu_limit: CPU limit (number of cores).
        """
        self.use_gvisor = use_gvisor
        self.isolation_level = isolation_level
        self.network_enabled = network_enabled
        self.max_memory_mb = max_memory_mb
        self.cpu_limit = cpu_limit
        self.gvisor_available = False
        
        # Check Docker availability
        self.docker_available = self._check_docker()
        
        # Store Open Interpreter configuration
        self.interpreter_config = {
            "auto_run": True,
            "safe_mode": "auto" if isolation_level != "low" else "off",
        }
        
        if isolation_level == "high":
            # In high isolation, we use Docker containers with additional constraints
            self.interpreter_config["docker"] = True
            
            # If gVisor is requested, we'll check and configure it
            if use_gvisor:
                self.gvisor_available = self._check_gvisor()
                if not self.gvisor_available:
                    logger.warning("gVisor was requested but is not available. Falling back to standard Docker isolation.")
    
    async def initialize(self):
        """
        Initialize the sandbox system.
        Checks requirements and configures the environment.
        """
        logger.info(f"Initializing safety sandbox (isolation_level={self.isolation_level}, gvisor={self.use_gvisor})")
        
        # Verify Docker is working
        if not self.docker_available:
            logger.warning("Docker is not available. Sandbox capabilities will be limited.")
            self.isolation_level = "low"
            self.use_gvisor = False
            return
        
        # Set up gVisor if requested and available
        if self.use_gvisor and self.gvisor_available:
            await self._setup_gvisor()
            logger.info("gVisor sandbox environment set up successfully")
        
        logger.info(f"Sandbox initialized with isolation level: {self.isolation_level}")
    
    def _check_docker(self) -> bool:
        """
        Check if Docker is available.
        
        Returns:
            True if Docker is available, False otherwise.
        """
        try:
            result = subprocess.run(
                ["docker", "info"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Docker check failed: {str(e)}")
            return False
    
    def _check_gvisor(self) -> bool:
        """
        Check if gVisor is available.
        
        Returns:
            True if gVisor is available, False otherwise.
        """
        try:
            # Check if runsc binary is available
            runsc_check = subprocess.run(
                ["which", "runsc"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=False
            )
            
            if runsc_check.returncode != 0:
                return False
            
            # Check if gVisor runtime is registered with Docker
            docker_info = subprocess.run(
                ["docker", "info", "--format", "{{json .}}"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=False,
                text=True
            )
            
            if docker_info.returncode != 0:
                return False
            
            # Parse Docker info JSON to check for gVisor/runsc runtime
            info = json.loads(docker_info.stdout)
            runtimes = info.get("Runtimes", {})
            
            return "runsc" in runtimes
            
        except Exception as e:
            logger.warning(f"gVisor check failed: {str(e)}")
            return False
    
    async def _setup_gvisor(self):
        """
        Set up gVisor if it's not already installed.
        """
        if self.gvisor_available:
            return
        
        logger.info("Setting up gVisor...")
        
        try:
            # Only attempt to install on Linux
            if os.name != "posix":
                logger.warning("gVisor installation is only supported on Linux")
                return
            
            # Attempt to install gVisor
            install_script = """
            # Download and install gVisor
            curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
            sudo apt-get update
            sudo apt-get install -y runsc
            
            # Configure Docker to use gVisor/runsc
            sudo mkdir -p /etc/docker
            if [ ! -f /etc/docker/daemon.json ]; then
                echo '{"runtimes": {"runsc": {"path": "/usr/bin/runsc"}}}' | sudo tee /etc/docker/daemon.json
            else
                # Add runsc to existing daemon.json
                TMP_FILE=$(mktemp)
                sudo cat /etc/docker/daemon.json | jq '. + {"runtimes": (if .runtimes then .runtimes else {} end) + {"runsc": {"path": "/usr/bin/runsc"}}}' > $TMP_FILE
                sudo mv $TMP_FILE /etc/docker/daemon.json
            fi
            
            # Restart Docker
            sudo systemctl restart docker
            """
            
            # This would require sudo privileges, which is typically not available
            # in a running service. In practice, gVisor should be installed and
            # configured by a system administrator or via infrastructure provisioning.
            logger.warning("Automatic gVisor installation skipped - requires administrative privileges")
            logger.warning("Please install gVisor manually following instructions at https://gvisor.dev/docs/user_guide/install/")
            
            # Instead, we'll just check again to see if it's already available
            self.gvisor_available = self._check_gvisor()
            
        except Exception as e:
            logger.error(f"Error setting up gVisor: {str(e)}")
            self.gvisor_available = False
    
    def get_interpreter_config(self) -> Dict[str, Any]:
        """
        Get the configuration for Open Interpreter based on safety settings.
        
        Returns:
            Dict of Open Interpreter configuration settings.
        """
        config = self.interpreter_config.copy()
        
        # Apply Docker settings if using high isolation
        if self.isolation_level == "high" and self.docker_available:
            docker_args = []
            
            # Apply memory limit
            docker_args.append(f"--memory={self.max_memory_mb}m")
            
            # Apply CPU limit
            docker_args.append(f"--cpus={self.cpu_limit}")
            
            # Network settings
            if not self.network_enabled:
                docker_args.append("--network=none")
            
            # Use gVisor if available
            if self.use_gvisor and self.gvisor_available:
                docker_args.append("--runtime=runsc")
            
            # Add storage limits
            docker_args.append("--storage-opt=size=10G")
            
            # Set security options
            docker_args.append("--security-opt=no-new-privileges")
            
            # Apply Docker arguments
            config["docker_args"] = " ".join(docker_args)
        
        return config
    
    async def run_in_sandbox(self, 
                            code: str, 
                            language: str, 
                            working_dir: Optional[str] = None,
                            timeout: int = 60) -> Dict[str, Any]:
        """
        Run code in the sandbox.
        
        Args:
            code: The code to run.
            language: The language of the code.
            working_dir: Working directory for code execution.
            timeout: Timeout in seconds.
            
        Returns:
            Dict with the execution results.
        """
        if not working_dir:
            working_dir = tempfile.mkdtemp(prefix="ai-architect-sandbox-")
        
        try:
            # Write code to a file
            file_ext = self._get_file_extension(language)
            code_file = os.path.join(working_dir, f"code{file_ext}")
            
            with open(code_file, "w") as f:
                f.write(code)
            
            # Prepare the command based on language and isolation level
            if self.isolation_level == "high" and self.docker_available:
                cmd, env = self._prepare_docker_command(code_file, language, working_dir)
            else:
                cmd, env = self._prepare_local_command(code_file, language, working_dir)
            
            # Run the command with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=working_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "output": "",
                    "error": f"Execution timed out after {timeout} seconds",
                    "exit_code": -1
                }
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8", errors="replace"),
                "error": stderr.decode("utf-8", errors="replace"),
                "exit_code": process.returncode
            }
            
        except Exception as e:
            logger.error(f"Error in sandbox execution: {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }
        finally:
            # Clean up if using a temporary directory
            if working_dir.startswith(tempfile.gettempdir()):
                try:
                    shutil.rmtree(working_dir)
                except Exception as e:
                    logger.warning(f"Failed to clean up sandbox directory: {str(e)}")
    
    def _get_file_extension(self, language: str) -> str:
        """
        Get the file extension for a language.
        
        Args:
            language: Programming language.
            
        Returns:
            File extension including the dot.
        """
        extensions = {
            "python": ".py",
            "python3": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "bash": ".sh",
            "shell": ".sh",
            "sh": ".sh",
            "ruby": ".rb",
            "rb": ".rb",
            "go": ".go",
            "golang": ".go",
            "java": ".java",
            "c": ".c",
            "cpp": ".cpp",
            "c++": ".cpp",
            "csharp": ".cs",
            "cs": ".cs",
            "php": ".php",
            "rust": ".rs",
            "rs": ".rs",
        }
        
        return extensions.get(language.lower(), f".{language}")
    
    def _prepare_docker_command(self, 
                              code_file: str, 
                              language: str, 
                              working_dir: str) -> tuple:
        """
        Prepare a Docker command for running code.
        
        Args:
            code_file: Path to the code file.
            language: Programming language.
            working_dir: Working directory.
            
        Returns:
            Tuple of (command_list, environment_dict).
        """
        filename = os.path.basename(code_file)
        
        # Select the appropriate Docker image and command based on language
        if language.lower() in ["python", "python3", "py"]:
            image = "python:3.11-slim"
            docker_cmd = f"python /{filename}"
        elif language.lower() in ["javascript", "js"]:
            image = "node:16-slim"
            docker_cmd = f"node /{filename}"
        elif language.lower() in ["typescript", "ts"]:
            image = "node:16-slim"
            docker_cmd = f"npx ts-node /{filename}"
        elif language.lower() in ["bash", "shell", "sh"]:
            image = "alpine:latest"
            docker_cmd = f"sh /{filename}"
        else:
            # Default to a basic Linux environment
            image = "ubuntu:latest"
            docker_cmd = f"cat /{filename}"  # Just output the file since we don't know how to run it
        
        # Prepare Docker arguments
        docker_args = [
            "run",
            "--rm",  # Remove container after execution
            "-v", f"{os.path.abspath(working_dir)}:/workspace",  # Mount the working directory
            "-w", "/workspace",  # Set working directory in container
        ]
        
        # Add any safety constraints
        if not self.network_enabled:
            docker_args.append("--network=none")
            
        docker_args.append(f"--memory={self.max_memory_mb}m")
        docker_args.append(f"--cpus={self.cpu_limit}")
        
        # Use gVisor if available
        if self.use_gvisor and self.gvisor_available:
            docker_args.append("--runtime=runsc")
        
        # Add security options
        docker_args.append("--security-opt=no-new-privileges")
        
        # Add the image and command
        docker_args.extend([image, "sh", "-c", docker_cmd])
        
        # Final command is "docker" followed by all the arguments
        cmd = ["docker"] + docker_args
        
        # Environment variables
        env = os.environ.copy()
        
        return cmd, env
    
    def _prepare_local_command(self, 
                             code_file: str, 
                             language: str, 
                             working_dir: str) -> tuple:
        """
        Prepare a local command for running code (less secure).
        
        Args:
            code_file: Path to the code file.
            language: Programming language.
            working_dir: Working directory.
            
        Returns:
            Tuple of (command_list, environment_dict).
        """
        # Select the appropriate command based on language
        if language.lower() in ["python", "python3", "py"]:
            cmd = ["python", code_file]
        elif language.lower() in ["javascript", "js"]:
            cmd = ["node", code_file]
        elif language.lower() in ["typescript", "ts"]:
            cmd = ["npx", "ts-node", code_file]
        elif language.lower() in ["bash", "shell", "sh"]:
            cmd = ["sh", code_file]
        else:
            # Default to just trying to execute the file
            cmd = [code_file]
        
        # Environment variables
        env = os.environ.copy()
        
        # Safety measure to restrict Python
        if language.lower() in ["python", "python3", "py"]:
            env["PYTHONPATH"] = working_dir  # Only allow imports from working dir
            
        return cmd, env
    
    def prepare_interpreter_for_task(self, 
                                   task_id: str, 
                                   output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare Open Interpreter configuration for a specific task.
        
        Args:
            task_id: Task ID.
            output_dir: Directory for outputs.
            
        Returns:
            Dict with Open Interpreter configuration.
        """
        # Start with base configuration
        config = self.get_interpreter_config()
        
        # Set output directory
        if output_dir:
            config["local_file_output_base_path"] = output_dir
        
        # Allow configuring Open Interpreter based on task
        config["task_id"] = task_id
        
        return config
