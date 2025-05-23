#!/usr/bin/env python3
"""
Enhanced Config Loader with comprehensive configuration management
"""

import logging
import json
import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Enhanced configuration loader with validation and dynamic updates"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: Dict[str, Any] = {}
        self._default_config = self._get_default_config()
        
        logger.info(f"ConfigLoader initialized with config file: {config_file}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "default_llm_model_backend": "mock",
            "default_llm_provider": "mock",
            "log_level": "INFO",
            "max_concurrent_agents": 5,
            "planner_agent_prompt_template": "Create an optimal execution plan for: {goal}",
            "code_execution_timeout_seconds": 300,
            "default_generated_app_port": 8501,
            "cloud_build_timeout_seconds": 1800,
            
            # LLM Provider configurations
            "llm_providers": {
                "mock": {
                    "type": "mock",
                    "priority": 1,
                    "weight": 1.0,
                    "max_requests_per_minute": 1000,
                    "config": {}
                },
                "local": {
                    "type": "local",
                    "priority": 2,
                    "weight": 0.8,
                    "max_requests_per_minute": 100,
                    "config": {
                        "endpoint": "http://localhost:11434",
                        "model": "llama2"
                    }
                }
            },
            
            # Agent configurations
            "agents": {
                "max_retry_attempts": 3,
                "default_timeout": 30,
                "health_check_interval": 60
            },
            
            # Open Interpreter configuration
            "open_interpreter_config": {
                "auto_run": False,
                "safe_mode": True,
                "local": True,
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 2000
            },
            
            # GCP configuration defaults
            "gcp_config_defaults": {
                "project_id": "",
                "region": "us-central1",
                "zone": "us-central1-a",
                "machine_type": "e2-medium",
                "disk_size_gb": 20
            },
            
            # ChromaDB configuration
            "chroma_db_config": {
                "host": "localhost",
                "port": 8000,
                "collection_name": "architect_memory",
                "persist_directory": "./chroma_db"
            },
            
            # Monitoring configuration
            "monitoring": {
                "enable_metrics": True,
                "metrics_port": 9090,
                "health_check_interval": 30,
                "log_retention_days": 7
            },
            
            # Security configuration
            "security": {
                "enable_auth": False,
                "api_key_required": False,
                "cors_origins": ["http://localhost:3000", "http://localhost:8501"],
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 100
                }
            }
        }
    
    async def load_config(self):
        """Load configuration from file with fallback to defaults"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                
                # Merge with defaults
                self._config = self._merge_configs(self._default_config, file_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                self._config = self._default_config.copy()
                logger.info("Using default configuration")
            
            # Validate configuration
            await self._validate_config()
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = self._default_config.copy()
    
    async def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.copy()
    
    async def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration with new values"""
        try:
            # Apply updates
            updated_config = self._merge_configs(self._config, updates)
            
            # Validate updated configuration
            old_config = self._config.copy()
            self._config = updated_config
            
            try:
                await self._validate_config()
            except Exception as e:
                # Rollback on validation failure
                self._config = old_config
                raise ValueError(f"Configuration validation failed: {e}")
            
            # Save to file
            await self._save_config()
            
            logger.info("Configuration updated successfully")
            return self._config.copy()
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            raise
    
    async def _validate_config(self):
        """Validate configuration values"""
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self._config.get("log_level") not in valid_log_levels:
            raise ValueError(f"Invalid log_level. Must be one of: {valid_log_levels}")
        
        # Validate numeric ranges
        if not (1 <= self._config.get("max_concurrent_agents", 5) <= 10):
            raise ValueError("max_concurrent_agents must be between 1 and 10")
        
        if not (1 <= self._config.get("code_execution_timeout_seconds", 300) <= 3600):
            raise ValueError("code_execution_timeout_seconds must be between 1 and 3600")
        
        if not (1000 <= self._config.get("default_generated_app_port", 8501) <= 65535):
            raise ValueError("default_generated_app_port must be between 1000 and 65535")
        
        # Validate LLM providers
        if not isinstance(self._config.get("llm_providers"), dict):
            raise ValueError("llm_providers must be a dictionary")
        
        logger.debug("Configuration validation passed")
    
    def _merge_configs(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def _save_config(self):
        """Save current configuration to file"""
        try:
            # Create backup of existing config
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.json.backup')
                self.config_file.replace(backup_file)
            
            # Write new configuration
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2, sort_keys=True)
            
            logger.debug(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM-specific configuration"""
        return {
            "providers": self._config.get("llm_providers", {}),
            "default_provider": self._config.get("default_llm_provider", "mock"),
            "default_model": self._config.get("default_llm_model_backend", "mock")
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent-specific configuration"""
        return self._config.get("agents", {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self._config.get("monitoring", {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self._config.get("security", {})
    
    async def reload_config(self):
        """Reload configuration from file"""
        await self.load_config()
        logger.info("Configuration reloaded")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            "config_file": str(self.config_file),
            "config_exists": self.config_file.exists(),
            "llm_providers": list(self._config.get("llm_providers", {}).keys()),
            "default_provider": self._config.get("default_llm_provider"),
            "max_concurrent_agents": self._config.get("max_concurrent_agents"),
            "log_level": self._config.get("log_level")
        }