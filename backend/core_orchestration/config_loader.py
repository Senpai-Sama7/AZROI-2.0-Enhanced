#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/core_orchestration/config_loader.py

import json
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger("ai-architect-backend.config")

class ConfigLoader:
    """
    Configuration loader that combines JSON config and environment variables.
    Environment variables take precedence over JSON config.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the config loader.
        
        Args:
            config_path: Path to the config.json file. If None, uses default path.
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "config.json"
        )
        
        # Load environment variables from .env file
        load_dotenv()
        
        self.base_config = {}
        self.env_config = {}
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from config.json and override with environment variables.
        
        Returns:
            Dict containing the merged configuration.
        """
        # Load base config from JSON
        try:
            with open(self.config_path, "r") as f:
                self.base_config = json.load(f)
            logger.info(f"Loaded base configuration from {self.config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {self.config_path}: {str(e)}")
            self.base_config = {}
            
        # Get environment variables that match config keys
        self._load_env_config()
        
        # Merge configs, with env taking precedence
        merged_config = self._merge_configs()
        
        # Add additional vector storage config
        if "chroma_db_config" in merged_config:
            # Transition from ChromaDB to Qdrant for vector storage
            merged_config["vector_storage_config"] = {
                "collection_name": merged_config["chroma_db_config"].get("collection_name", "ai_architect_memory"),
                "path": merged_config["chroma_db_config"].get("path", "./backend/vectorstore_data"),
                "url": os.environ.get("QDRANT_URL", None),  # Can be set via env for remote Qdrant
            }
        
        # Add Redis config
        merged_config["redis_config"] = {
            "url": os.environ.get("REDIS_URL", "redis://localhost:6379"),
            "ttl": int(os.environ.get("REDIS_CACHE_TTL", "3600")),  # Default 1 hour TTL
        }
        
        # Add monitoring config
        merged_config["monitoring_config"] = {
            "prometheus_port": int(os.environ.get("METRICS_PORT", "8002")),
            "collect_hardware_metrics": os.environ.get("COLLECT_HARDWARE_METRICS", "true").lower() == "true",
            "metrics_interval": int(os.environ.get("METRICS_INTERVAL", "15")),  # seconds
        }
        
        # Add sandbox config
        merged_config["sandbox_config"] = {
            "use_gvisor": os.environ.get("USE_GVISOR_SANDBOX", "false").lower() == "true",
            "isolation_level": os.environ.get("SANDBOX_ISOLATION_LEVEL", "high"),
            "max_memory_mb": int(os.environ.get("SANDBOX_MAX_MEMORY_MB", "2048")),
            "cpu_limit": float(os.environ.get("SANDBOX_CPU_LIMIT", "1.0")),
            "network_enabled": os.environ.get("SANDBOX_NETWORK_ENABLED", "false").lower() == "true",
        }
        
        return merged_config
    
    def _load_env_config(self):
        """
        Load configuration from environment variables.
        Maps environment variables to config keys.
        """
        env_mapping = {
            # Map of environment variable name to config key path
            "BACKEND_GEMINI_API_KEY": "gemini_api_key",
            "DEFAULT_LLM_MODEL": "default_llm_model_backend",
            "LOG_LEVEL": "log_level",
            "MAX_CONCURRENT_AGENTS": "max_concurrent_agents",
            "CODE_EXECUTION_TIMEOUT_SECONDS": "code_execution_timeout_seconds",
            "OUTPUT_BASE_PATH_CODE_EXECUTIONS": "output_base_path_code_executions",
            "DEFAULT_GENERATED_APP_PORT": "default_generated_app_port",
            "CLOUD_BUILD_TIMEOUT_SECONDS": "cloud_build_timeout_seconds",
            
            # GCP config mapping
            "GCP_PROJECT_ID": ["gcp_config_defaults", "project_id"],
            "GCP_REGION": ["gcp_config_defaults", "region"],
            "GCS_BUCKET_NAME": ["gcp_config_defaults", "gcs_bucket_name"],
            "ARTIFACT_REGISTRY_DOCKER_REPO": ["gcp_config_defaults", "artifact_registry_repository"],
            "ARTIFACT_REGISTRY_REGION_FALLBACK": ["gcp_config_defaults", "artifact_registry_region_fallback"],
            "CLOUD_RUN_SERVICE_NAME_PREFIX": ["gcp_config_defaults", "cloud_run_service_prefix"],
            "CLOUD_RUN_ALLOW_UNAUTHENTICATED": ["gcp_config_defaults", "cloud_run_allow_unauthenticated"],
            
            # Open Interpreter config
            "OPEN_INTERPRETER_MODEL_STRING": ["open_interpreter_config", "model_string_fallback"],
            "AZURE_OPENAI_API_KEY": ["open_interpreter_config", "azure_api_key"],
            "AZURE_OPENAI_API_BASE": ["open_interpreter_config", "azure_api_base"],
            "AZURE_OPENAI_API_VERSION": ["open_interpreter_config", "azure_api_version"],
            "AZURE_OPENAI_DEPLOYMENT_ID": ["open_interpreter_config", "azure_deployment_id"],
            "OPENAI_API_KEY": ["open_interpreter_config", "openai_api_key"],
            
            # ChromaDB config (transitioning to Qdrant)
            "CHROMA_DB_PATH": ["chroma_db_config", "path"],
            "CHROMA_DB_COLLECTION_NAME": ["chroma_db_config", "collection_name"],
        }
        
        self.env_config = {}
        
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Handle boolean values
                if value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                
                # Handle numeric values
                try:
                    if "." in value and value.replace(".", "", 1).isdigit():
                        value = float(value)
                    elif value.isdigit():
                        value = int(value)
                except ValueError:
                    pass
                
                # Set in env_config
                if isinstance(config_key, list):
                    # Handle nested keys
                    current = self.env_config
                    for i, key in enumerate(config_key):
                        if i == len(config_key) - 1:
                            # Last key, set the value
                            if key not in current:
                                current[key] = value
                        else:
                            # Create nested dict if not exists
                            if key not in current:
                                current[key] = {}
                            current = current[key]
                else:
                    # Simple key
                    self.env_config[config_key] = value
    
    def _merge_configs(self) -> Dict[str, Any]:
        """
        Merge base config with environment config.
        Environment config takes precedence.
        
        Returns:
            Dict containing the merged configuration.
        """
        def deep_merge(base, override):
            merged = base.copy()
            
            for key, value in override.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    # Recursively merge dictionaries
                    merged[key] = deep_merge(merged[key], value)
                else:
                    # Override with value from override
                    merged[key] = value
                    
            return merged
        
        return deep_merge(self.base_config, self.env_config)
        
    def get_value(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a specific config value.
        
        Args:
            key: Config key to get.
            default: Default value if key not found.
            
        Returns:
            Config value or default.
        """
        config = self.load_config()
        return config.get(key, default)