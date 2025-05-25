#!/usr/bin/env python3
"""
Enhanced main FastAPI application for AZROI Autonomous AI Architect.
Production-ready implementation with comprehensive monitoring, security, and observability.
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError
import aioredis
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Import core components
from backend.core_orchestration.config_loader import ConfigLoader
from backend.core_orchestration.agent_orchestrator import AgentOrchestrator
from backend.core_orchestration.agent_orchestrator_enhanced import AgentOrchestratorEnhanced
from backend.core_orchestration.llm_router import LLMRouter
from backend.core_orchestration.monitoring_system import MonitoringSystem

# Import production components
from backend.config.production_config import ConfigurationManager
from backend.monitoring import (
    setup_monitoring, setup_logging, health_endpoint, metrics_endpoint,
    MonitoringMiddleware, performance_logger, agent_logger
)
from backend.security.auth import AuthenticationManager, get_current_user
from backend.database.repositories import SessionRepository, AnalysisRepository

# Configure enhanced logging
from backend.monitoring.logging_config import setup_logging

# Load configuration
config_manager = ConfigurationManager()
config = config_manager.get_config()

# Set up logging with configuration
setup_logging(config.to_dict(), config.logging.level)
logger = logging.getLogger('azroi.main')

# Security
security = HTTPBearer()
auth_manager = AuthenticationManager(config)

# Enhanced Pydantic models for API
class ArchitectGoalRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000, description="The comprehensive goal description")
    priority: str = Field(default="medium", regex="^(low|medium|high|critical)$")
    target_platform: Optional[str] = Field(default="azure", regex="^(azure|gcp|aws|hybrid)$")
    complexity_level: Optional[str] = Field(default="medium", regex="^(simple|medium|complex|enterprise)$")
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict)
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
class ArchitectGoal(BaseModel):
    id: str
    text: str
    priority: str
    target_platform: str
    complexity_level: str
    status: str = "pending"
    analysis: Optional[Dict[str, Any]] = None
    architecture_plan: Optional[Dict[str, Any]] = None
    implementation_plan: Optional[Dict[str, Any]] = None
    submitTime: str
    completionTime: Optional[str] = None
    processingError: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agents_involved: List[str] = Field(default_factory=list)
    execution_metrics: Optional[Dict[str, Any]] = None

class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates"""
    default_llm_model_backend: Optional[str] = None
    log_level: Optional[str] = Field(None, regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_concurrent_agents: Optional[int] = Field(None, ge=1, le=20)
    ai_agent_config: Optional[Dict[str, Any]] = None
    
class SystemStatusResponse(BaseModel):
    """System status response model"""
    status: str
    timestamp: str
    version: str
    environment: str
    active_sessions: int
    agent_status: Dict[str, Any]
    system_metrics: Dict[str, Any]

class AgentExecutionRequest(BaseModel):
    """Request model for direct agent execution"""
    agent_type: str = Field(..., regex="^(architect|code_generator|infrastructure|qa|security|performance|documentation|deployment)$")
    task_description: str = Field(..., min_length=10, max_length=2000)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_id: Optional[str] = None

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting AZROI Autonomous AI Architect application")
    
    # Initialize core components
    config_loader = ConfigLoader()
    llm_router = LLMRouter(config_loader)
    monitoring_system = MonitoringSystem()
    
    # Initialize enhanced orchestrator
    orchestrator = AgentOrchestratorEnhanced(
        config_loader=config_loader,
        llm_router=llm_router,
        monitoring_system=monitoring_system
    )
    
    # Store components in app state
    app.state.config = config
    app.state.config_loader = config_loader
    app.state.orchestrator = orchestrator
    app.state.llm_router = llm_router
    app.state.monitoring_system = monitoring_system
    app.state.auth_manager = auth_manager
    app.state.config_manager = config_manager  # Ensure config_manager is available globally
    
    # Initialize Redis connection
    app.state.redis = aioredis.from_url(config.redis.url)
    
    # Initialize repositories
    app.state.session_repo = SessionRepository()
    app.state.analysis_repo = AnalysisRepository()
    
    # Set up monitoring
    await setup_monitoring(app, config)
    
    # WebSocket connections manager
    app.state.websocket_connections = {}
    
    logger.info("Application startup completed successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down AZROI Autonomous AI Architect application")
    await app.state.redis.close()
    logger.info("Application shutdown completed")

# Create FastAPI application with enhanced configuration
app = FastAPI(
    title="AZROI Autonomous AI Architect",
    description="Production-ready autonomous AI architect system with CrewAI orchestration",
    version="2.0.0",
    docs_url="/api/docs" if config.environment != "production" else None,
    redoc_url="/api/redoc" if config.environment != "production" else None,
    lifespan=lifespan
)

# Security middleware
if config.security.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.security.allowed_hosts
    )

# CORS middleware with production settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler with logging."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.utcnow().isoformat()}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors."""
    logger.warning(
        "Validation error occurred",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Health and monitoring endpoints
@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Comprehensive health check endpoint."""
    return await health_endpoint(app)

@app.get("/health/{service}", tags=["Monitoring"])
async def service_health_check(service: str):
    """Health check for specific service."""
    health_checker = app.state.health_checker
    results = await health_checker.check_health(service)
    
    if service not in results:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    result = results[service]
    status_code = 200 if result.status == "healthy" else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "service": service,
            "status": result.status,
            "timestamp": result.timestamp.isoformat(),
            "response_time_ms": result.response_time_ms,
            "details": result.details,
            "error": result.error
        }
    )

@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()

@app.get("/api/system/status", tags=["System"], response_model=SystemStatusResponse)
async def get_system_status(current_user: dict = Depends(get_current_user)):
    """Get comprehensive system status."""
    try:
        # Get agent status from orchestrator
        orchestrator = app.state.orchestrator
        agent_status = await orchestrator.get_agent_status()
        
        # Get active sessions count
        active_sessions = len(app.state.websocket_connections)
        
        # Get system metrics
        system_metrics = {
            "uptime": datetime.utcnow().isoformat(),
            "active_connections": active_sessions,
            "environment": config.environment
        }
        
        return SystemStatusResponse(
            status="operational",
            timestamp=datetime.utcnow().isoformat(),
            version="2.0.0",
            environment=config.environment,
            active_sessions=active_sessions,
            agent_status=agent_status,
            system_metrics=system_metrics
        )
        
    except Exception as e:
        logger.error("Error getting system status", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get system status")

# Enhanced architect goal endpoints
@app.post("/api/architect-goals", tags=["Architecture"], response_model=ArchitectGoal)
async def create_architect_goal(
    request: ArchitectGoalRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create and process a new architect goal with enhanced workflow."""
    try:
        goal_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        goal = ArchitectGoal(
            id=goal_id,
            text=request.text,
            priority=request.priority,
            target_platform=request.target_platform,
            complexity_level=request.complexity_level,
            status="processing",
            submitTime=datetime.utcnow().isoformat(),
            user_id=current_user.get("user_id"),
            session_id=session_id
        )
        
        # Store in Redis for real-time tracking
        await app.state.redis.set(
            f"goal:{goal_id}",
            goal.json(),
            ex=86400  # 24 hours
        )
        
        # Log goal creation
        logger.info(
            "New architect goal created",
            goal_id=goal_id,
            user_id=current_user.get("user_id"),
            priority=request.priority,
            target_platform=request.target_platform,
            complexity_level=request.complexity_level
        )
        
        # Process asynchronously
        background_tasks.add_task(
            process_architect_goal_enhanced,
            goal,
            request.requirements,
            request.constraints
        )
        
        return goal
        
    except Exception as e:
        logger.error("Error creating architect goal", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create architect goal")

async def process_architect_goal_enhanced(
    goal: ArchitectGoal,
    requirements: Dict[str, Any],
    constraints: Dict[str, Any]
):
    """Enhanced goal processing with comprehensive workflow."""
    start_time = datetime.utcnow()
    
    try:
        orchestrator = app.state.orchestrator
        
        # Create enhanced context
        context = {
            "goal_id": goal.id,
            "session_id": goal.session_id,
            "user_id": goal.user_id,
            "text": goal.text,
            "priority": goal.priority,
            "target_platform": goal.target_platform,
            "complexity_level": goal.complexity_level,
            "requirements": requirements,
            "constraints": constraints,
            "timestamp": start_time.isoformat()
        }
        
        # Update status
        goal.status = "analyzing"
        await update_goal_status(goal)
        
        # Execute comprehensive workflow
        result = await orchestrator.execute_comprehensive_workflow(context)
        
        # Update goal with results
        goal.status = "completed"
        goal.analysis = result.get("analysis")
        goal.architecture_plan = result.get("architecture_plan")
        goal.implementation_plan = result.get("implementation_plan")
        goal.agents_involved = result.get("agents_involved", [])
        goal.completionTime = datetime.utcnow().isoformat()
        
        # Calculate execution metrics
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        goal.execution_metrics = {
            "execution_time_seconds": execution_time,
            "agents_used": len(goal.agents_involved),
            "complexity_score": result.get("complexity_score", 0)
        }
        
        await update_goal_status(goal)
        
        # Log successful completion
        performance_logger.log_agent_execution(
            agent_type="comprehensive_workflow",
            duration=execution_time,
            success=True,
            goal_id=goal.id,
            complexity_level=goal.complexity_level
        )
        
        # Notify via WebSocket
        try:
            await notify_goal_completion(goal)
        except Exception as notify_err:
            logger.warning(f"WebSocket notification failed for goal {goal.id}", error=str(notify_err))
    except Exception as e:
        logger.error(f"Error processing goal {goal.id}", exc_info=True)
        goal.status = "failed"
        goal.processingError = str(e)
        goal.completionTime = datetime.utcnow().isoformat()
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        performance_logger.log_agent_execution(
            agent_type="comprehensive_workflow",
            duration=execution_time,
            success=False,
            goal_id=goal.id,
            error=str(e)
        )
        try:
            await update_goal_status(goal)
        except Exception as update_err:
            logger.warning(f"Failed to update goal status for {goal.id}", error=str(update_err))

async def update_goal_status(goal: ArchitectGoal):
    """Update goal status in Redis and notify WebSocket connections."""
    try:
        # Update in Redis
        await app.state.redis.set(
            f"goal:{goal.id}",
            goal.json(),
            ex=86400
        )
        
        # Notify WebSocket connections
        for connection_id, websocket in app.state.websocket_connections.items():
            try:
                await websocket.send_text(json.dumps({
                    "type": "goal_status_update",
                    "goal_id": goal.id,
                    "status": goal.status,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                logger.warning(f"Failed to notify WebSocket {connection_id}", error=str(e))
                
    except Exception as e:
        logger.error("Error updating goal status", goal_id=goal.id, error=str(e))

async def notify_goal_completion(goal: ArchitectGoal):
    """Notify all WebSocket connections about goal completion."""
    notification = {
        "type": "goal_completed",
        "goal": goal.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    for connection_id, websocket in app.state.websocket_connections.items():
        try:
            await websocket.send_text(json.dumps(notification))
        except Exception as e:
            logger.warning(f"Failed to send completion notification to {connection_id}", error=str(e))

@app.get("/api/architect-goals/{goal_id}", tags=["Architecture"], response_model=ArchitectGoal)
async def get_architect_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get architect goal by ID."""
    try:
        goal_data = await app.state.redis.get(f"goal:{goal_id}")
        if not goal_data:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        goal = ArchitectGoal.parse_raw(goal_data)
        
        # Check user access
        if goal.user_id != current_user.get("user_id") and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return goal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving goal {goal_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve goal")

@app.get("/api/architect-goals", tags=["Architecture"], response_model=List[ArchitectGoal])
async def list_architect_goals(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List architect goals for the current user."""
    try:
        # Get all goal keys for the user
        pattern = "goal:*"
        keys = await app.state.redis.keys(pattern)
        
        goals = []
        for key in keys[offset:offset + limit]:
            goal_data = await app.state.redis.get(key)
            if goal_data:
                goal = ArchitectGoal.parse_raw(goal_data)
                
                # Filter by user and status
                if goal.user_id == current_user.get("user_id") or current_user.get("is_admin", False):
                    if not status or goal.status == status:
                        goals.append(goal)
        
        # Sort by submit time (newest first)
        goals.sort(key=lambda x: x.submitTime, reverse=True)
        
        return goals
        
    except Exception as e:
        logger.error("Error listing architect goals", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list goals")

# Direct agent execution endpoint
@app.post("/api/agents/execute", tags=["Agents"])
async def execute_agent(
    request: AgentExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Execute a specific agent directly."""
    try:
        execution_id = str(uuid.uuid4())
        session_id = request.session_id or str(uuid.uuid4())
        
        context = {
            "execution_id": execution_id,
            "session_id": session_id,
            "user_id": current_user.get("user_id"),
            "task_description": request.task_description,
            "context": request.context,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Execute agent in background
        background_tasks.add_task(
            execute_single_agent,
            request.agent_type,
            context
        )
        
        return {
            "execution_id": execution_id,
            "session_id": session_id,
            "agent_type": request.agent_type,
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error starting agent execution", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start agent execution")

async def execute_single_agent(agent_type: str, context: Dict[str, Any]):
    """Execute a single agent with the given context."""
    start_time = datetime.utcnow()
    
    try:
        orchestrator = app.state.orchestrator
        
        # Log agent start
        agent_logger.log_agent_start(
            agent_id=context["execution_id"],
            agent_type=agent_type,
            task_id=context["session_id"],
            user_id=context["user_id"]
        )
        
        # Execute the agent
        result = await orchestrator.execute_single_agent(agent_type, context)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log successful completion
        agent_logger.log_agent_complete(
            agent_id=context["execution_id"],
            agent_type=agent_type,
            task_id=context["session_id"],
            success=True,
            result_summary=result.get("summary", "")
        )
        
        performance_logger.log_agent_execution(
            agent_type=agent_type,
            duration=execution_time,
            success=True,
            execution_id=context["execution_id"]
        )
        
        # Notify via WebSocket
        try:
            await notify_agent_completion(context["execution_id"], agent_type, result, True)
        except Exception as notify_err:
            logger.warning(f"WebSocket notification failed for agent {context['execution_id']}", error=str(notify_err))
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.error(f"Agent execution failed", agent_type=agent_type, execution_id=context["execution_id"], exc_info=True)
        
        agent_logger.log_agent_error(
            agent_id=context["execution_id"],
            agent_type=agent_type,
            task_id=context["session_id"],
            error=str(e)
        )
        
        performance_logger.log_agent_execution(
            agent_type=agent_type,
            duration=execution_time,
            success=False,
            execution_id=context["execution_id"],
            error=str(e)
        )
        try:
            await notify_agent_completion(context["execution_id"], agent_type, {"error": str(e)}, False)
        except Exception as notify_err:
            logger.warning(f"WebSocket notification failed for agent {context['execution_id']}", error=str(notify_err))

# Configuration management endpoints
@app.post("/api/config/update", tags=["Configuration"])
async def update_system_config(
    config_update: ConfigUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update system configuration (admin only)."""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Update configuration
        config_manager = app.state.config_manager
        await config_manager.update_configuration(config_update.dict(exclude_unset=True))
        
        logger.info("System configuration updated", user_id=current_user.get("user_id"))
        
        return {
            "message": "Configuration updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error updating configuration", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update configuration")

@app.get("/api/config", tags=["Configuration"])
async def get_system_config(current_user: dict = Depends(get_current_user)):
    """Get current system configuration."""
    try:
        config_dict = config.to_dict()
        
        # Remove sensitive information for non-admin users
        if not current_user.get("is_admin", False):
            config_dict = {
                "environment": config_dict.get("environment"),
                "version": "2.0.0",
                "features": config_dict.get("features", {}),
                "ai_agent_config": {
                    "max_concurrent_agents": config_dict.get("ai_agent_config", {}).get("max_concurrent_agents")
                }
            }
        
        return config_dict
        
    except Exception as e:
        logger.error("Error retrieving configuration", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")

# Enhanced WebSocket endpoint with authentication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Enhanced WebSocket endpoint with authentication and real-time updates."""
    try:
        # Authenticate WebSocket connection
        if token:
            try:
                user = await auth_manager.verify_token(token)
            except Exception:
                await websocket.close(code=4001, reason="Authentication failed")
                return
        else:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        app.state.websocket_connections[connection_id] = websocket
        
        logger.info(f"WebSocket connection established", connection_id=connection_id, user_id=user.get("user_id"))
        
        try:
            # Send initial connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
                "user": {
                    "user_id": user.get("user_id"),
                    "username": user.get("username")
                }
            }))
            
            # Keep connection alive and handle messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle different message types
                    await handle_websocket_message(connection_id, message, user)
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from WebSocket {connection_id}")
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection closed", connection_id=connection_id)
        except Exception as e:
            logger.error(f"WebSocket error", connection_id=connection_id, error=str(e))
        finally:
            # Clean up connection
            if connection_id in app.state.websocket_connections:
                del app.state.websocket_connections[connection_id]
    except Exception as e:
        logger.error("WebSocket endpoint error", exc_info=True)
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            pass

async def handle_websocket_message(connection_id: str, message: Dict[str, Any], user: Dict[str, Any]):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    
    try:
        if message_type == "subscribe_to_goal":
            goal_id = message.get("goal_id")
            if goal_id:
                # Subscribe to goal updates
                logger.info(f"WebSocket {connection_id} subscribed to goal {goal_id}")
                
        elif message_type == "pong":
            # Handle ping/pong for keepalive
            pass
            
        elif message_type == "request_status":
            # Send current system status
            websocket = app.state.websocket_connections.get(connection_id)
            if websocket:
                status = await get_system_status(user)
                await websocket.send_text(json.dumps({
                    "type": "status_response",
                    "data": status.dict(),
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message", connection_id=connection_id, message_type=message_type, error=str(e))

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        workers=1,
        loop="asyncio"
    )