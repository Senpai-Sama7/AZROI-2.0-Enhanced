"""
Configuration management for AZROI Autonomous AI Architect
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "azroi"
    username: str = "azroi_user"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    ssl_mode: str = "prefer"
    echo_sql: bool = False
    connect_args: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def url(self) -> str:
        """Generate database URL"""
        auth = f"{self.username}:{self.password}@" if self.password else f"{self.username}@"
        return f"postgresql://{auth}{self.host}:{self.port}/{self.database}"
    
    @property
    def async_url(self) -> str:
        """Generate async database URL"""
        auth = f"{self.username}:{self.password}@" if self.password else f"{self.username}@"
        return f"postgresql+asyncpg://{auth}{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    ssl: bool = False
    ttl: int = 3600
    max_connections: int = 100
    retry_on_timeout: bool = True
    
    @property
    def url(self) -> str:
        """Generate Redis URL"""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """LLM configuration"""
    default_model: str = "gpt-4o"
    openai_api_key: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_api_base: Optional[str] = None
    azure_api_version: str = "2024-02-01"
    azure_deployment_id: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3


@dataclass
class CrewAIConfig:
    """CrewAI specific configuration"""
    max_concurrent_crews: int = 5
    max_agents_per_crew: int = 10
    task_timeout: int = 600
    agent_memory_enabled: bool = True
    verbose_logging: bool = False
    max_iterations: int = 15
    step_callback_enabled: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    password_min_length: int = 8
    enable_cors: bool = True
    cors_origins: list = field(default_factory=lambda: ["*"])
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    prometheus_enabled: bool = True
    prometheus_port: int = 8002
    metrics_interval: int = 15
    log_requests: bool = True
    collect_hardware_metrics: bool = True
    health_check_timeout: int = 5
    tracing_enabled: bool = False
    tracing_sample_rate: float = 0.1


@dataclass
class CloudConfig:
    """Cloud provider configuration"""
    provider: str = "gcp"  # gcp, aws, azure
    project_id: Optional[str] = None
    region: str = "us-central1"
    credentials_path: Optional[str] = None
    storage_bucket: Optional[str] = None
    artifact_registry: Optional[str] = None
    cloud_run_service_prefix: str = "azroi"


@dataclass
class AppConfig:
    """Main application configuration"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: LogLevel = LogLevel.INFO
    base_path: str = "/home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend"
    max_concurrent_agents: int = 5
    task_timeout: int = 600
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    crewai: CrewAIConfig = field(default_factory=CrewAIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)


class ConfigManager:
    """Configuration manager for the application"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()
        self._setup_logging()
    
    def _find_config_file(self) -> str:
        """Find configuration file"""
        base_dir = Path(__file__).parent.parent
        possible_paths = [
            base_dir / "config.json",
            base_dir / "config" / f"{os.getenv('ENVIRONMENT', 'development')}.json",
            base_dir / "config" / "default.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # Return default config path
        return str(base_dir / "config.json")
    
    def _load_config(self) -> AppConfig:
        """Load configuration from file and environment variables"""
        config_data = {}
        
        # Load from file if exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load config file {self.config_path}: {e}")
        
        # Override with environment variables
        config_data.update(self._load_from_env())
        
        return self._create_config_from_dict(config_data)
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # App level configs
        if env_val := os.getenv("ENVIRONMENT"):
            env_config["environment"] = Environment(env_val.lower())
        if env_val := os.getenv("DEBUG"):
            env_config["debug"] = env_val.lower() in ("true", "1", "yes")
        if env_val := os.getenv("HOST"):
            env_config["host"] = env_val
        if env_val := os.getenv("PORT"):
            env_config["port"] = int(env_val)
        if env_val := os.getenv("LOG_LEVEL"):
            env_config["log_level"] = LogLevel(env_val.upper())
        
        # Database configs
        db_config = {}
        if env_val := os.getenv("DATABASE_URL"):
            # Parse DATABASE_URL if provided
            db_config["url"] = env_val
        else:
            if env_val := os.getenv("DB_HOST"):
                db_config["host"] = env_val
            if env_val := os.getenv("DB_PORT"):
                db_config["port"] = int(env_val)
            if env_val := os.getenv("DB_NAME"):
                db_config["database"] = env_val
            if env_val := os.getenv("DB_USER"):
                db_config["username"] = env_val
            if env_val := os.getenv("DB_PASSWORD"):
                db_config["password"] = env_val
        
        if db_config:
            env_config["database"] = db_config
        
        # Redis configs
        redis_config = {}
        if env_val := os.getenv("REDIS_URL"):
            redis_config["url"] = env_val
        else:
            if env_val := os.getenv("REDIS_HOST"):
                redis_config["host"] = env_val
            if env_val := os.getenv("REDIS_PORT"):
                redis_config["port"] = int(env_val)
            if env_val := os.getenv("REDIS_PASSWORD"):
                redis_config["password"] = env_val
        
        if redis_config:
            env_config["redis"] = redis_config
        
        # LLM configs
        llm_config = {}
        if env_val := os.getenv("OPENAI_API_KEY"):
            llm_config["openai_api_key"] = env_val
        if env_val := os.getenv("AZURE_OPENAI_API_KEY"):
            llm_config["azure_api_key"] = env_val
        if env_val := os.getenv("AZURE_OPENAI_API_BASE"):
            llm_config["azure_api_base"] = env_val
        if env_val := os.getenv("AZURE_OPENAI_DEPLOYMENT_ID"):
            llm_config["azure_deployment_id"] = env_val
        if env_val := os.getenv("ANTHROPIC_API_KEY"):
            llm_config["anthropic_api_key"] = env_val
        if env_val := os.getenv("GOOGLE_API_KEY"):
            llm_config["google_api_key"] = env_val
        
        if llm_config:
            env_config["llm"] = llm_config
        
        # Security configs
        security_config = {}
        if env_val := os.getenv("SECRET_KEY"):
            security_config["secret_key"] = env_val
        if env_val := os.getenv("JWT_EXPIRATION"):
            security_config["jwt_expiration"] = int(env_val)
        
        if security_config:
            env_config["security"] = security_config
        
        # Cloud configs
        cloud_config = {}
        if env_val := os.getenv("CLOUD_PROVIDER"):
            cloud_config["provider"] = env_val
        if env_val := os.getenv("GCP_PROJECT_ID"):
            cloud_config["project_id"] = env_val
        if env_val := os.getenv("CLOUD_REGION"):
            cloud_config["region"] = env_val
        if env_val := os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            cloud_config["credentials_path"] = env_val
        
        if cloud_config:
            env_config["cloud"] = cloud_config
        
        return env_config
    
    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> AppConfig:
        """Create AppConfig from dictionary data"""
        # Extract nested configs
        db_data = config_data.pop("database", {})
        redis_data = config_data.pop("redis", {})
        llm_data = config_data.pop("llm", {})
        crewai_data = config_data.pop("crewai", {})
        security_data = config_data.pop("security", {})
        monitoring_data = config_data.pop("monitoring", {})
        cloud_data = config_data.pop("cloud", {})
        
        # Create sub-configs
        database_config = DatabaseConfig(**db_data)
        redis_config = RedisConfig(**redis_data)
        llm_config = LLMConfig(**llm_data)
        crewai_config = CrewAIConfig(**crewai_data)
        security_config = SecurityConfig(**security_data)
        monitoring_config = MonitoringConfig(**monitoring_data)
        cloud_config = CloudConfig(**cloud_data)
        
        # Create main config
        # Filter config_data to only include fields that AppConfig accepts
        app_config_fields = {
            'environment', 'debug', 'host', 'port', 'workers', 
            'log_level', 'base_path', 'max_concurrent_agents', 'task_timeout'
        }
        
        filtered_config_data = {k: v for k, v in config_data.items() if k in app_config_fields}
        
        app_config = AppConfig(
            database=database_config,
            redis=redis_config,
            llm=llm_config,
            crewai=crewai_config,
            security=security_config,
            monitoring=monitoring_config,
            cloud=cloud_config,
            **filtered_config_data
        )
        
        return app_config
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.value),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    Path(self.config.base_path) / "logs" / "azroi.log",
                    mode='a'
                )
            ]
        )
        
        # Create logs directory if it doesn't exist
        log_dir = Path(self.config.base_path) / "logs"
        log_dir.mkdir(exist_ok=True)
    
    def get_config(self) -> AppConfig:
        """Get the current configuration"""
        return self.config
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self._setup_logging()
    
    def save_config(self, config_path: Optional[str] = None):
        """Save current configuration to file"""
        save_path = config_path or self.config_path
        
        # Convert config to dictionary
        config_dict = self._config_to_dict(self.config)
        
        try:
            with open(save_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config to {save_path}: {e}")
            raise
    
    def _config_to_dict(self, config: AppConfig) -> Dict[str, Any]:
        """Convert AppConfig to dictionary"""
        result = {}
        
        # Convert main config fields
        for field_name, field_value in config.__dict__.items():
            if hasattr(field_value, '__dict__'):
                # Convert nested dataclass to dict
                result[field_name] = field_value.__dict__.copy()
            elif isinstance(field_value, Enum):
                result[field_name] = field_value.value
            else:
                result[field_name] = field_value
        
        return result


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration"""
    return get_config_manager().get_config()


def reload_config():
    """Reload the global configuration"""
    get_config_manager().reload_config()


# Export commonly used configs
def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config().database


def get_redis_config() -> RedisConfig:
    """Get Redis configuration"""
    return get_config().redis


def get_llm_config() -> LLMConfig:
    """Get LLM configuration"""
    return get_config().llm


def get_crewai_config() -> CrewAIConfig:
    """Get CrewAI configuration"""
    return get_config().crewai


def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return get_config().security


def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration"""
    return get_config().monitoring


def get_cloud_config() -> CloudConfig:
    """Get cloud configuration"""
    return get_config().cloud
