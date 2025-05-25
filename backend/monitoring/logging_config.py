"""
Custom logging configuration for AZROI Autonomous AI Architect.
Provides structured logging with multiple handlers and formatters.
"""

import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add user ID if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        # Add request ID if present
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        return json.dumps(log_data, ensure_ascii=False)

class ContextFilter(logging.Filter):
    """Filter to add context information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to the log record."""
        # This could be enhanced to get context from async context vars
        # or from request-scoped storage
        return True

def setup_logging(config: Dict[str, Any], log_level: str = "INFO"):
    """
    Set up comprehensive logging configuration.
    
    Args:
        config: Application configuration dictionary
        log_level: Default log level
    """
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Logging configuration
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                '()': JSONFormatter,
            }
        },
        'filters': {
            'context_filter': {
                '()': ContextFilter,
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'stream': sys.stdout,
                'filters': ['context_filter']
            },
            'file_app': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': 'logs/azroi_app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['context_filter']
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': 'logs/azroi_error.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['context_filter']
            },
            'file_agent': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'json',
                'filename': 'logs/azroi_agents.log',
                'maxBytes': 20971520,  # 20MB
                'backupCount': 10,
                'filters': ['context_filter']
            },
            'file_performance': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': 'logs/azroi_performance.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['context_filter']
            }
        },
        'loggers': {
            'azroi': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_app', 'file_error'],
                'propagate': False
            },
            'azroi.agents': {
                'level': 'DEBUG',
                'handlers': ['file_agent'],
                'propagate': True
            },
            'azroi.performance': {
                'level': 'INFO',
                'handlers': ['file_performance'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file_app'],
                'propagate': False
            },
            'uvicorn.error': {
                'level': 'INFO',
                'handlers': ['console', 'file_error'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['file_app'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['console', 'file_app'],
                'propagate': False
            },
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': ['file_app'],
                'propagate': False
            },
            'redis': {
                'level': 'WARNING',
                'handlers': ['file_app'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Set up exception logging
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = logging.getLogger('azroi')
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_exception

class PerformanceLogger:
    """Logger for performance metrics and timing information."""
    
    def __init__(self):
        self.logger = logging.getLogger('azroi.performance')
    
    def log_agent_execution(self, agent_type: str, duration: float, success: bool, **kwargs):
        """Log agent execution performance."""
        self.logger.info(
            "Agent execution completed",
            extra={
                'extra_fields': {
                    'event_type': 'agent_execution',
                    'agent_type': agent_type,
                    'duration_seconds': duration,
                    'success': success,
                    **kwargs
                }
            }
        )
    
    def log_database_query(self, query_type: str, duration: float, rows_affected: int = None):
        """Log database query performance."""
        extra_data = {
            'event_type': 'database_query',
            'query_type': query_type,
            'duration_seconds': duration
        }
        
        if rows_affected is not None:
            extra_data['rows_affected'] = rows_affected
        
        self.logger.info(
            "Database query executed",
            extra={'extra_fields': extra_data}
        )
    
    def log_api_request(self, method: str, path: str, duration: float, status_code: int):
        """Log API request performance."""
        self.logger.info(
            "API request processed",
            extra={
                'extra_fields': {
                    'event_type': 'api_request',
                    'method': method,
                    'path': path,
                    'duration_seconds': duration,
                    'status_code': status_code
                }
            }
        )

class AgentLogger:
    """Specialized logger for agent operations."""
    
    def __init__(self):
        self.logger = logging.getLogger('azroi.agents')
    
    def log_agent_start(self, agent_id: str, agent_type: str, task_id: str, **kwargs):
        """Log agent start."""
        self.logger.info(
            f"Agent {agent_type} started",
            extra={
                'extra_fields': {
                    'event_type': 'agent_start',
                    'agent_id': agent_id,
                    'agent_type': agent_type,
                    'task_id': task_id,
                    **kwargs
                }
            }
        )
    
    def log_agent_complete(self, agent_id: str, agent_type: str, task_id: str, 
                          success: bool, result_summary: str = None, **kwargs):
        """Log agent completion."""
        extra_data = {
            'event_type': 'agent_complete',
            'agent_id': agent_id,
            'agent_type': agent_type,
            'task_id': task_id,
            'success': success,
            **kwargs
        }
        
        if result_summary:
            extra_data['result_summary'] = result_summary
        
        level = logging.INFO if success else logging.WARNING
        message = f"Agent {agent_type} {'completed successfully' if success else 'failed'}"
        
        self.logger.log(
            level,
            message,
            extra={'extra_fields': extra_data}
        )
    
    def log_agent_error(self, agent_id: str, agent_type: str, task_id: str, 
                       error: str, **kwargs):
        """Log agent error."""
        self.logger.error(
            f"Agent {agent_type} error",
            extra={
                'extra_fields': {
                    'event_type': 'agent_error',
                    'agent_id': agent_id,
                    'agent_type': agent_type,
                    'task_id': task_id,
                    'error': error,
                    **kwargs
                }
            }
        )

# Singleton instances
performance_logger = PerformanceLogger()
agent_logger = AgentLogger()
