#!/usr/bin/env python3
"""
Database management CLI for AZROI Autonomous AI Architect
"""

import asyncio
import click
import logging
from pathlib import Path
from database.connection import DatabaseManager, DatabaseInitializer
from config.settings import get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Database management commands for AZROI."""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Force recreate tables (drops existing tables)')
def init():
    """Initialize the database with tables and default data."""
    async def _init():
        try:
            config = get_config()
            logger.info(f"Initializing database: {config.database.database}")
            
            manager = DatabaseManager()
            manager.initialize()
            
            if click.confirm('This will create database tables. Continue?'):
                await manager.create_tables()
                await DatabaseInitializer._create_default_data()
                logger.info("Database initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_init())


@cli.command()
@click.option('--force', is_flag=True, help='Force drop without confirmation')
def drop():
    """Drop all database tables."""
    async def _drop():
        try:
            config = get_config()
            logger.info(f"Dropping tables from database: {config.database.database}")
            
            if not click.confirm('This will DROP ALL TABLES and data. Are you sure?'):
                return
            
            manager = DatabaseManager()
            manager.initialize()
            await manager.drop_tables()
            logger.info("Database tables dropped successfully!")
            
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_drop())


@cli.command()
def status():
    """Check database connection status."""
    async def _status():
        try:
            config = get_config()
            manager = DatabaseManager()
            manager.initialize()
            
            healthy = await manager.health_check()
            
            click.echo(f"Database: {config.database.database}")
            click.echo(f"Host: {config.database.host}:{config.database.port}")
            click.echo(f"Status: {'✓ Connected' if healthy else '✗ Connection failed'}")
            
            if not healthy:
                raise click.ClickException("Database connection failed")
                
        except Exception as e:
            logger.error(f"Database status check failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_status())


@cli.command()
def create_migration():
    """Create a new Alembic migration."""
    try:
        import subprocess
        result = subprocess.run(
            ['alembic', 'revision', '--autogenerate', '-m', 'Auto migration'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            click.echo("Migration created successfully!")
            click.echo(result.stdout)
        else:
            click.echo("Failed to create migration:")
            click.echo(result.stderr)
            raise click.ClickException("Migration creation failed")
            
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise click.ClickException(str(e))


@cli.command()
def migrate():
    """Run pending Alembic migrations."""
    try:
        import subprocess
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            click.echo("Migrations applied successfully!")
            click.echo(result.stdout)
        else:
            click.echo("Failed to apply migrations:")
            click.echo(result.stderr)
            raise click.ClickException("Migration failed")
            
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise click.ClickException(str(e))


@cli.command()
def seed():
    """Seed database with sample data."""
    async def _seed():
        try:
            from database.models import User, Project, Task, Agent, UserRole, AgentType, ProjectStatus, TaskStatus, TaskPriority
            from database.connection import get_db_manager
            from security.auth import PasswordManager
            import uuid
            from datetime import datetime, timedelta
            
            manager = get_db_manager()
            password_manager = PasswordManager()
            
            logger.info("Seeding database with sample data...")
            
            if manager._async_session_factory:
                async with manager.get_async_session() as session:
                    await _create_sample_data_async(session, password_manager)
            else:
                with manager.get_session() as session:
                    _create_sample_data_sync(session, password_manager)
            
            logger.info("Sample data created successfully!")
            
        except Exception as e:
            logger.error(f"Failed to seed database: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_seed())


async def _create_sample_data_async(session, password_manager):
    """Create sample data using async session."""
    from database.models import User, Project, Task, Agent, UserRole, AgentType, ProjectStatus, TaskStatus, TaskPriority
    from sqlalchemy import select
    import uuid
    from datetime import datetime, timedelta
    
    # Create sample users
    users_data = [
        {
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "role": UserRole.USER,
            "password": "password123"
        },
        {
            "username": "jane_smith",
            "email": "jane@example.com", 
            "full_name": "Jane Smith",
            "role": UserRole.USER,
            "password": "password123"
        }
    ]
    
    created_users = []
    for user_data in users_data:
        password = user_data.pop("password")
        result = await session.execute(select(User).where(User.username == user_data["username"]))
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            user_data["hashed_password"] = password_manager.hash_password(password)
            user_data["is_active"] = True
            user_data["is_verified"] = True
            user = User(**user_data)
            session.add(user)
            await session.flush()
            created_users.append(user)
    
    # Create sample project
    if created_users:
        project = Project(
            name="AI Web Application",
            description="Build an AI-powered web application with modern architecture",
            status=ProjectStatus.ACTIVE,
            owner_id=created_users[0].id,
            start_date=datetime.utcnow(),
            config={
                "technology_stack": ["React", "FastAPI", "PostgreSQL"],
                "deployment_target": "cloud"
            }
        )
        session.add(project)
        await session.flush()
        
        # Create sample tasks
        tasks_data = [
            {
                "title": "Design System Architecture",
                "description": "Create comprehensive system architecture design",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "project_id": project.id,
                "creator_id": created_users[0].id,
                "assignee_id": created_users[0].id,
                "due_date": datetime.utcnow() + timedelta(days=7)
            },
            {
                "title": "Implement Backend API",
                "description": "Develop REST API endpoints using FastAPI",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "project_id": project.id,
                "creator_id": created_users[0].id,
                "due_date": datetime.utcnow() + timedelta(days=14)
            },
            {
                "title": "Build Frontend Interface",
                "description": "Create React-based user interface",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "project_id": project.id,
                "creator_id": created_users[0].id,
                "due_date": datetime.utcnow() + timedelta(days=21)
            }
        ]
        
        for task_data in tasks_data:
            task = Task(**task_data)
            session.add(task)
    
    await session.commit()


def _create_sample_data_sync(session, password_manager):
    """Create sample data using sync session."""
    from database.models import User, Project, Task, Agent, UserRole, AgentType, ProjectStatus, TaskStatus, TaskPriority
    import uuid
    from datetime import datetime, timedelta
    
    # Create sample users
    users_data = [
        {
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "role": UserRole.USER,
            "password": "password123"
        },
        {
            "username": "jane_smith",
            "email": "jane@example.com",
            "full_name": "Jane Smith", 
            "role": UserRole.USER,
            "password": "password123"
        }
    ]
    
    created_users = []
    for user_data in users_data:
        password = user_data.pop("password")
        existing_user = session.query(User).filter_by(username=user_data["username"]).first()
        
        if not existing_user:
            user_data["hashed_password"] = password_manager.hash_password(password)
            user_data["is_active"] = True
            user_data["is_verified"] = True
            user = User(**user_data)
            session.add(user)
            session.flush()
            created_users.append(user)
    
    # Create sample project
    if created_users:
        project = Project(
            name="AI Web Application",
            description="Build an AI-powered web application with modern architecture",
            status=ProjectStatus.ACTIVE,
            owner_id=created_users[0].id,
            start_date=datetime.utcnow(),
            config={
                "technology_stack": ["React", "FastAPI", "PostgreSQL"],
                "deployment_target": "cloud"
            }
        )
        session.add(project)
        session.flush()
        
        # Create sample tasks
        tasks_data = [
            {
                "title": "Design System Architecture",
                "description": "Create comprehensive system architecture design",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "project_id": project.id,
                "creator_id": created_users[0].id,
                "assignee_id": created_users[0].id,
                "due_date": datetime.utcnow() + timedelta(days=7)
            },
            {
                "title": "Implement Backend API",
                "description": "Develop REST API endpoints using FastAPI",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "project_id": project.id,
                "creator_id": created_users[0].id,
                "due_date": datetime.utcnow() + timedelta(days=14)
            },
            {
                "title": "Build Frontend Interface",
                "description": "Create React-based user interface",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "project_id": project.id,
                "creator_id": created_users[0].id,
                "due_date": datetime.utcnow() + timedelta(days=21)
            }
        ]
        
        for task_data in tasks_data:
            task = Task(**task_data)
            session.add(task)
    
    session.commit()


if __name__ == '__main__':
    cli()
