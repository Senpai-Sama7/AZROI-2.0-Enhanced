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
        def __init__(self, *args, **kwargs): pass
        def dispose(self): pass
        def connect(self): return MockConnection()
        
    class MockConnection:
        def __init__(self): pass
        def close(self): pass
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
        def first(self): return None
        def all(self): return []
        
    class MockResult:
        def fetchone(self): return None
        def fetchall(self): return []
        def scalar(self): return None
        
    def create_engine(*args, **kwargs): return MockEngine()
    def create_async_engine(*args, **kwargs): return MockEngine()
    def sessionmaker(*args, **kwargs): return lambda: MockSession()
    def async_sessionmaker(*args, **kwargs): return lambda: MockAsyncSession()
    def event(*args, **kwargs): pass
    
    Session = MockSession
    AsyncSession = MockAsyncSession
    StaticPool = None
    SQLALCHEMY_AVAILABLE = False

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

try:
    from .models import Base
except ImportError:
    try:
        from models import Base
    except ImportError:
        from sqlalchemy.orm import declarative_base
        Base = declarative_base()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        self.config = get_config().database
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connections and session factories."""
        if self._initialized:
            return
        
        try:
            # Create synchronous engine
            self._engine = create_engine(
                self.config.url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo_sql,
                connect_args=self.config.connect_args
            )
            
            # Create asynchronous engine if async URL is provided
            if self.config.async_url:
                self._async_engine = create_async_engine(
                    self.config.async_url,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    echo=self.config.echo_sql,
                    connect_args=self.config.connect_args
                )
                
                self._async_session_factory = async_sessionmaker(
                    bind=self._async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False
            )
            
            # Set up database event listeners
            self._setup_event_listeners()
            
            self._initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Set up database event listeners for logging and monitoring."""
        
        @event.listens_for(self._engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")
        
        @event.listens_for(self._engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Database connection checked back into pool")
    
    async def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            self.initialize()
        
        try:
            if self._async_engine:
                async with self._async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            else:
                Base.metadata.create_all(bind=self._engine)
            
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def drop_tables(self):
        """Drop all database tables."""
        if not self._initialized:
            self.initialize()
        
        try:
            if self._async_engine:
                async with self._async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            else:
                Base.metadata.drop_all(bind=self._engine)
            
            logger.info("Database tables dropped successfully")
            
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a synchronous database session."""
        if not self._initialized:
            self.initialize()
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an asynchronous database session."""
        if not self._initialized:
            self.initialize()
        
        if not self._async_session_factory:
            raise RuntimeError("Async database session factory not available")
        
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()
    
    def get_engine(self):
        """Get the synchronous database engine."""
        if not self._initialized:
            self.initialize()
        return self._engine
    
    def get_async_engine(self):
        """Get the asynchronous database engine."""
        if not self._initialized:
            self.initialize()
        return self._async_engine
    
    async def health_check(self) -> bool:
        """Perform a database health check."""
        try:
            if self._async_engine:
                async with self._async_engine.begin() as conn:
                    await conn.execute("SELECT 1")
            else:
                with self._engine.begin() as conn:
                    conn.execute("SELECT 1")
            
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        
        if self._engine:
            self._engine.dispose()
        
        self._initialized = False
        logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for getting a database session."""
    manager = get_db_manager()
    with manager.get_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting an async database session."""
    manager = get_db_manager()
    async with manager.get_async_session() as session:
        yield session


class DatabaseInitializer:
    """Database initialization utilities."""
    
    @staticmethod
    async def initialize_database():
        """Initialize the database with tables and default data."""
        try:
            manager = get_db_manager()
            manager.initialize()
            await manager.create_tables()
            
            # Create default data
            await DatabaseInitializer._create_default_data()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @staticmethod
    async def _create_default_data():
        """Create default data in the database."""
        from .models import User, Agent, UserRole, AgentType
        from ..security.auth import PasswordManager
        
        manager = get_db_manager()
        
        # Check if we're using async sessions
        if manager._async_session_factory:
            async with manager.get_async_session() as session:
                await DatabaseInitializer._create_default_data_async(session)
        else:
            with manager.get_session() as session:
                DatabaseInitializer._create_default_data_sync(session)
    
    @staticmethod
    async def _create_default_data_async(session: AsyncSession):
        """Create default data using async session."""
        from .models import User, Agent, UserRole, AgentType
        from ..security.auth import PasswordManager
        from sqlalchemy import select
        
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            # Create default admin user
            password_manager = PasswordManager()
            hashed_password = password_manager.hash_password("admin123")
            
            admin_user = User(
                username="admin",
                email="admin@azroi.com",
                full_name="System Administrator",
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            session.add(admin_user)
            logger.info("Created default admin user")
        
        # Create default agents
        default_agents = [
            {
                "name": "System Architect",
                "agent_type": AgentType.ARCHITECT,
                "description": "AI agent specialized in system architecture and design",
                "capabilities": ["architecture_design", "system_analysis", "technology_recommendations"],
                "tools": ["architecture_analysis", "design_patterns", "scalability_assessment"]
            },
            {
                "name": "Code Generator",
                "agent_type": AgentType.CODE_EXECUTOR,
                "description": "AI agent specialized in code generation and implementation",
                "capabilities": ["code_generation", "refactoring", "optimization"],
                "tools": ["code_generation", "syntax_validation", "best_practices"]
            },
            {
                "name": "Cloud Deployer",
                "agent_type": AgentType.CLOUD_DEPLOYER,
                "description": "AI agent specialized in cloud infrastructure and deployment",
                "capabilities": ["infrastructure_provisioning", "deployment_automation", "monitoring_setup"],
                "tools": ["infrastructure_provisioning", "deployment_scripts", "monitoring_config"]
            },
            {
                "name": "Quality Assurance",
                "agent_type": AgentType.QUALITY_ASSURANCE,
                "description": "AI agent specialized in quality assurance and testing",
                "capabilities": ["test_generation", "code_review", "quality_metrics"],
                "tools": ["quality_assurance", "test_automation", "performance_analysis"]
            }
        ]
        
        for agent_data in default_agents:
            result = await session.execute(
                select(Agent).where(Agent.name == agent_data["name"])
            )
            existing_agent = result.scalar_one_or_none()
            
            if not existing_agent:
                agent = Agent(**agent_data)
                session.add(agent)
                logger.info(f"Created default agent: {agent_data['name']}")
        
        await session.commit()
    
    @staticmethod
    def _create_default_data_sync(session: Session):
        """Create default data using sync session."""
        from .models import User, Agent, UserRole, AgentType
        from ..security.auth import PasswordManager
        
        # Check if admin user exists
        admin_user = session.query(User).filter_by(username="admin").first()
        
        if not admin_user:
            # Create default admin user
            password_manager = PasswordManager()
            hashed_password = password_manager.hash_password("admin123")
            
            admin_user = User(
                username="admin",
                email="admin@azroi.com",
                full_name="System Administrator",
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            session.add(admin_user)
            logger.info("Created default admin user")
        
        # Create default agents
        default_agents = [
            {
                "name": "System Architect",
                "agent_type": AgentType.ARCHITECT,
                "description": "AI agent specialized in system architecture and design",
                "capabilities": ["architecture_design", "system_analysis", "technology_recommendations"],
                "tools": ["architecture_analysis", "design_patterns", "scalability_assessment"]
            },
            {
                "name": "Code Generator",
                "agent_type": AgentType.CODE_EXECUTOR,
                "description": "AI agent specialized in code generation and implementation",
                "capabilities": ["code_generation", "refactoring", "optimization"],
                "tools": ["code_generation", "syntax_validation", "best_practices"]
            },
            {
                "name": "Cloud Deployer",
                "agent_type": AgentType.CLOUD_DEPLOYER,
                "description": "AI agent specialized in cloud infrastructure and deployment",
                "capabilities": ["infrastructure_provisioning", "deployment_automation", "monitoring_setup"],
                "tools": ["infrastructure_provisioning", "deployment_scripts", "monitoring_config"]
            },
            {
                "name": "Quality Assurance",
                "agent_type": AgentType.QUALITY_ASSURANCE,
                "description": "AI agent specialized in quality assurance and testing",
                "capabilities": ["test_generation", "code_review", "quality_metrics"],
                "tools": ["quality_assurance", "test_automation", "performance_analysis"]
            }
        ]
        
        for agent_data in default_agents:
            existing_agent = session.query(Agent).filter_by(name=agent_data["name"]).first()
            
            if not existing_agent:
                agent = Agent(**agent_data)
                session.add(agent)
                logger.info(f"Created default agent: {agent_data['name']}")
        
        session.commit()
