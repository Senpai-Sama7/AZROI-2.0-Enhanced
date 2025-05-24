"""
Repository pattern implementation for database operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Type, TypeVar, Generic
from uuid import UUID
from sqlalchemy import and_, or_, desc, asc, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy.exc import IntegrityError

from .models import (
    Base, User, Project, Task, Agent, CrewSession, 
    TaskExecution, AuditLog, UserRole, TaskStatus, 
    TaskPriority, AgentType, ProjectStatus
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, model: Type[T], session: Session = None, async_session: AsyncSession = None):
        self.model = model
        self.session = session
        self.async_session = async_session
    
    async def create(self, **kwargs) -> T:
        """Create a new entity."""
        try:
            entity = self.model(**kwargs)
            
            if self.async_session:
                self.async_session.add(entity)
                await self.async_session.flush()
                await self.async_session.refresh(entity)
            else:
                self.session.add(entity)
                self.session.flush()
                self.session.refresh(entity)
            
            return entity
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise
    
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(self.model).where(self.model.id == entity_id)
                )
                return result.scalar_one_or_none()
            else:
                return self.session.query(self.model).filter(self.model.id == entity_id).first()
                
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by ID {entity_id}: {e}")
            raise
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(self.model).limit(limit).offset(offset)
                )
                return result.scalars().all()
            else:
                return self.session.query(self.model).limit(limit).offset(offset).all()
                
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise
    
    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    update(self.model)
                    .where(self.model.id == entity_id)
                    .values(**kwargs)
                    .returning(self.model)
                )
                entity = result.scalar_one_or_none()
                if entity:
                    await self.async_session.refresh(entity)
                return entity
            else:
                entity = self.session.query(self.model).filter(self.model.id == entity_id).first()
                if entity:
                    for key, value in kwargs.items():
                        setattr(entity, key, value)
                    self.session.flush()
                    self.session.refresh(entity)
                return entity
                
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__} {entity_id}: {e}")
            raise
    
    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    delete(self.model).where(self.model.id == entity_id)
                )
                return result.rowcount > 0
            else:
                entity = self.session.query(self.model).filter(self.model.id == entity_id).first()
                if entity:
                    self.session.delete(entity)
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__} {entity_id}: {e}")
            raise
    
    async def count(self, **filters) -> int:
        """Count entities with optional filters."""
        try:
            query = select(func.count(self.model.id))
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        conditions.append(getattr(self.model, key) == value)
                if conditions:
                    query = query.where(and_(*conditions))
            
            if self.async_session:
                result = await self.async_session.execute(query)
                return result.scalar()
            else:
                result = self.session.execute(query)
                return result.scalar()
                
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(User, session, async_session)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(User).where(User.username == username)
                )
                return result.scalar_one_or_none()
            else:
                return self.session.query(User).filter(User.username == username).first()
                
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(User).where(User.email == email)
                )
                return result.scalar_one_or_none()
            else:
                return self.session.query(User).filter(User.email == email).first()
                
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise
    
    async def get_by_role(self, role: UserRole) -> List[User]:
        """Get users by role."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(User).where(User.role == role)
                )
                return result.scalars().all()
            else:
                return self.session.query(User).filter(User.role == role).all()
                
        except Exception as e:
            logger.error(f"Error getting users by role {role}: {e}")
            raise
    
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        try:
            await self.update(user_id, last_login=datetime.utcnow())
            
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            raise


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(Project, session, async_session)
    
    async def get_by_owner(self, owner_id: UUID) -> List[Project]:
        """Get projects by owner."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(Project)
                    .where(Project.owner_id == owner_id)
                    .options(selectinload(Project.tasks))
                )
                return result.scalars().all()
            else:
                return (self.session.query(Project)
                       .filter(Project.owner_id == owner_id)
                       .options(selectinload(Project.tasks))
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting projects by owner {owner_id}: {e}")
            raise
    
    async def get_by_status(self, status: ProjectStatus) -> List[Project]:
        """Get projects by status."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(Project).where(Project.status == status)
                )
                return result.scalars().all()
            else:
                return self.session.query(Project).filter(Project.status == status).all()
                
        except Exception as e:
            logger.error(f"Error getting projects by status {status}: {e}")
            raise


class TaskRepository(BaseRepository[Task]):
    """Repository for Task operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(Task, session, async_session)
    
    async def get_by_project(self, project_id: UUID) -> List[Task]:
        """Get tasks by project."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(Task)
                    .where(Task.project_id == project_id)
                    .options(selectinload(Task.executions))
                )
                return result.scalars().all()
            else:
                return (self.session.query(Task)
                       .filter(Task.project_id == project_id)
                       .options(selectinload(Task.executions))
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting tasks by project {project_id}: {e}")
            raise
    
    async def get_by_assignee(self, assignee_id: UUID) -> List[Task]:
        """Get tasks by assignee."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(Task).where(Task.assignee_id == assignee_id)
                )
                return result.scalars().all()
            else:
                return self.session.query(Task).filter(Task.assignee_id == assignee_id).all()
                
        except Exception as e:
            logger.error(f"Error getting tasks by assignee {assignee_id}: {e}")
            raise
    
    async def get_by_status_and_priority(self, status: TaskStatus = None, priority: TaskPriority = None) -> List[Task]:
        """Get tasks by status and/or priority."""
        try:
            conditions = []
            if status:
                conditions.append(Task.status == status)
            if priority:
                conditions.append(Task.priority == priority)
            
            query = select(Task)
            if conditions:
                query = query.where(and_(*conditions))
            
            if self.async_session:
                result = await self.async_session.execute(query)
                return result.scalars().all()
            else:
                return self.session.execute(query).scalars().all()
                
        except Exception as e:
            logger.error(f"Error getting tasks by status/priority: {e}")
            raise
    
    async def get_overdue_tasks(self) -> List[Task]:
        """Get overdue tasks."""
        try:
            now = datetime.utcnow()
            query = (select(Task)
                    .where(and_(
                        Task.due_date < now,
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
                    )))
            
            if self.async_session:
                result = await self.async_session.execute(query)
                return result.scalars().all()
            else:
                return self.session.execute(query).scalars().all()
                
        except Exception as e:
            logger.error(f"Error getting overdue tasks: {e}")
            raise


class AgentRepository(BaseRepository[Agent]):
    """Repository for Agent operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(Agent, session, async_session)
    
    async def get_by_type(self, agent_type: AgentType) -> List[Agent]:
        """Get agents by type."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(Agent).where(Agent.agent_type == agent_type)
                )
                return result.scalars().all()
            else:
                return self.session.query(Agent).filter(Agent.agent_type == agent_type).all()
                
        except Exception as e:
            logger.error(f"Error getting agents by type {agent_type}: {e}")
            raise
    
    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(Agent).where(Agent.is_active == True)
                )
                return result.scalars().all()
            else:
                return self.session.query(Agent).filter(Agent.is_active == True).all()
                
        except Exception as e:
            logger.error(f"Error getting active agents: {e}")
            raise
    
    async def update_performance_metrics(self, agent_id: UUID, metrics: Dict[str, Any]) -> None:
        """Update agent performance metrics."""
        try:
            await self.update(agent_id, 
                            performance_metrics=metrics, 
                            last_active=datetime.utcnow())
            
        except Exception as e:
            logger.error(f"Error updating agent metrics {agent_id}: {e}")
            raise


class CrewSessionRepository(BaseRepository[CrewSession]):
    """Repository for CrewSession operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(CrewSession, session, async_session)
    
    async def get_by_project(self, project_id: UUID) -> List[CrewSession]:
        """Get crew sessions by project."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(CrewSession)
                    .where(CrewSession.project_id == project_id)
                    .options(selectinload(CrewSession.agents))
                )
                return result.scalars().all()
            else:
                return (self.session.query(CrewSession)
                       .filter(CrewSession.project_id == project_id)
                       .options(selectinload(CrewSession.agents))
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting crew sessions by project {project_id}: {e}")
            raise
    
    async def get_active_sessions(self) -> List[CrewSession]:
        """Get active crew sessions."""
        try:
            active_statuses = ["pending", "running", "paused"]
            
            if self.async_session:
                result = await self.async_session.execute(
                    select(CrewSession).where(CrewSession.status.in_(active_statuses))
                )
                return result.scalars().all()
            else:
                return self.session.query(CrewSession).filter(
                    CrewSession.status.in_(active_statuses)
                ).all()
                
        except Exception as e:
            logger.error(f"Error getting active crew sessions: {e}")
            raise


class TaskExecutionRepository(BaseRepository[TaskExecution]):
    """Repository for TaskExecution operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(TaskExecution, session, async_session)
    
    async def get_by_task(self, task_id: UUID) -> List[TaskExecution]:
        """Get executions by task."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(TaskExecution)
                    .where(TaskExecution.task_id == task_id)
                    .options(selectinload(TaskExecution.agent))
                )
                return result.scalars().all()
            else:
                return (self.session.query(TaskExecution)
                       .filter(TaskExecution.task_id == task_id)
                       .options(selectinload(TaskExecution.agent))
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting executions by task {task_id}: {e}")
            raise
    
    async def get_by_agent(self, agent_id: UUID) -> List[TaskExecution]:
        """Get executions by agent."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(TaskExecution)
                    .where(TaskExecution.agent_id == agent_id)
                    .options(selectinload(TaskExecution.task))
                )
                return result.scalars().all()
            else:
                return (self.session.query(TaskExecution)
                       .filter(TaskExecution.agent_id == agent_id)
                       .options(selectinload(TaskExecution.task))
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting executions by agent {agent_id}: {e}")
            raise
    
    async def get_execution_metrics(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get execution metrics for a date range."""
        try:
            conditions = []
            if start_date:
                conditions.append(TaskExecution.created_at >= start_date)
            if end_date:
                conditions.append(TaskExecution.created_at <= end_date)
            
            base_query = select(TaskExecution)
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # Get execution counts by status
            status_query = (select(TaskExecution.status, func.count(TaskExecution.id))
                          .group_by(TaskExecution.status))
            if conditions:
                status_query = status_query.where(and_(*conditions))
            
            # Get average execution time
            avg_time_query = select(func.avg(TaskExecution.execution_time))
            if conditions:
                avg_time_query = avg_time_query.where(and_(*conditions))
            
            if self.async_session:
                status_result = await self.async_session.execute(status_query)
                avg_time_result = await self.async_session.execute(avg_time_query)
            else:
                status_result = self.session.execute(status_query)
                avg_time_result = self.session.execute(avg_time_query)
            
            status_counts = dict(status_result.fetchall())
            avg_execution_time = avg_time_result.scalar()
            
            return {
                "status_counts": status_counts,
                "average_execution_time": avg_execution_time,
                "total_executions": sum(status_counts.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting execution metrics: {e}")
            raise


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog operations."""
    
    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        super().__init__(AuditLog, session, async_session)
    
    async def get_by_user(self, user_id: UUID, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by user."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(AuditLog)
                    .where(AuditLog.user_id == user_id)
                    .order_by(desc(AuditLog.created_at))
                    .limit(limit)
                )
                return result.scalars().all()
            else:
                return (self.session.query(AuditLog)
                       .filter(AuditLog.user_id == user_id)
                       .order_by(desc(AuditLog.created_at))
                       .limit(limit)
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting audit logs by user {user_id}: {e}")
            raise
    
    async def get_by_resource(self, resource_type: str, resource_id: str) -> List[AuditLog]:
        """Get audit logs by resource."""
        try:
            if self.async_session:
                result = await self.async_session.execute(
                    select(AuditLog)
                    .where(and_(
                        AuditLog.resource_type == resource_type,
                        AuditLog.resource_id == resource_id
                    ))
                    .order_by(desc(AuditLog.created_at))
                )
                return result.scalars().all()
            else:
                return (self.session.query(AuditLog)
                       .filter(and_(
                           AuditLog.resource_type == resource_type,
                           AuditLog.resource_id == resource_id
                       ))
                       .order_by(desc(AuditLog.created_at))
                       .all())
                
        except Exception as e:
            logger.error(f"Error getting audit logs by resource {resource_type}/{resource_id}: {e}")
            raise
    
    async def log_event(self, user_id: UUID, event_type: str, resource_type: str, 
                       resource_id: str, action: str, old_values: Dict = None, 
                       new_values: Dict = None, metadata: Dict = None, 
                       ip_address: str = None, user_agent: str = None) -> AuditLog:
        """Create a new audit log entry."""
        try:
            audit_log = await self.create(
                user_id=user_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                old_values=old_values or {},
                new_values=new_values or {},
                metadata=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
            raise
