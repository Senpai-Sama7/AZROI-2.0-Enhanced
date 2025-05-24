"""
Comprehensive logging system for AZROI
"""
import logging
import logging.handlers
import sys
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
import threading
from contextlib import contextmanager


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """Log context for structured logging"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    crew_id: Optional[str] = None
    task_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class StructuredLogger:
    """Structured logger with context support"""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self._context: LogContext = LogContext()
        self._local = threading.local()
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger(name)
    
    def _get_context(self) -> LogContext:
        """Get current log context"""
        if hasattr(self._local, 'context'):
            return self._local.context
        return self._context
    
    def _set_context(self, context: LogContext):
        """Set current log context"""
        self._local.context = context
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for temporary log context"""
        current_context = self._get_context()
        new_context = LogContext(**{**asdict(current_context), **kwargs})
        old_context = getattr(self._local, 'context', None)
        
        try:
            self._set_context(new_context)
            yield
        finally:
            if old_context:
                self._local.context = old_context
            else:
                delattr(self._local, 'context')
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Bind context variables"""
        current_context = self._get_context()
        new_context = LogContext(**{**asdict(current_context), **kwargs})
        
        new_logger = StructuredLogger(self.name, self.level)
        new_logger._set_context(new_context)
        return new_logger
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method"""
        context = self._get_context()
        context_dict = context.to_dict()
        
        # Merge context with additional kwargs
        log_data = {**context_dict, **kwargs}
        
        getattr(self.logger, level.lower())(message, **log_data)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message"""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            kwargs['traceback'] = traceback.format_exc()
        
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            kwargs['traceback'] = traceback.format_exc()
        
        self._log("CRITICAL", message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        kwargs['traceback'] = traceback.format_exc()
        self._log("ERROR", message, **kwargs)


class LogManager:
    """Centralized log management"""
    
    def __init__(self, log_dir: Union[str, Path] = None, level: LogLevel = LogLevel.INFO):
        self.log_dir = Path(log_dir) if log_dir else Path("./logs")
        self.level = level
        self.loggers: Dict[str, StructuredLogger] = {}
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup root logger
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Setup root logger configuration"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.level.value))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler for all logs
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "azroi.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
        # JSON structured logs
        json_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "structured.jsonl",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,
            encoding='utf-8'
        )
        json_formatter = StructuredFormatter()
        json_handler.setFormatter(json_formatter)
        root_logger.addHandler(json_handler)
    
    def get_logger(self, name: str) -> StructuredLogger:
        """Get or create a logger"""
        if name not in self.loggers:
            self.loggers[name] = StructuredLogger(name, self.level)
        return self.loggers[name]
    
    def set_level(self, level: LogLevel):
        """Set global log level"""
        self.level = level
        logging.getLogger().setLevel(getattr(logging, level.value))
        
        for logger in self.loggers.values():
            logger.level = level
    
    def create_component_logger(self, component: str) -> StructuredLogger:
        """Create a logger with component context"""
        logger = self.get_logger(f"azroi.{component}")
        return logger.bind(component=component)
    
    def create_agent_logger(self, agent_id: str, crew_id: Optional[str] = None) -> StructuredLogger:
        """Create a logger for an agent"""
        logger = self.get_logger(f"azroi.agent.{agent_id}")
        context = {"agent_id": agent_id}
        if crew_id:
            context["crew_id"] = crew_id
        return logger.bind(**context)
    
    def create_task_logger(self, task_id: str, agent_id: Optional[str] = None) -> StructuredLogger:
        """Create a logger for a task"""
        logger = self.get_logger(f"azroi.task.{task_id}")
        context = {"task_id": task_id}
        if agent_id:
            context["agent_id"] = agent_id
        return logger.bind(**context)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'):
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


class PerformanceLogger:
    """Performance monitoring logger"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
    
    @contextmanager
    def timing(self, operation: str, **context):
        """Context manager for timing operations"""
        start_time = datetime.utcnow()
        self.logger.info(f"Starting {operation}", operation=operation, **context)
        
        try:
            yield
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(
                f"Completed {operation}",
                operation=operation,
                duration_seconds=duration,
                status="success",
                **context
            )
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(
                f"Failed {operation}",
                operation=operation,
                duration_seconds=duration,
                status="error",
                error=e,
                **context
            )
            raise
    
    def log_metrics(self, metrics: Dict[str, Union[int, float]], **context):
        """Log performance metrics"""
        self.logger.info("Performance metrics", metrics=metrics, **context)


# Global log manager
_log_manager: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Get the global log manager"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def get_logger(name: str) -> StructuredLogger:
    """Get a logger by name"""
    return get_log_manager().get_logger(name)


def get_component_logger(component: str) -> StructuredLogger:
    """Get a component logger"""
    return get_log_manager().create_component_logger(component)


def get_agent_logger(agent_id: str, crew_id: Optional[str] = None) -> StructuredLogger:
    """Get an agent logger"""
    return get_log_manager().create_agent_logger(agent_id, crew_id)


def get_task_logger(task_id: str, agent_id: Optional[str] = None) -> StructuredLogger:
    """Get a task logger"""
    return get_log_manager().create_task_logger(task_id, agent_id)


def setup_logging(log_dir: Union[str, Path] = None, level: LogLevel = LogLevel.INFO):
    """Setup global logging configuration"""
    global _log_manager
    _log_manager = LogManager(log_dir, level)


# Convenience functions
def log_startup(service_name: str, version: str, config: Dict[str, Any]):
    """Log service startup"""
    logger = get_component_logger("startup")
    logger.info(
        f"Starting {service_name}",
        service=service_name,
        version=version,
        config=config
    )


def log_shutdown(service_name: str):
    """Log service shutdown"""
    logger = get_component_logger("shutdown")
    logger.info(f"Shutting down {service_name}", service=service_name)


def log_request(method: str, path: str, user_id: Optional[str] = None, **kwargs):
    """Log HTTP request"""
    logger = get_component_logger("http")
    logger.info(
        f"{method} {path}",
        http_method=method,
        http_path=path,
        user_id=user_id,
        **kwargs
    )


def log_response(method: str, path: str, status_code: int, duration: float, **kwargs):
    """Log HTTP response"""
    logger = get_component_logger("http")
    logger.info(
        f"{method} {path} - {status_code}",
        http_method=method,
        http_path=path,
        http_status=status_code,
        duration_seconds=duration,
        **kwargs
    )
