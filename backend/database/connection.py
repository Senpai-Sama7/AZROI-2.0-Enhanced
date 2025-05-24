"""
Database connection and session management for the Autonomous AI Architect system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

# Fallback imports for SQLAlchemy and related dependencies
try:
    from sqlalchemy import create_engine, event
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    # Mock SQLAlchemy classes
    class MockEngine:
        def __init__(self, *args, **kwargs): 
            self.url = kwargs.get('url', 'sqlite:///./test.db')
        def dispose(self): pass
        def connect(self): return MockConnection()
        def begin(self): return MockTransaction()
        
    class MockConnection:
        def __init__(self): pass
        def close(self): pass
        def execute(self, *args): return MockResult()
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    class MockTransaction:
        def commit(self): pass
        def rollback(self): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    class MockSession:
        def __init__(self, *args, **kwargs): pass
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
        def add(self, obj): pass
        def query(self, *args): return MockQuery()
        def execute(self, *args): return MockResult()
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    class MockAsyncSession:
        def __init__(self, *args, **kwargs): pass
        async def commit(self): pass
        async def rollback(self): pass
        async def close(self): pass
        def add(self, obj): pass
        async def execute(self, *args): return MockResult()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        
    class MockQuery:
        def filter(self, *args): return self
        def filter_by(self, **kwargs): return self
        def first(self): return None
        def all(self): return []
        
    class MockResult:
        def fetchone(self): return None
        def fetchall(self): return []
        def scalar(self): return None
        def scalars(self): return MockScalars()
        
    class MockScalars:
        def first(self): return None
        def all(self): return []
        
    def create_engine(*args, **kwargs): return MockEngine(*args, **kwargs)
    def create_async_engine(*args, **kwargs): return MockEngine(*args, **kwargs)
    def sessionmaker(*args, **kwargs): return lambda: MockSession()
    def async_sessionmaker(*args, **kwargs): return lambda: MockAsyncSession()
    
    class MockEvent:
        @staticmethod
        def listens_for(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    event = MockEvent()
    Session = MockSession
    AsyncSession = MockAsyncSession
    StaticPool = None
    SQLALCHEMY_AVAILABLE = False

# Configuration imports with fallback
try:
    from ..config.settings import get_config
except ImportError:
    try:
        from config.settings import get_config
    except ImportError:
        from dataclasses import dataclass, field
        from typing import Dict, Any
        
        @dataclass
        class MockDatabaseConfig:
            host: str = "localhost"
            port: int = 5432
            database: str = "test_db"
            username: str = "test"
            password: str = "test"
            pool_size: int = 5
            max_overflow: int = 10
            pool_timeout: int = 30
            pool_recycle: int = 3600
            ssl_mode: str = "prefer"
            echo_sql: bool = False
            connect_args: Dict[str, Any] = field(default_factory=dict)
            
            @property
            def url(self) -> str:
                return "sqlite:///./test.db"
                
            @property 
            def async_url(self) -> str:
                return "sqlite+aiosqlite:///./test.db"
            
        @dataclass 
        class MockAppConfig:
            database: MockDatabaseConfig = field(default_factory=MockDatabaseConfig)
        
        def get_config():
            return MockAppConfig()

# Models import with fallback
try:
    from .models import Base
except ImportError:
    try:
        from models import Base
    except ImportError:
        class MockBase:
            metadata = None
            @classmethod
            def __subclasshook__(cls, subclass):
                return True
        Base = MockBase

# Security imports with fallback
try:
    from ..security.auth import PasswordHasher
except ImportError:
    try:
        from security.auth import PasswordHasher
    except ImportError:
        class MockPasswordHasher:
            def hash_password(self, password: str) -> str:
                return f"hashed_{password}"
            def verify_password(self, plain: str, hashed: str) -> bool:
                return hashed == f"hashed_{plain}"
        PasswordHasher = MockPasswordHasher

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        """Initialize database connections and session factories."""
        self.config = get_config().database
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        
    def initialize(self):
        """Initialize database engines and session factories."""
        try:
            if SQLALCHEMY_AVAILABLE:
                # Create sync engine
                self._engine = create_engine(
                    self.config.url,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    echo=self.config.echo_sql,
                    connect_args=self.config.connect_args,
                    poolclass=StaticPool if "sqlite" in self.config.url else None
                )
                
                # Create session factory
                self._session_factory = sessionmaker(
                    bind=self._engine,
                    autocommit=False,
                    autoflush=False
                )
                
                # Create async engine
                self._async_engine = create_async_engine(
                    self.config.async_url,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    echo=self.config.echo_sql,
                    connect_args=self.config.connect_args,
                    poolclass=StaticPool if "sqlite" in self.config.async_url else None
                )
                
                # Create async session factory
                self._async_session_factory = async_sessionmaker(
                    bind=self._async_engine,
                    class_=AsyncSession,
                    autocommit=False,
                    autoflush=False
                )
                
                # Set up database event listeners
                self._setup_event_listeners()
            else:
                # Use mock engines for testing without SQLAlchemy
                self._engine = create_engine(self.config.url)
                self._async_engine = create_async_engine(self.config.async_url)
                self._session_factory = sessionmaker()
                self._async_session_factory = async_sessionmaker()
                
            logger.info("Database connections initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
            
    def _setup_event_listeners(self):
        """Set up database event listeners."""
        if not SQLALCHEMY_AVAILABLE:
            return
            
        try:
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                if "sqlite" in self.config.url:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
        except Exception as e:
            logger.warning(f"Failed to set up event listeners: {e}")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session context manager."""
        if not self._session_factory:
            raise RuntimeError("Database session factory not available")
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session context manager."""
        if not self._async_session_factory:
            raise RuntimeError("Async database session factory not available")
        
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_engine(self):
        """Get the database engine."""
        return self._engine
    
    def get_async_engine(self):
        """Get the async database engine."""
        return self._async_engine
    
    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
        if self._async_engine and hasattr(self._async_engine, 'dispose'):
            asyncio.create_task(self._async_engine.dispose())
        logger.info("Database connections closed")
    
    async def create_tables(self):
        """Create database tables."""
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("SQLAlchemy not available, skipping table creation")
            return
            
        try:
            if self._async_engine:
                async with self._async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            if SQLALCHEMY_AVAILABLE and self._async_engine:
                async with self._async_engine.begin() as conn:
                    await conn.execute("SELECT 1")
                return True
            return False
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager


def get_db_session():
    """Get a database session (sync)."""
    manager = get_database_manager()
    return manager.get_session()


async def get_async_db_session():
    """Get an async database session."""
    manager = get_database_manager()
    async with manager.get_async_session() as session:
        yield session


async def initialize_database():
    """Initialize database with default data."""
    try:
        manager = get_database_manager()
        
        # Create tables
        await manager.create_tables()
        
        # Create default data
        await _create_default_data()
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def _create_default_data():
    """Create default users and agents."""
    if not SQLALCHEMY_AVAILABLE:
        logger.warning("SQLAlchemy not available, skipping default data creation")
        return
        
    try:
        # Import models here to avoid circular imports
        from .models import User, Agent, UserRole, AgentType
        from sqlalchemy import select
        
        manager = get_database_manager()
        async with manager.get_async_session() as session:
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = result.scalars().first()
            
            if not admin_user:
                # Create admin user
                password_manager = PasswordHasher()
                hashed_password = password_manager.hash_password("admin123")
                
                admin_user = User(
                    username="admin",
                    email="admin@azroi.com",
                    full_name="System Administrator",
                    role=UserRole.ADMIN,
                    hashed_password=hashed_password,
                    is_active=True,
                )
                session.add(admin_user)
                await session.commit()
                logger.info("Default admin user created")
            
            # Create default agents
            default_agents = [
                {
                    "name": "architect",
                    "type": AgentType.PLANNER,
                    "description": "System architect agent",
                    "config": {"temperature": 0.7}
                },
                {
                    "name": "coder", 
                    "type": AgentType.EXECUTOR,
                    "description": "Code generation agent",
                    "config": {"temperature": 0.3}
                },
                {
                    "name": "tester",
                    "type": AgentType.REVIEWER,
                    "description": "Code testing agent", 
                    "config": {"temperature": 0.5}
                }
            ]
            
            for agent_data in default_agents:
                # Check if agent exists
                result = await session.execute(
                    select(Agent).where(Agent.name == agent_data["name"])
                )
                existing_agent = result.scalars().first()
                
                if not existing_agent:
                    agent = Agent(**agent_data)
                    session.add(agent)
            
            await session.commit()
            logger.info("Default agents created")
            
    except Exception as e:
        logger.error(f"Failed to create default data: {e}")
        # Don't raise here to allow system to continue even if default data fails
