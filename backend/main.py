#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/main.py

import asyncio
import json
import logging
import os
import secrets
import threading
import time
import uuid
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import core components
from core_orchestration.config_loader import ConfigLoader
from core_orchestration.agent_orchestrator import AgentOrchestrator
from core_orchestration.llm_router import LLMRouter
from core_orchestration.monitoring_system import MonitoringSystem, register_monitoring_metrics
from core_orchestration.safety_sandbox import SafetySandbox
from core_orchestration.hardware_audit import HardwareAuditSystem

# Import agents (will be used with CrewAI)
from agents.architect_agent import ArchitectAgent
from agents.planner_agent import PlannerAgent
from agents.code_execution_agent import CodeExecutionAgent
from agents.cloud_agent import CloudAgent

# Import vector storage and memory
from tools.vector_storage import VectorStorage
from tools.memory_manager import MemoryManager  # Keep compatibility with existing memory manager

# Import new AZR and FFL components
from azr.core import AbsoluteZeroReasoner
from ffl.core import FractalFeedbackLoop

# Load environment variables
load_dotenv()

# Set up credential paths
ROOT_DIR = Path(__file__).parent.parent
CREDENTIALS_DIR = ROOT_DIR / "credentials"
GCP_CREDENTIALS_PATH = CREDENTIALS_DIR / "architect-super-sa-key.json"
AZURE_CREDENTIALS_PATH = CREDENTIALS_DIR / "azure_deployment.json"

# Set Google Application Credentials environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCP_CREDENTIALS_PATH)

# Load Azure credentials
azure_credentials = {}
if AZURE_CREDENTIALS_PATH.exists():
    with open(AZURE_CREDENTIALS_PATH, "r") as f:
        azure_credentials = json.load(f)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("ai-architect-backend")

# Initialize configuration
config_loader = ConfigLoader()
config = config_loader.load_config()  # This will load from config.json and override with .env values

# Set log level from config
log_level = getattr(logging, config.get("log_level", "INFO"))
logger.setLevel(log_level)

# Create FastAPI app
app = FastAPI(
    title="Autonomous AI Architect API",
    description="Backend API for the Autonomous AI Architect system",
    version="1.0.0",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared resources
active_connections: Dict[str, WebSocket] = {}
active_tasks: Dict[str, Dict[str, Any]] = {}  # Track active tasks and their states
task_locks: Dict[str, asyncio.Lock] = {}  # Locks for task state updates to prevent race conditions

# Initialize monitoring system
monitoring_system = MonitoringSystem()
register_monitoring_metrics()  # Set up initial prometheus metrics

# Hardware audit system
hardware_audit_system = HardwareAuditSystem()  # For monitoring and auditing system resources

# Initialize vector storage with GCP bucket if available
bucket_name = os.getenv("GOOGLE_BUCKET", "").replace("gs://", "").replace("/", "")
vector_storage = VectorStorage(
    collection_name=config.get("vector_storage_config", {}).get("collection_name", "ai_architect_memory"),
    url=config.get("vector_storage_config", {}).get("url", None),
    path=config.get("vector_storage_config", {}).get("path", "./backend/vectorstore_data"),
    gcp_bucket_name=bucket_name if bucket_name else None,
    gcp_project_id=os.getenv("GOOGLE_PROJECT_ID", None),
)

# Initialize memory manager (compatibility layer over vector storage)
memory_manager = MemoryManager(
    vector_storage=vector_storage,
    collection_name=config.get("vector_storage_config", {}).get("collection_name", "ai_architect_memory"),
)

# Configure LLM router with Azure OpenAI if credentials exist
azure_config = {
    "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY") or azure_credentials.get("azure_api_key", ""),
    "azure_api_base": os.getenv("AZURE_OPENAI_API_BASE") or azure_credentials.get("azure_api_base", ""),
    "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION") or azure_credentials.get("azure_api_version", ""),
    "azure_deployment_id": os.getenv("AZURE_OPENAI_DEPLOYMENT_ID") or azure_credentials.get("azure_deployment_id", ""),
}

# Initialize LLM router with caching and Azure OpenAI support
llm_router = LLMRouter(
    redis_url=config.get("redis_config", {}).get("url", "redis://localhost:6379"),
    default_model=config.get("default_llm_model_backend", "gemini-2.5-flash-preview-04-17"),
    azure_config=azure_config if all(azure_config.values()) else None,
)

# Initialize safety sandbox
safety_sandbox = SafetySandbox(
    use_gvisor=config.get("sandbox_config", {}).get("use_gvisor", False),
    isolation_level=config.get("sandbox_config", {}).get("isolation_level", "high"),
)

# Initialize Absolute Zero Reasoner (AZR)
azr = AbsoluteZeroReasoner(llm_router=llm_router)

# Initialize Fractal Feedback Loop (FFL)
ffl = FractalFeedbackLoop(
    llm_router=llm_router,
    monitoring_system=monitoring_system,
    feedback_interval=config.get("ffl_config", {}).get("feedback_interval", 3600),
    initial_feedback_delay=config.get("ffl_config", {}).get("initial_feedback_delay", 86400),
    min_samples_required=config.get("ffl_config", {}).get("min_samples_required", 10),
    config=config.get("ffl_config", {})
)

# Initialize agent orchestrator with CrewAI and integrate AZR
agent_orchestrator = AgentOrchestrator(
    llm_router=llm_router, 
    memory_manager=memory_manager,
    safety_sandbox=safety_sandbox,
    monitoring_system=monitoring_system,
    azr=azr,  # Add AZR for zero-shot planning
    ffl=ffl,   # Add FFL for system improvement
    config=config
)

# --- API Models ---
class GoalRequest(BaseModel):
    goal: str
    client_analysis: Optional[str] = None
    user_id: Optional[str] = None  # To associate goals with specific users

class GoalResponse(BaseModel):
    goal_id: str
    status: str
    message: str
    websocket_url: str

# --- API Routes ---
@app.get("/")
async def root():
    return {"status": "alive", "service": "Autonomous AI Architect Backend"}

@app.get("/health")
async def health_check():
    """Health check endpoint with system metrics."""
    system_metrics = hardware_audit_system.get_basic_metrics()
    system_metrics["status"] = "healthy"
    return system_metrics

@app.get("/status/{goal_id}")
async def get_goal_status(goal_id: str):
    """Get the status and information about a specific goal."""
    if goal_id not in active_tasks:
        # Try to retrieve from memory
        memory_result = memory_manager.get_by_id(goal_id)
        if memory_result:
            return memory_result
        else:
            raise HTTPException(status_code=404, detail=f"Goal ID {goal_id} not found")
    
    # If active, return current status
    return active_tasks[goal_id]

@app.post("/goals", response_model=GoalResponse)
async def submit_goal(goal_request: GoalRequest, background_tasks: BackgroundTasks):
    """Submit a new goal to the Autonomous AI Architect system."""
    # Generate a unique goal ID
    goal_id = str(uuid.uuid4())
    
    # Create a lock for this task to prevent race conditions
    task_locks[goal_id] = asyncio.Lock()
    
    # Initialize task state
    active_tasks[goal_id] = {
        "goal_id": goal_id,
        "goal": goal_request.goal,
        "client_analysis": goal_request.client_analysis,
        "user_id": goal_request.user_id or "anonymous",
        "status": "submitted",
        "created_at": time.time(),
        "updated_at": time.time(),
        "plan": None,
        "artifacts": [],
        "logs": [],
    }
    
    # Start the orchestration process in the background
    background_tasks.add_task(
        agent_orchestrator.start_orchestration,
        goal_id=goal_id,
        goal=goal_request.goal,
        client_analysis=goal_request.client_analysis,
    )
    
    # Return response with websocket URL for real-time updates
    host = os.environ.get("HOST", "localhost")
    port = os.environ.get("PORT", "8001")
    websocket_url = f"ws://{host}:{port}/ws/{goal_id}"
    
    return GoalResponse(
        goal_id=goal_id,
        status="submitted",
        message="Goal submitted successfully. Connect to the websocket for real-time updates.",
        websocket_url=websocket_url,
    )

@app.websocket("/ws/{goal_id}")
async def websocket_endpoint(websocket: WebSocket, goal_id: str):
    """WebSocket connection for real-time updates on goal progress."""
    await websocket.accept()
    
    # Store the connection
    active_connections[goal_id] = websocket
    
    try:
        # Send initial data if there's any
        if goal_id in active_tasks:
            await websocket.send_json({"type": "state_update", "data": active_tasks[goal_id]})
        
        # Keep the connection open to receive messages from client (if needed)
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            message_data = json.loads(data)
            
            # Example: Client requests specific information
            if message_data.get("type") == "request_logs":
                if goal_id in active_tasks:
                    await websocket.send_json({
                        "type": "logs",
                        "data": {"logs": active_tasks[goal_id].get("logs", [])}
                    })
    
    except WebSocketDisconnect:
        # Clean up when client disconnects
        if goal_id in active_connections:
            del active_connections[goal_id]
    
    except Exception as e:
        logger.error(f"WebSocket error for {goal_id}: {str(e)}")
        if goal_id in active_connections:
            del active_connections[goal_id]

# Add new endpoint for AZR planning
@app.post("/planning")
async def create_plan(goal_request: GoalRequest):
    """Create a plan using Absolute Zero Reasoner without execution."""
    try:
        plan = await azr.decompose_task(
            goal=goal_request.goal,
            context=goal_request.client_analysis
        )
        return {
            "status": "success",
            "plan": plan,
            "goal": goal_request.goal
        }
    except Exception as e:
        logger.error(f"Error creating plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating plan: {str(e)}")

# Add endpoint to view FFL analytics
@app.get("/ffl/analytics")
async def get_ffl_analytics():
    """Get FFL analytics including performance metrics and improvement history."""
    return {
        "performance_metrics": ffl.performance_metrics,
        "improvement_history": ffl.improvement_history,
        "last_feedback_time": ffl.last_feedback_time,
        "next_feedback_time": ffl.last_feedback_time + ffl.feedback_interval
    }

# Utility function to send updates to connected WebSocket clients
async def send_update(goal_id: str, data: dict, update_type: str = "state_update"):
    """Send an update to a connected client via WebSocket."""
    if goal_id in active_connections:
        websocket = active_connections[goal_id]
        try:
            await websocket.send_json({"type": update_type, "data": data})
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {str(e)}")

# Update task state (with locking to prevent race conditions)
async def update_task_state(goal_id: str, updates: dict):
    """Update the state of a task with proper locking to prevent race conditions."""
    if goal_id not in task_locks:
        task_locks[goal_id] = asyncio.Lock()
        
    async with task_locks[goal_id]:
        if goal_id in active_tasks:
            active_tasks[goal_id].update(updates)
            active_tasks[goal_id]["updated_at"] = time.time()
            
            # Also update in vector memory
            memory_manager.store(active_tasks[goal_id])
            
            # Send update to connected client
            await send_update(goal_id, active_tasks[goal_id])
            
            # If task is complete, update metrics
            if updates.get("status") == "completed":
                monitoring_system.record_task_completed(goal_id)
                
                # Cleanup locks after completion
                if goal_id in task_locks:
                    del task_locks[goal_id]

# --- Cleanup job ---
async def cleanup_old_tasks():
    """Periodic job to clean up old tasks from memory to prevent leaks."""
    while True:
        current_time = time.time()
        
        # Keep locks here to prevent race conditions
        goals_to_remove = []
        
        for goal_id, task in active_tasks.items():
            # If task is over 24 hours old and not active, mark for removal
            if current_time - task.get("updated_at", 0) > 86400 and task.get("status") not in ["running", "submitted"]:
                goals_to_remove.append(goal_id)
        
        # Remove old tasks
        for goal_id in goals_to_remove:
            if goal_id in active_tasks:
                # Make sure it's saved to memory first
                memory_manager.store(active_tasks[goal_id])
                
                # Then delete from active state
                del active_tasks[goal_id]
                
                # Clean up any locks
                if goal_id in task_locks:
                    del task_locks[goal_id]
                    
                logger.info(f"Cleaned up old task {goal_id}")
        
        # Run once per hour
        await asyncio.sleep(3600)

# --- Main function ---
@app.on_event("startup")
async def startup_event():
    """Startup event handler to initialize system components."""
    # Start the cleanup task
    asyncio.create_task(cleanup_old_tasks())
    
    # Update system metrics on startup
    system_info = hardware_audit_system.get_full_system_info()
    logger.info(f"System initialized with: {json.dumps(system_info, indent=2)}")
    
    # Start monitoring system
    monitoring_system.start()
    
    # Initialize vector storage
    await vector_storage.initialize()
    
    # Initialize safety sandbox - ensure safety features are active
    await safety_sandbox.initialize()
    
    # Start Fractal Feedback Loop
    await ffl.start()
    
    # Expose Prometheus metrics
    from prometheus_client import start_http_server
    start_http_server(int(os.environ.get("METRICS_PORT", "8002")))

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler to clean up resources."""
    # Cleanup any resources
    await llm_router.close()
    monitoring_system.stop()
    await ffl.stop()

# Expose agent orchestrator and update function to other modules
app.state.agent_orchestrator = agent_orchestrator
app.state.update_task_state = update_task_state
app.state.send_update = send_update

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 8001)),
        reload=True  # Only for development
    )