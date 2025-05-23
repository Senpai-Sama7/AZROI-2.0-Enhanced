#!/usr/bin/env python3
"""
Main FastAPI application for the Autonomous AI Architect backend.
Provides REST API endpoints and WebSocket connections for real-time updates.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

# Import core components
from backend.core_orchestration.config_loader import ConfigLoader
from backend.core_orchestration.agent_orchestrator import AgentOrchestrator
from backend.core_orchestration.llm_router import LLMRouter
from backend.core_orchestration.monitoring_system import MonitoringSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class ArchitectGoalRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000, description="The goal description")
    
class ArchitectGoal(BaseModel):
    id: str
    text: str
    status: str = "pending"
    analysis: Optional[str] = None
    submitTime: str
    completionTime: Optional[str] = None
    processingError: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates"""
    default_llm_model_backend: Optional[str] = None
    log_level: Optional[str] = None
    max_concurrent_agents: Optional[int] = Field(None, ge=1, le=10)
    planner_agent_prompt_template: Optional[str] = None
    code_execution_timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)
    default_generated_app_port: Optional[int] = Field(None, ge=1000, le=65535)
    cloud_build_timeout_seconds: Optional[str] = None
    
    # Nested configurations
    open_interpreter_config: Optional[Dict] = None
    gcp_config_defaults: Optional[Dict] = None
    chroma_db_config: Optional[Dict] = None

# Global state management
class AppState:
    def __init__(self):
        self.goals: Dict[str, ArchitectGoal] = {}
        self.agents: Dict[str, Dict] = {}
        self.outputs: List[Dict] = []
        self.websocket_connections: List[WebSocket] = []
        self.config_loader: ConfigLoader = ConfigLoader()
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.llm_router: Optional[LLMRouter] = None
        self.monitoring: MonitoringSystem = MonitoringSystem()

app_state = AppState()

# Initialize FastAPI app
app = FastAPI(
    title="Autonomous AI Architect API",
    description="Backend API for the Autonomous AI Architect system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # React and Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting Autonomous AI Architect backend...")
        
        # Load configuration
        await app_state.config_loader.load_config()
        
        # Initialize LLM router
        llm_config = await app_state.config_loader.get_config()
        app_state.llm_router = LLMRouter(
            providers=llm_config.get('llm_providers', None),
            default_provider=llm_config.get('default_llm_provider', 'mock')
        )
        
        # Initialize agent orchestrator
        app_state.orchestrator = AgentOrchestrator(
            config_loader=app_state.config_loader,
            llm_router=app_state.llm_router
        )
        
        # Start monitoring
        await app_state.monitoring.start()
        
        logger.info("Backend startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        system_status = await app_state.monitoring.get_system_status()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "config_loader": "healthy" if app_state.config_loader else "unhealthy",
                "orchestrator": "healthy" if app_state.orchestrator else "unhealthy",
                "llm_router": "healthy" if app_state.llm_router else "unhealthy",
            },
            "system": system_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Configuration endpoints
@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        config = await app_state.config_loader.get_config()
        return config
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(config_update: ConfigUpdateRequest):
    """Update configuration"""
    try:
        # Validate and apply configuration changes
        updated_config = await app_state.config_loader.update_config(config_update.dict(exclude_unset=True))
        
        # Restart services if necessary
        if app_state.orchestrator:
            await app_state.orchestrator.reload_config()
        
        return {
            "message": "Configuration updated successfully",
            "updated_config": updated_config
        }
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Goal management endpoints
@app.post("/api/goals")
async def submit_goal(goal_request: ArchitectGoalRequest, background_tasks: BackgroundTasks):
    """Submit a new goal for processing"""
    try:
        goal_id = str(uuid.uuid4())
        goal = ArchitectGoal(
            id=goal_id,
            text=goal_request.text,
            submitTime=datetime.utcnow().isoformat()
        )
        
        app_state.goals[goal_id] = goal
        
        # Start processing in background
        background_tasks.add_task(process_goal, goal_id)
        
        # Notify WebSocket clients
        await broadcast_goal_update(goal)
        
        return {"goal_id": goal_id, "status": "submitted"}
    except Exception as e:
        logger.error(f"Failed to submit goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/goals/{goal_id}")
async def get_goal(goal_id: str):
    """Get goal by ID"""
    if goal_id not in app_state.goals:
        raise HTTPException(status_code=404, detail="Goal not found")
    return app_state.goals[goal_id]

@app.get("/api/goals")
async def list_goals():
    """List all goals"""
    return list(app_state.goals.values())

# Outputs endpoint
@app.get("/api/outputs")
async def get_outputs(goal_id: Optional[str] = None):
    """Get outputs, optionally filtered by goal ID"""
    if goal_id:
        filtered_outputs = [output for output in app_state.outputs if output.get("goalId") == goal_id]
        return filtered_outputs
    return app_state.outputs

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    app_state.websocket_connections.append(websocket)
    
    try:
        # Send initial state
        await websocket.send_json({
            "event": "initial_state",
            "data": {
                "goals": list(app_state.goals.values()),
                "agents": list(app_state.agents.values()),
                "outputs": app_state.outputs[-50:]  # Last 50 outputs
            }
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_json()
                # Handle incoming WebSocket messages if needed
                logger.debug(f"Received WebSocket message: {data}")
            except:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in app_state.websocket_connections:
            app_state.websocket_connections.remove(websocket)

# Background task functions
async def process_goal(goal_id: str):
    """Process a goal using the agent orchestrator"""
    try:
        goal = app_state.goals[goal_id]
        goal.status = "analyzing"
        await broadcast_goal_update(goal)
        
        # Use orchestrator to process the goal
        if app_state.orchestrator:
            async for update in app_state.orchestrator.process_goal(goal.text, goal_id):
                if update["type"] == "goal_status":
                    goal.status = update["status"]
                    if update.get("error"):
                        goal.processingError = update["error"]
                    if update["status"] == "completed":
                        goal.completionTime = datetime.utcnow().isoformat()
                    await broadcast_goal_update(goal)
                
                elif update["type"] == "agent_update":
                    app_state.agents[update["agent"]["id"]] = update["agent"]
                    await broadcast_agent_update(update["agent"])
                
                elif update["type"] == "output":
                    output = {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        **update["data"]
                    }
                    app_state.outputs.append(output)
                    await broadcast_output_update(output)
        else:
            # Fallback if orchestrator is not available
            goal.status = "completed"
            goal.completionTime = datetime.utcnow().isoformat()
            await broadcast_goal_update(goal)
        
    except Exception as e:
        logger.error(f"Goal processing failed for {goal_id}: {e}")
        goal = app_state.goals[goal_id]
        goal.status = "error"
        goal.processingError = str(e)
        await broadcast_goal_update(goal)

# WebSocket broadcast functions
async def broadcast_goal_update(goal: ArchitectGoal):
    """Broadcast goal update to all connected WebSocket clients"""
    message = {
        "event": "goal_update",
        "data": {
            "goal_id": goal.id,
            "goal": goal.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await broadcast_to_websockets(message)

async def broadcast_agent_update(agent: Dict):
    """Broadcast agent update to all connected WebSocket clients"""
    message = {
        "event": "agent_update",
        "data": {
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await broadcast_to_websockets(message)

async def broadcast_output_update(output: Dict):
    """Broadcast output update to all connected WebSocket clients"""
    message = {
        "event": "output_update",
        "data": {
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await broadcast_to_websockets(message)

async def broadcast_to_websockets(message: Dict):
    """Broadcast message to all connected WebSocket clients"""
    if not app_state.websocket_connections:
        return
    
    disconnected = []
    for websocket in app_state.websocket_connections:
        try:
            await websocket.send_json(message)
        except:
            disconnected.append(websocket)
    
    # Remove disconnected clients
    for websocket in disconnected:
        app_state.websocket_connections.remove(websocket)

# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )