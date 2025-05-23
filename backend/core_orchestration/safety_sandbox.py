#!/usr/bin/env python3
"""
Safety Sandbox for secure task execution and validation
"""

import logging
import asyncio
import os
import tempfile
import shutil
import subprocess
import json
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import hashlib
import uuid

logger = logging.getLogger(__name__)

class SafetySandbox:
    """Secure sandbox for task validation and execution"""
    
    def __init__(self, 
                 sandbox_dir: Optional[str] = None,
                 max_execution_time: float = 300.0,
                 max_memory_mb: int = 512,
                 allowed_commands: Optional[List[str]] = None):
        self.sandbox_dir = sandbox_dir or tempfile.mkdtemp(prefix="safety_sandbox_")
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.allowed_commands = allowed_commands or ['python', 'pip', 'git', 'curl', 'wget']
        
        # Security settings
        self.dangerous_patterns = [
            'rm -rf', 'sudo', 'chmod 777', 'mkfs', 'fdisk',
            'eval(', 'exec(', '__import__', 'subprocess.call',
            'os.system', 'shell=True'
        ]
        
        # Task validation cache
        self._validation_cache = {}
        
        logger.info(f"SafetySandbox initialized at {self.sandbox_dir}")
    
    async def validate_task(self, task) -> bool:
        """Validate task safety"""
        try:
            # Quick validation cache check
            task_hash = self._get_task_hash(task)
            if task_hash in self._validation_cache:
                return self._validation_cache[task_hash]
            
            # Validate task content
            is_safe = await self._validate_task_content(task)
            
            # Cache result
            self._validation_cache[task_hash] = is_safe
            
            return is_safe
            
        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            return False
    
    def _get_task_hash(self, task) -> str:
        """Generate hash for task validation caching"""
        task_content = f"{task.name}_{task.description}_{str(task.metadata)}"
        return hashlib.md5(task_content.encode()).hexdigest()
    
    async def _validate_task_content(self, task) -> bool:
        """Validate task content for safety"""
        # Check task description for dangerous patterns
        content = f"{task.description} {str(task.metadata)}"
        
        for pattern in self.dangerous_patterns:
            if pattern.lower() in content.lower():
                logger.warning(f"Dangerous pattern detected in task {task.id}: {pattern}")
                return False
        
        # Additional metadata validation
        if task.metadata:
            if task.metadata.get('requires_root', False):
                logger.warning(f"Task {task.id} requires root access - denied")
                return False
            
            if task.metadata.get('network_access', False):
                # Could add network access validation here
                pass
        
        return True
    
    async def execute_in_sandbox(self, command: List[str], 
                                cwd: Optional[str] = None,
                                env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute command in sandbox with safety constraints"""
        try:
            # Validate command
            if not self._is_command_allowed(command):
                raise ValueError(f"Command not allowed: {command[0]}")
            
            # Prepare execution environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # Set working directory
            work_dir = cwd or self.sandbox_dir
            
            # Execute with timeout and constraints
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=work_dir,
                env=exec_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024  # 1MB buffer limit
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.max_execution_time
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {self.max_execution_time}s")
            
            execution_time = time.time() - start_time
            
            return {
                'returncode': process.returncode,
                'stdout': stdout.decode('utf-8', errors='ignore'),
                'stderr': stderr.decode('utf-8', errors='ignore'),
                'execution_time': execution_time,
                'success': process.returncode == 0
            }
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'execution_time': 0,
                'success': False
            }
    
    def _is_command_allowed(self, command: List[str]) -> bool:
        """Check if command is in allowed list"""
        if not command:
            return False
        
        cmd_name = command[0].split('/')[-1]  # Get base command name
        return cmd_name in self.allowed_commands
    
    def create_temp_file(self, content: str, suffix: str = '.tmp') -> str:
        """Create temporary file in sandbox"""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            dir=self.sandbox_dir,
            delete=False
        )
        
        with temp_file:
            temp_file.write(content)
        
        return temp_file.name
    
    def cleanup_temp_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path) and file_path.startswith(self.sandbox_dir):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def get_sandbox_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics"""
        try:
            # Get directory size
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(self.sandbox_dir)
                for filename in filenames
            )
            
            # Count files
            file_count = sum(
                len(filenames)
                for dirpath, dirnames, filenames in os.walk(self.sandbox_dir)
            )
            
            return {
                'sandbox_dir': self.sandbox_dir,
                'total_size_bytes': total_size,
                'file_count': file_count,
                'validation_cache_size': len(self._validation_cache),
                'max_execution_time': self.max_execution_time,
                'max_memory_mb': self.max_memory_mb
            }
            
        except Exception as e:
            logger.error(f"Failed to get sandbox stats: {e}")
            return {'error': str(e)}
    
    def cleanup(self):
        """Clean up sandbox directory"""
        try:
            if os.path.exists(self.sandbox_dir):
                shutil.rmtree(self.sandbox_dir)
            logger.info(f"Sandbox cleaned up: {self.sandbox_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup()
        except:
            pass
