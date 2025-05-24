"""
SQLAlchemy database models for the Autonomous AI Architect system.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum

Base = declarative_base()


class UserRole(enum.Enum):
    """User roles enum."""
    ADMIN = "admin"
    USER = "user"
    AGENT = "agent"
    READONLY = "readonly"


class TaskStatus(enum.Enum):
    """Task status enum."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(enum.Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentType(enum.Enum):
    """Agent type enum."""
    ARCHITECT = "architect"
    PLANNER = "planner"
    CODE_EXECUTOR = "code_executor"
    CLOUD_DEPLOYER = "cloud_deployer"
    QUALITY_ASSURANCE = "quality_assurance"
    SECURITY_AUDITOR = "security_auditor"
    DATA_ANALYST = "data_analyst"
    DOCUMENTATION = "documentation"


class ProjectStatus(enum.Enum):
    """Project status enum."""
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    preferences = Column(JSONB, default=dict)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.creator_id")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}', role='{self.role.value}')>"


class Project(Base):
    """Project model for organizing work."""
    
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ProjectStatus), nullable=False, default=ProjectStatus.DRAFT)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Project configuration and metadata
    config = Column(JSONB, default=dict)
    project_metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    crew_sessions = relationship("CrewSession", back_populates="project")
    
    def __repr__(self):
        return f"<Project(id='{self.id}', name='{self.name}', status='{self.status.value}')>"


class Task(Base):
    """Task model for individual work items."""
    
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    
    # Foreign keys
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    
    # Task details
    requirements = Column(JSONB, default=dict)
    constraints = Column(JSONB, default=dict)
    deliverables = Column(JSONB, default=list)
    dependencies = Column(JSONB, default=list)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0, nullable=False)
    estimated_effort = Column(Float, nullable=True)  # hours
    actual_effort = Column(Float, nullable=True)  # hours
    
    # Timestamps
    due_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    parent_task = relationship("Task", remote_side=[id])
    subtasks = relationship("Task", back_populates="parent_task")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_project_status', 'project_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Task(id='{self.id}', title='{self.title}', status='{self.status.value}')>"


class Agent(Base):
    """Agent model for AI agents."""
    
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Agent configuration
    config = Column(JSONB, default=dict)
    capabilities = Column(JSONB, default=list)
    tools = Column(JSONB, default=list)
    
    # Status and performance
    is_active = Column(Boolean, default=True, nullable=False)
    performance_metrics = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, nullable=True)
    
    # Relationships
    executions = relationship("TaskExecution", back_populates="agent")
    crew_memberships = relationship("CrewSessionAgent", back_populates="agent")
    
    def __repr__(self):
        return f"<Agent(id='{self.id}', name='{self.name}', type='{self.agent_type.value}')>"


class CrewSession(Base):
    """CrewAI session model for orchestrated agent collaboration."""
    
    __tablename__ = "crew_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Session status and configuration
    status = Column(String(50), nullable=False, default="pending")
    config = Column(JSONB, default=dict)
    goals = Column(JSONB, default=list)
    
    # Performance metrics
    metrics = Column(JSONB, default=dict)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="crew_sessions")
    agents = relationship("CrewSessionAgent", back_populates="crew_session", cascade="all, delete-orphan")
    executions = relationship("TaskExecution", back_populates="crew_session")
    
    def __repr__(self):
        return f"<CrewSession(id='{self.id}', name='{self.name}', status='{self.status}')>"


class CrewSessionAgent(Base):
    """Many-to-many relationship table for crew sessions and agents."""
    
    __tablename__ = "crew_session_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_session_id = Column(UUID(as_uuid=True), ForeignKey("crew_sessions.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # Role-specific configuration
    role = Column(String(255), nullable=True)
    config = Column(JSONB, default=dict)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    crew_session = relationship("CrewSession", back_populates="agents")
    agent = relationship("Agent", back_populates="crew_memberships")
    
    __table_args__ = (
        UniqueConstraint('crew_session_id', 'agent_id', name='uq_crew_session_agent'),
    )


class TaskExecution(Base):
    """Task execution model for tracking agent task execution."""
    
    __tablename__ = "task_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    crew_session_id = Column(UUID(as_uuid=True), ForeignKey("crew_sessions.id"), nullable=True)
    
    # Execution details
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    error_details = Column(JSONB, nullable=True)
    
    # Performance metrics
    execution_time = Column(Float, nullable=True)  # seconds
    tokens_used = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="executions")
    agent = relationship("Agent", back_populates="executions")
    crew_session = relationship("CrewSession", back_populates="executions")
    
    __table_args__ = (
        Index('idx_execution_status_agent', 'status', 'agent_id'),
        Index('idx_execution_task_status', 'task_id', 'status'),
    )
    
    def __repr__(self):
        return f"<TaskExecution(id='{self.id}', task_id='{self.task_id}', status='{self.status.value}')>"


class AuditLog(Base):
    """Audit log model for tracking system events."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Event details
    event_type = Column(String(255), nullable=False)
    resource_type = Column(String(255), nullable=False)
    resource_id = Column(String(255), nullable=True)
    action = Column(String(255), nullable=False)
    
    # Event data
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    event_metadata = Column(JSONB, default=dict)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id='{self.id}', event_type='{self.event_type}', action='{self.action}')>"
