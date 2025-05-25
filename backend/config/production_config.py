#!/usr/bin/env python3
"""
Production-ready Configuration Management System for Autonomous AI Architect
Following Azure best practices for secure, scalable configuration management.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

# Optional imports with fallbacks
try:
    import yaml
except ImportError:
    yaml = None

# Define SecretStr class that's compatible with both pydantic and standalone use
class SecretStr:
    """Secret string type that hides the value when printed"""
    def __init__(self, value: str = ""):
        self._secret_value = value
    
    def get_secret_value(self) -> str:
        return self._secret_value
    
    def __str__(self) -> str:
        return "*" * 8
    
    def __bool__(self) -> bool:
        return bool(self._secret_value)

try:
    from pydantic import BaseModel, Field, validator
    # Try to use pydantic's SecretStr if available, but fallback to our implementation
    try:
        from pydantic.types import SecretStr as PydanticSecretStr
        # Use pydantic's version if available
        SecretStr = PydanticSecretStr
    except ImportError:
        pass  # Use our fallback implementation
except ImportError:
    # Full fallback for when pydantic is not available
    BaseModel = object
    Field = lambda **kwargs: None
    validator = lambda *args, **kwargs: lambda f: f

try:
    import redis
    Redis = redis.Redis
except ImportError:
    redis = None
    Redis = None

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.core.exceptions import AzureError
except ImportError:
    SecretClient = None
    DefaultAzureCredential = None
    ManagedIdentityCredential = None
    AzureError = Exception

# Type checking imports
if TYPE_CHECKING:
    from typing import Type

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"

class CloudProvider(Enum):
    """Supported cloud providers"""
    AZURE = "azure"
    GCP = "gcp"
    AWS = "aws"
    HYBRID = "hybrid"

class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Database configuration with Azure security best practices"""
    host: str = "localhost"
    port: int = 5432
    database: str = "azroi_db"
    username: str = "azroi_user"
    password: SecretStr = field(default_factory=lambda: SecretStr(""))
    ssl_mode: str = "require"
    connection_pool_size: int = 20
    max_overflow: int = 10
    connection_timeout: int = 30
    command_timeout: int = 60
    retry_attempts: int = 3
    backup_enabled: bool = True
    encryption_at_rest: bool = True
    
    # Azure-specific settings
    azure_managed_identity: bool = True
    azure_key_vault_uri: Optional[str] = None
    connection_string_secret_name: Optional[str] = "db-connection-string"

@dataclass
class RedisConfig:
    """Redis configuration for caching and session management"""
    host: str = "localhost"
    port: int = 6379
    password: SecretStr = field(default_factory=lambda: SecretStr(""))
    database: int = 0
    ssl_enabled: bool = True
    connection_pool_size: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    health_check_interval: int = 30
    retry_on_timeout: bool = True
    
    # Azure-specific settings
    azure_cache_name: Optional[str] = None
    azure_managed_identity: bool = True

@dataclass
class AzureConfig:
    """Azure cloud configuration with security best practices"""
    # Core Azure settings
    tenant_id: str = ""
    subscription_id: str = ""
    resource_group: str = "azroi-rg"
    location: str = "eastus"
    
    # Authentication
    use_managed_identity: bool = True
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    
    # Key Vault
    key_vault_uri: str = ""
    key_vault_enabled: bool = True
    
    # Container Apps
    container_app_environment: str = "azroi-env"
    container_registry: str = "azroiregistry"
    
    # Storage
    storage_account: str = "azroistorage"
    storage_container: str = "artifacts"
    
    # AI Services
    openai_endpoint: str = ""
    openai_deployment: str = "gpt-4o"
    cognitive_services_endpoint: str = ""
    
    # Monitoring
    log_analytics_workspace: str = "azroi-logs"
    application_insights: str = "azroi-insights"
    
    # Security
    network_security_group: str = "azroi-nsg"
    private_endpoints_enabled: bool = True

@dataclass
class GCPConfig:
    """Google Cloud Platform configuration"""
    project_id: str = "ai-agent-system-458618"
    region: str = "us-central1"
    zone: str = "us-central1-a"
    
    # Storage
    gcs_bucket: str = "azroi-bucket"
    
    # Artifact Registry
    artifact_registry_repo: str = "ai-architect-apps"
    artifact_registry_region: str = "us-central1"
    
    # Cloud Run
    cloud_run_service_prefix: str = "azroi-svc"
    cloud_run_allow_unauthenticated: bool = False
    
    # AI Platform
    vertex_ai_location: str = "us-central1"
    
    # Credentials
    service_account_key_path: Optional[str] = None
    use_default_credentials: bool = True

@dataclass
class SecurityConfig:
    """Security configuration following Azure security best practices"""
    # Authentication
    jwt_secret_key: SecretStr = field(default_factory=lambda: SecretStr(""))
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30
    
    # API Security
    api_rate_limit_per_minute: int = 1000
    api_rate_limit_burst: int = 100
    cors_origins: List[str] = field(default_factory=lambda: ["https://localhost:3000"])
    
    # Encryption
    encryption_key: SecretStr = field(default_factory=lambda: SecretStr(""))
    data_encryption_enabled: bool = True
    tls_min_version: str = "1.2"
    
    # Azure AD integration
    azure_ad_enabled: bool = True
    azure_ad_tenant_id: str = ""
    azure_ad_client_id: str = ""
    azure_ad_client_secret: SecretStr = field(default_factory=lambda: SecretStr(""))
    
    # Role-based access control
    rbac_enabled: bool = True
    admin_users: List[str] = field(default_factory=list)
    
    # Audit logging
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 90

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    # Metrics
    prometheus_enabled: bool = True
    prometheus_port: int = 8002
    metrics_collection_interval: int = 15
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    structured_logging: bool = True
    log_retention_days: int = 30
    
    # Health checks
    health_check_enabled: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 10
    
    # Performance monitoring
    performance_monitoring_enabled: bool = True
    slow_query_threshold_ms: int = 1000
    memory_usage_alert_threshold: float = 0.8
    cpu_usage_alert_threshold: float = 0.8
    
    # Azure Application Insights
    app_insights_enabled: bool = True
    app_insights_connection_string: str = ""
    
    # Alerting
    alert_webhook_url: Optional[str] = None
    alert_email_recipients: List[str] = field(default_factory=list)

@dataclass
class AgentConfig:
    """AI Agent configuration"""
    # Agent limits
    max_concurrent_agents: int = 10
    agent_timeout_minutes: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 1.5
    
    # CrewAI configuration
    crewai_enabled: bool = True
    crew_process_type: str = "sequential"
    crew_verbose: bool = False
    crew_memory_enabled: bool = True
    
    # LLM configuration
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Tool configuration
    tools_enabled: List[str] = field(default_factory=lambda: [
        "ArchitectureAnalysisTool",
        "CodeGenerationTool", 
        "InfrastructureProvisioningTool",
        "QualityAssuranceTool"
    ])
    tool_timeout_seconds: int = 300
    
    # Memory and context
    context_window_size: int = 8000
    memory_persistence_enabled: bool = True
    conversation_history_limit: int = 100

@dataclass
class ProductionConfig:
    """Main production configuration class"""
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Core services
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    
    # Cloud providers
    cloud_provider: CloudProvider = CloudProvider.AZURE
    azure: AzureConfig = field(default_factory=AzureConfig)
    gcp: GCPConfig = field(default_factory=GCPConfig)
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # File storage
    temp_dir: str = "/tmp/azroi"
    upload_max_size_mb: int = 100
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "azure_integration": True,
        "gcp_integration": True,
        "advanced_monitoring": True,
        "audit_logging": True,
        "auto_scaling": True,
        "backup_automation": True
    })

class ConfigurationManager:
    """Production-ready configuration manager with Azure Key Vault integration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config: ProductionConfig = ProductionConfig()  # Initialize with defaults
        self._redis_client: Optional[Any] = None  # Use Any to avoid import issues
        self._azure_credential: Optional[Any] = None
        self._key_vault_client: Optional[Any] = None
        self._config_cache_ttl = 300  # 5 minutes
        
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        env = os.getenv("AZROI_ENV", "development")
        return f"config/{env}.yaml"
    
    async def initialize(self) -> None:
        """Initialize configuration manager"""
        try:
            logger.info("Initializing Configuration Manager...")
            
            # Load base configuration
            await self._load_configuration()
            
            # Initialize Azure services if enabled
            if self.config.azure.key_vault_enabled:
                await self._initialize_azure_services()
            
            # Initialize Redis for configuration caching
            if self.config.redis:
                await self._initialize_redis()
            
            # Load secrets from Key Vault
            await self._load_secrets()
            
            # Validate configuration
            await self._validate_configuration()
            
            logger.info("Configuration Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize configuration manager: {e}")
            raise
    
    async def _load_configuration(self) -> None:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return

            with open(self.config_path, 'r') as f:
                if yaml and (self.config_path.endswith('.yaml') or self.config_path.endswith('.yml')):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            # Override with environment variables
            config_data = self._apply_environment_overrides(config_data)

            # Update configuration object
            self.config = ProductionConfig(**config_data)

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _apply_environment_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        env_mappings = {
            "AZROI_ENV": "environment",
            "AZROI_DEBUG": "debug",
            "AZROI_API_HOST": "api_host",
            "AZROI_API_PORT": "api_port",
            "AZROI_CLOUD_PROVIDER": "cloud_provider",

            # Database
            "AZROI_DB_HOST": "database.host",
            "AZROI_DB_PORT": "database.port",
            "AZROI_DB_NAME": "database.database",
            "AZROI_DB_USER": "database.username",
            "AZROI_DB_PASSWORD": "database.password",

            # Azure
            "AZURE_TENANT_ID": "azure.tenant_id",
            "AZURE_SUBSCRIPTION_ID": "azure.subscription_id",
            "AZURE_RESOURCE_GROUP": "azure.resource_group",
            "AZURE_KEY_VAULT_URI": "azure.key_vault_uri",

            # Redis
            "AZROI_REDIS_HOST": "redis.host",
            "AZROI_REDIS_PORT": "redis.port",
            "AZROI_REDIS_PASSWORD": "redis.password",
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_data, config_path, value)

        return config_data

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested dictionary value using dot notation"""
        keys = path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Convert string values to appropriate types
        if isinstance(value, str):
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)

        current[keys[-1]] = value

    async def _initialize_azure_services(self) -> None:
        """Initialize Azure services"""
        try:
            if not DefaultAzureCredential or not SecretClient:
                logger.warning("Azure libraries not installed, skipping Azure initialization")
                return

            if self.config.azure.use_managed_identity and ManagedIdentityCredential:
                self._azure_credential = ManagedIdentityCredential()
            elif DefaultAzureCredential:
                self._azure_credential = DefaultAzureCredential()

            if self.config.azure.key_vault_uri and SecretClient and self._azure_credential:
                self._key_vault_client = SecretClient(
                    vault_url=self.config.azure.key_vault_uri,
                    credential=self._azure_credential
                )

                # Test connection
                try:
                    if hasattr(self._key_vault_client, 'get_secret'):
                        await asyncio.to_thread(self._key_vault_client.get_secret, "test-secret")
                        logger.info("Azure Key Vault connection established")
                except Exception:
                    logger.warning("Azure Key Vault test connection failed, but client initialized")

        except AzureError as e:
            logger.warning(f"Azure services initialization failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error initializing Azure services: {e}")

    async def _initialize_redis(self) -> None:
        """Initialize Redis connection"""
        try:
            if not redis or not Redis:
                logger.warning("Redis library not installed, skipping Redis initialization")
                return

            self._redis_client = Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                password=self.config.redis.password.get_secret_value() if self.config.redis.password else None,
                db=self.config.redis.database,
                ssl=self.config.redis.ssl_enabled,
                socket_timeout=self.config.redis.socket_timeout,
                socket_connect_timeout=self.config.redis.socket_connect_timeout,
                retry_on_timeout=self.config.redis.retry_on_timeout,
                health_check_interval=self.config.redis.health_check_interval
            )

            # Test connection
            if hasattr(self._redis_client, 'ping'):
                await asyncio.to_thread(self._redis_client.ping)
                logger.info("Redis connection established")

        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
            self._redis_client = None

    async def _load_secrets(self) -> None:
        """Load secrets from Azure Key Vault"""
        if not self._key_vault_client:
            return

        try:
            secret_mappings = {
                "db-password": "database.password",
                "jwt-secret": "security.jwt_secret_key",
                "encryption-key": "security.encryption_key",
                "azure-ad-client-secret": "security.azure_ad_client_secret",
                "redis-password": "redis.password"
            }

            for secret_name, config_path in secret_mappings.items():
                try:
                    secret = await asyncio.to_thread(
                        self._key_vault_client.get_secret, secret_name
                    )
                    self._set_nested_value(asdict(self.config), config_path, secret.value)
                except Exception as e:
                    logger.warning(f"Failed to load secret {secret_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")

    async def _validate_configuration(self) -> None:
        """Validate configuration"""
        errors = []

        # Validate required Azure settings
        if self.config.cloud_provider == CloudProvider.AZURE:
            if not self.config.azure.subscription_id:
                errors.append("Azure subscription ID is required")
            if not self.config.azure.resource_group:
                errors.append("Azure resource group is required")

        # Validate database configuration
        if not self.config.database.host:
            errors.append("Database host is required")

        # Validate security settings
        if self.config.environment == Environment.PRODUCTION:
            if not self.config.security.jwt_secret_key.get_secret_value():
                errors.append("JWT secret key is required in production")
            if not self.config.security.encryption_key.get_secret_value():
                errors.append("Encryption key is required in production")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    async def get_config(self) -> ProductionConfig:
        """Get current configuration"""
        return self.config
    
    async def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration"""
        try:
            # Apply updates to current config
            current_data = asdict(self.config)
            for path, value in updates.items():
                self._set_nested_value(current_data, path, value)

            # Create new config object
            self.config = ProductionConfig(**current_data)
            logger.info("Configuration updated successfully")
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            raise

    async def reload_config(self) -> None:
        """Reload configuration from source"""
        try:
            await self._load_configuration()
            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            raise

    async def get_feature_flag(self, feature_name: str) -> bool:
        """Get the value of a feature flag"""
        try:
            return self.config.features.get(feature_name, False)
        except Exception as e:
            logger.error(f"Failed to get feature flag '{feature_name}': {e}")
            raise

    async def set_feature_flag(self, feature_name: str, enabled: bool) -> None:
        """Set the value of a feature flag"""
        try:
            self.config.features[feature_name] = enabled
            logger.info(f"Feature flag '{feature_name}' set to {enabled}")
        except Exception as e:
            logger.error(f"Failed to set feature flag '{feature_name}': {e}")
            raise

    async def health_check(self) -> bool:
        """Perform a health check of the configuration system"""
        try:
            # Check Azure Key Vault connection
            if self.config.azure.key_vault_enabled and self._key_vault_client:
                await asyncio.to_thread(self._key_vault_client.get_secret, "test-secret")

            # Check Redis connection
            if self._redis_client:
                await asyncio.to_thread(self._redis_client.ping)

            logger.info("Health check passed")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def save_config_to_file(self, file_path: Optional[str] = None) -> None:
        """Save current configuration to file"""
        try:
            target_path = file_path or self.config_path
            config_data = asdict(self.config)
            
            # Convert SecretStr objects to strings for serialization
            def convert_secrets(obj):
                if isinstance(obj, dict):
                    return {k: convert_secrets(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_secrets(v) for v in obj]
                elif isinstance(obj, SecretStr):
                    return "***REDACTED***"  # Don't save actual secrets
                return obj
            
            config_data = convert_secrets(config_data)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Save based on file extension
            with open(target_path, 'w') as f:
                if yaml and (target_path.endswith('.yaml') or target_path.endswith('.yml')):
                    yaml.dump(config_data, f, default_flow_style=False)
                else:
                    json.dump(config_data, f, indent=2, default=str)
            
            logger.info(f"Configuration saved to {target_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    async def backup_config(self) -> str:
        """Create a backup of current configuration"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_path}.backup_{timestamp}"
            await self.save_config_to_file(backup_path)
            logger.info(f"Configuration backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            raise

    async def restore_config(self, backup_path: str) -> None:
        """Restore configuration from backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Load backup
            with open(backup_path, 'r') as f:
                if yaml and (backup_path.endswith('.yaml') or backup_path.endswith('.yml')):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # Apply environment overrides
            config_data = self._apply_environment_overrides(config_data)
            
            # Update configuration
            self.config = ProductionConfig(**config_data)
            await self._validate_configuration()
            
            logger.info(f"Configuration restored from {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            raise

    async def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration (without secrets)"""
        try:
            summary = {
                "environment": self.config.environment.value,
                "cloud_provider": self.config.cloud_provider.value,
                "debug": self.config.debug,
                "api_host": self.config.api_host,
                "api_port": self.config.api_port,
                "database_host": self.config.database.host,
                "redis_host": self.config.redis.host,
                "feature_flags": dict(self.config.features),
                "azure_settings": {
                    "key_vault_enabled": self.config.azure.key_vault_enabled,
                    "use_managed_identity": self.config.azure.use_managed_identity,
                    "resource_group": self.config.azure.resource_group,
                    "location": self.config.azure.location
                },
                "monitoring": {
                    "prometheus_enabled": self.config.monitoring.prometheus_enabled,
                    "app_insights_enabled": self.config.monitoring.app_insights_enabled,
                    "log_level": self.config.monitoring.log_level.value
                },
                "agents": {
                    "max_concurrent_agents": self.config.agents.max_concurrent_agents,
                    "default_model": self.config.agents.default_model,
                    "tools_enabled": len(self.config.agents.tools_enabled)
                }
            }
            return summary
        except Exception as e:
            logger.error(f"Failed to get config summary: {e}")
            raise

    async def validate_azure_connectivity(self) -> Dict[str, bool]:
        """Validate Azure service connectivity"""
        results = {
            "key_vault": False,
            "managed_identity": False,
            "subscription_access": False
        }
        
        if not self._azure_credential:
            return results
        
        try:
            # Test Key Vault access
            if self._key_vault_client and hasattr(self._key_vault_client, 'get_secret'):
                try:
                    await asyncio.to_thread(self._key_vault_client.get_secret, "test-secret")
                    results["key_vault"] = True
                except Exception:
                    pass
            
            # Test managed identity (if available)
            if self.config.azure.use_managed_identity:
                try:
                    # Try to get a token to validate managed identity
                    if hasattr(self._azure_credential, 'get_token'):
                        token = await asyncio.to_thread(
                            self._azure_credential.get_token, 
                            "https://management.azure.com/.default"
                        )
                        if token:
                            results["managed_identity"] = True
                            results["subscription_access"] = True
                except Exception:
                    pass
            
        except Exception as e:
            logger.warning(f"Azure connectivity validation failed: {e}")
        
        return results

    def get_environment_overrides(self) -> Dict[str, str]:
        """Get current environment variable overrides"""
        env_vars = {}
        env_mappings = {
            "AZROI_ENV": "environment",
            "AZROI_DEBUG": "debug",
            "AZROI_API_HOST": "api_host",
            "AZROI_API_PORT": "api_port",
            "AZROI_CLOUD_PROVIDER": "cloud_provider",
            "AZROI_DB_HOST": "database.host",
            "AZROI_DB_PORT": "database.port",
            "AZROI_DB_NAME": "database.database",
            "AZROI_DB_USER": "database.username",
            "AZURE_TENANT_ID": "azure.tenant_id",
            "AZURE_SUBSCRIPTION_ID": "azure.subscription_id",
            "AZURE_RESOURCE_GROUP": "azure.resource_group",
            "AZURE_KEY_VAULT_URI": "azure.key_vault_uri",
            "AZROI_REDIS_HOST": "redis.host",
            "AZROI_REDIS_PORT": "redis.port",
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                env_vars[env_var] = value
        
        return env_vars

# Global configuration manager instance
config_manager = ConfigurationManager()

async def get_config() -> ProductionConfig:
    """Get global configuration"""
    return await config_manager.get_config()

async def initialize_config(config_path: Optional[str] = None) -> None:
    """Initialize global configuration"""
    global config_manager
    if config_path:
        config_manager = ConfigurationManager(config_path)
    await config_manager.initialize()
