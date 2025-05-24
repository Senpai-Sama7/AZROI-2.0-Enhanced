"""
Database module for Autonomous AI Architect system.
Provides SQLAlchemy models and database management functionality.
"""

# Import models with fallback
try:
    from .models import Base, User, Project, Task, Agent, CrewSession, TaskExecution, AuditLog
except ImportError:
    # Mock models for when SQLAlchemy is not available
    class MockModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    Base = MockModel
    User = MockModel
    Project = MockModel
    Task = MockModel
    Agent = MockModel
    CrewSession = MockModel
    TaskExecution = MockModel
    AuditLog = MockModel

# Import connection utilities with fallback
try:
    from .connection import DatabaseManager, get_db_session, get_async_db_session
except ImportError:
    # Mock database functions
    class MockDatabaseManager:
        def __init__(self): pass
        def initialize(self): pass
        def close(self): pass
        def get_session(self): return MockSession()
        async def get_async_session(self): return MockAsyncSession()
    
    class MockSession:
        def __init__(self): pass
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    
    class MockAsyncSession:
        def __init__(self): pass
        async def commit(self): pass
        async def rollback(self): pass
        async def close(self): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    
    DatabaseManager = MockDatabaseManager
    
    def get_db_session():
        return MockSession()
    
    async def get_async_db_session():
        yield MockAsyncSession()

# Import repositories with fallback
try:
    from .repositories import (
        UserRepository,
        ProjectRepository, 
        TaskRepository,
        AgentRepository,
        CrewSessionRepository,
        TaskExecutionRepository,
        AuditLogRepository
    )
except ImportError:
    # Mock repositories
    class MockRepository:
        def __init__(self, *args, **kwargs): pass
        async def create(self, *args, **kwargs): return MockModel()
        async def get(self, *args, **kwargs): return MockModel()
        async def get_all(self, *args, **kwargs): return []
        async def update(self, *args, **kwargs): return MockModel()
        async def delete(self, *args, **kwargs): return True
    
    UserRepository = MockRepository
    ProjectRepository = MockRepository
    TaskRepository = MockRepository
    AgentRepository = MockRepository
    CrewSessionRepository = MockRepository
    TaskExecutionRepository = MockRepository
    AuditLogRepository = MockRepository

__all__ = [
    'Base',
    'User',
    'Project', 
    'Task',
    'Agent',
    'CrewSession',
    'TaskExecution',
    'AuditLog',
    'DatabaseManager',
    'get_db_session',
    'get_async_db_session',
    'UserRepository',
    'ProjectRepository',
    'TaskRepository', 
    'AgentRepository',
    'CrewSessionRepository',
    'TaskExecutionRepository',
    'AuditLogRepository'
]
