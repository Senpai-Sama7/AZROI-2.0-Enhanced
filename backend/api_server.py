#!/usr/bin/env python3
"""
FastAPI Backend for Autonomous AI Architect System
Production-ready API endpoints with CrewAI integration.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

# Import our enhanced orchestrator
try:
    from .core_orchestration.agent_orchestrator_enhanced import (
        EnhancedAgentOrchestrator, 
        AgentType, 
        TaskPriority, 
        CrewTask,
        CrewSession,
        AgentInstance
    )
    from .database import (
        get_db_session, 
        get_async_db_session,
        UserRepository,
        ProjectRepository,
        TaskRepository,
        AgentRepository,
        CrewSessionRepository,
        TaskExecutionRepository,
        AuditLogRepository
    )
    from .database.models import User as DBUser, Project, Task, Agent
    from .security import AuthManager, get_current_user, require_role
    from .config import get_config
    from .app_logging import get_logger
    from .monitoring import MonitoringManager
except ImportError:
    try:
        from core_orchestration.agent_orchestrator_enhanced import (
            EnhancedAgentOrchestrator, 
            AgentType, 
            TaskPriority, 
            CrewTask,
            CrewSession,
            AgentInstance
        )
        from database import (
            get_db_session, 
            get_async_db_session,
            UserRepository,
            ProjectRepository,
            TaskRepository,
            AgentRepository,
            CrewSessionRepository,
            TaskExecutionRepository,
            AuditLogRepository
        )
        from database.models import User as DBUser, Project, Task, Agent
        from security import AuthManager, get_current_user, require_role
        from config import get_config
        from app_logging import get_logger
        from monitoring import MonitoringManager
    except ImportError:
        # Fallback for testing
        from agent_orchestrator_enhanced import (
            EnhancedAgentOrchestrator, 
            AgentType, 
            TaskPriority, 
            CrewTask,
            CrewSession,
            AgentInstance
        )
        # Mock imports for testing
        get_db_session = None
        get_async_db_session = None
        AuthManager = None
        get_current_user = None
        require_role = None
        get_config = None
        
        # Create a mock logger class
        class MockLogger:
            def info(self, *args, **kwargs): pass
            def error(self, *args, **kwargs): pass
            def warning(self, *args, **kwargs): pass
            def debug(self, *args, **kwargs): pass
        
        def get_logger(name):
            return MockLogger()
        
        MonitoringManager = None
        DBUser = None

# Configure logging
try:
    logger = get_logger(__name__)
except:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

# Global instances
orchestrator: Optional[EnhancedAgentOrchestrator] = None
try:
    auth_manager: Optional[AuthManager] = None
    monitoring_manager: Optional[MonitoringManager] = None
except:
    auth_manager = None
    monitoring_manager = None

# Pydantic models for API
class GoalRequest(BaseModel):
    goal: str = Field(..., description="The goal to process")
    goal_id: Optional[str] = Field(None, description="Optional goal ID")
    use_crewai: bool = Field(True, description="Whether to use CrewAI processing")

class TaskRequest(BaseModel):
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    agent_type: str = Field(..., description="Agent type for the task")
    priority: str = Field("medium", description="Task priority (low, medium, high, critical)")
    expected_output: str = Field("", description="Expected task output")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class CrewSessionRequest(BaseModel):
    name: str = Field(..., description="Session name")
    description: str = Field(..., description="Session description")
    agent_types: List[str] = Field(..., description="List of agent types for the session")
    process_type: str = Field("sequential", description="Process type (sequential or hierarchical)")

class AgentRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent to create")
    goal_context: str = Field("", description="Optional goal context for the agent")
    custom_tools: Optional[List[str]] = Field(None, description="Custom tools for the agent")

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# Startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global orchestrator
    
    # Startup
    try:
        logger.info("Starting Autonomous AI Architect API...")
        orchestrator = EnhancedAgentOrchestrator()
        await orchestrator.initialize()
        logger.info("Orchestrator initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise
    finally:
        # Shutdown
        if orchestrator:
            await orchestrator.shutdown()
        logger.info("API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Autonomous AI Architect API",
    description="Production-ready API for autonomous AI architecture tasks with CrewAI integration",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")
            
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: str):
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

manager = ConnectionManager()

# Dependency to get orchestrator
def get_orchestrator() -> EnhancedAgentOrchestrator:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orchestrator

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "orchestrator_available": orchestrator is not None
    }

# Goal processing endpoints
@app.post("/api/goals/process")
async def process_goal(
    request: GoalRequest,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Process a goal using the orchestrator"""
    try:
        goal_id = request.goal_id or str(uuid.uuid4())
        
        logger.info(f"Processing goal: {request.goal} (ID: {goal_id})")
        
        # Start processing in background
        async def goal_processor():
            results = []
            try:
                if request.use_crewai:
                    async for update in orch.process_goal_with_crewai(request.goal, goal_id):
                        results.append(update)
                        # Broadcast to WebSocket clients
                        await manager.broadcast(json.dumps(update))
                else:
                    async for update in orch.process_goal(request.goal, goal_id):
                        results.append(update)
                        await manager.broadcast(json.dumps(update))
            except Exception as e:
                error_update = {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "error",
                    "error": str(e)
                }
                results.append(error_update)
                await manager.broadcast(json.dumps(error_update))
            
            return results
        
        # Start background task
        asyncio.create_task(goal_processor())
        
        return {
            "goal_id": goal_id,
            "status": "started",
            "message": "Goal processing started",
            "use_crewai": request.use_crewai
        }
        
    except Exception as e:
        logger.error(f"Failed to process goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/goals/{goal_id}/stream")
async def stream_goal_progress(
    goal_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Stream goal processing progress"""
    async def generate():
        try:
            async for update in orch.process_goal_with_crewai("", goal_id):
                yield f"data: {json.dumps(update)}\n\n"
        except Exception as e:
            error_data = {"error": str(e), "goal_id": goal_id}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

# Agent management endpoints
@app.post("/api/agents/create")
async def create_agent(
    request: AgentRequest,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Create a new agent instance"""
    try:
        agent_type = AgentType(request.agent_type)
        agent = await orch.create_agent_instance(
            agent_type=agent_type,
            goal_context=request.goal_context,
            custom_tools=request.custom_tools
        )
        
        return {
            "id": agent.id,
            "name": agent.name,
            "type": agent.agent_type.value,
            "status": agent.status,
            "capabilities": agent.capabilities,
            "tools": agent.tools,
            "created_at": agent.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {request.agent_type}")
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents")
async def list_agents(
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """List all active agents"""
    try:
        agents = await orch.get_active_agents()
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/instances")
async def list_agent_instances(
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """List all agent instances"""
    try:
        instances = []
        for agent in orch.agent_instances.values():
            instances.append({
                "id": agent.id,
                "name": agent.name,
                "type": agent.agent_type.value,
                "status": agent.status,
                "current_task": agent.current_task,
                "progress": agent.progress,
                "capabilities": agent.capabilities,
                "tools": agent.tools,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at,
                "last_active": agent.last_active
            })
        return {"agent_instances": instances}
    except Exception as e:
        logger.error(f"Failed to list agent instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/agents/{agent_id}")
async def stop_agent(
    agent_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Stop a specific agent"""
    try:
        success = await orch.stop_agent(agent_id)
        if success:
            return {"message": f"Agent {agent_id} stopped successfully"}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# CrewAI Agent management endpoints
@app.get("/api/crew/agents/{agent_id}")
async def get_crew_agent(
    agent_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get details of a specific agent"""
    try:
        agent = await orch.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/agents/{agent_id}/pause")
async def pause_crew_agent(
    agent_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Pause a specific agent"""
    try:
        success = await orch.pause_agent(agent_id)
        if success:
            return {"agent_id": agent_id, "status": "paused"}
        else:
            raise HTTPException(status_code=400, detail="Failed to pause agent")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/agents/{agent_id}/resume")
async def resume_crew_agent(
    agent_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Resume a paused agent"""
    try:
        success = await orch.resume_agent(agent_id)
        if success:
            return {"agent_id": agent_id, "status": "active"}
        else:
            raise HTTPException(status_code=400, detail="Failed to resume agent")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/agents/{agent_id}/reset")
async def reset_crew_agent(
    agent_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Reset an agent's state"""
    try:
        success = await orch.reset_agent(agent_id)
        if success:
            return {"agent_id": agent_id, "status": "reset"}
        else:
            raise HTTPException(status_code=400, detail="Failed to reset agent")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Task management endpoints
@app.post("/api/tasks/create")
async def create_task(
    request: TaskRequest,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Create a new task"""
    try:
        agent_type = AgentType(request.agent_type)
        priority = TaskPriority[request.priority.upper()]
        
        task = await orch.create_task(
            title=request.title,
            description=request.description,
            agent_type=agent_type,
            dependencies=request.dependencies,
            priority=priority,
            expected_output=request.expected_output,
            metadata=request.metadata
        )
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "agent_type": task.agent_type.value,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/queue")
async def get_task_queue(
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get the current task queue"""
    try:
        tasks = []
        for task in orch.task_queue:
            tasks.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "agent_type": task.agent_type.value,
                "status": task.status.value,
                "priority": task.priority.value,
                "progress": task.progress,
                "created_at": task.created_at,
                "updated_at": task.updated_at
            })
        return {"tasks": tasks, "count": len(tasks)}
    except Exception as e:
        logger.error(f"Failed to get task queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# CrewAI Task management endpoints
@app.get("/api/crew/tasks/{task_id}")
async def get_crew_task(
    task_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get details of a specific task"""
    try:
        task = await orch.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/tasks/{task_id}/retry")
async def retry_crew_task(
    task_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Retry a failed task"""
    try:
        success = await orch.retry_task(task_id)
        if success:
            return {"task_id": task_id, "status": "retrying"}
        else:
            raise HTTPException(status_code=400, detail="Failed to retry task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/tasks/{task_id}/skip")
async def skip_crew_task(
    task_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Skip a task"""
    try:
        success = await orch.skip_task(task_id)
        if success:
            return {"task_id": task_id, "status": "skipped"}
        else:
            raise HTTPException(status_code=400, detail="Failed to skip task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to skip task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/tasks/{task_id}/prioritize")
async def prioritize_crew_task(
    task_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Prioritize a task"""
    try:
        success = await orch.prioritize_task(task_id)
        if success:
            return {"task_id": task_id, "status": "prioritized"}
        else:
            raise HTTPException(status_code=400, detail="Failed to prioritize task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to prioritize task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# CrewAI Task execution endpoints
@app.get("/api/crew/executions/{execution_id}")
async def get_task_execution(
    execution_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get details of a task execution"""
    try:
        execution = await orch.get_task_execution(execution_id)
        if execution is None:
            raise HTTPException(status_code=404, detail="Task execution not found")
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# CrewAI session management endpoints
@app.post("/api/crew/sessions")
async def create_crew_session(
    request: CrewSessionRequest,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Create a new crew session"""
    try:
        agent_types = [AgentType(agent_type) for agent_type in request.agent_types]
        
        session = await orch.create_crew_session(
            name=request.name,
            description=request.description,
            agent_types=agent_types,
            process_type=request.process_type
        )
        
        return {
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "status": session.status,
            "process_type": session.process_type,
            "agent_count": len(session.agents),
            "task_count": len(session.tasks)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create crew session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crew/sessions")
async def list_crew_sessions(
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """List all crew sessions"""
    try:
        sessions = []
        for session in orch.crew_sessions.values():
            sessions.append({
                "id": session.id,
                "name": session.name,
                "description": session.description,
                "status": session.status,
                "process_type": session.process_type,
                "agent_count": len(session.agents),
                "task_count": len(session.tasks),
                "started_at": session.started_at,
                "completed_at": session.completed_at
            })
        return sessions
    except Exception as e:
        logger.error(f"Failed to list crew sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crew/sessions/{session_id}")
async def get_crew_session(
    session_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get details of a specific crew session"""
    try:
        status = await orch.get_session_status(session_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Crew session not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get crew session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/sessions/{session_id}/start")
async def start_crew_session(
    session_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Start a crew session"""
    try:
        # Start execution in background
        async def session_executor():
            try:
                async for update in orch.execute_crew_session(session_id):
                    await manager.broadcast(json.dumps(update))
            except Exception as e:
                error_update = {
                    "type": "crew_session_update",
                    "session_id": session_id,
                    "status": "failed",
                    "error": str(e)
                }
                await manager.broadcast(json.dumps(error_update))
        
        asyncio.create_task(session_executor())
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": "Crew session execution started"
        }
    except Exception as e:
        logger.error(f"Failed to start crew session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/sessions/{session_id}/pause")
async def pause_crew_session(
    session_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Pause a crew session"""
    try:
        success = await orch.pause_crew_session(session_id)
        if success:
            return {"session_id": session_id, "status": "paused"}
        else:
            raise HTTPException(status_code=400, detail="Failed to pause session")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause crew session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/sessions/{session_id}/stop")
async def stop_crew_session(
    session_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Stop a crew session"""
    try:
        success = await orch.stop_crew_session(session_id)
        if success:
            return {"session_id": session_id, "status": "stopped"}
        else:
            raise HTTPException(status_code=400, detail="Failed to stop session")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop crew session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crew/sessions/{session_id}/metrics")
async def get_crew_session_metrics(
    session_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get metrics for a crew session"""
    try:
        metrics = await orch.get_session_metrics(session_id)
        if metrics is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crew/sessions/{session_id}/collaborations")
async def get_session_collaborations(
    session_id: str,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get agent collaborations for a session"""
    try:
        collaborations = await orch.get_session_collaborations(session_id)
        return collaborations or []
    except Exception as e:
        logger.error(f"Failed to get session collaborations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crew/sessions/{session_id}/tasks")
async def add_task_to_session(
    session_id: str,
    request: TaskRequest,
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Add a task to a crew session"""
    try:
        agent_type = AgentType(request.agent_type)
        priority = TaskPriority[request.priority.upper()]
        
        task = CrewTask(
            id=str(uuid.uuid4()),
            title=request.title,
            description=request.description,
            agent_type=agent_type,
            priority=priority,
            expected_output=request.expected_output,
            dependencies=request.dependencies,
            metadata=request.metadata
        )
        
        success = await orch.add_task_to_session(session_id, task)
        if success:
            return {
                "message": "Task added to session successfully",
                "task_id": task.id,
                "session_id": session_id
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add task to session")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add task to session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Metrics and monitoring endpoints
@app.get("/api/metrics")
async def get_metrics(
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Get orchestrator execution metrics"""
    try:
        metrics = await orch.get_execution_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Utility endpoints
@app.post("/api/cleanup")
async def cleanup_resources(
    orch: EnhancedAgentOrchestrator = Depends(get_orchestrator)
):
    """Clean up completed tasks and sessions"""
    try:
        await orch.cleanup_resources()
        await orch.cleanup_completed_agents()
        return {"message": "Resource cleanup completed successfully"}
    except Exception as e:
        logger.error(f"Failed to cleanup resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent-types")
async def get_agent_types():
    """Get available agent types"""
    return {
        "agent_types": [
            {
                "value": agent_type.value,
                "name": agent_type.value.replace("_", " ").title()
            }
            for agent_type in AgentType
        ]
    }

@app.get("/api/task-priorities")
async def get_task_priorities():
    """Get available task priorities"""
    return {
        "priorities": [
            {
                "value": priority.name.lower(),
                "name": priority.name.title(),
                "level": priority.value
            }
            for priority in TaskPriority
        ]
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo received message (can be used for heartbeat)
            message = {
                "type": "echo",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            await manager.send_personal_message(json.dumps(message), client_id)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return ErrorResponse(
        error=exc.detail,
        detail=f"HTTP {exc.status_code}",
        timestamp=datetime.utcnow().isoformat()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        error="Internal server error",
        detail=str(exc),
        timestamp=datetime.utcnow().isoformat()
    )

# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
