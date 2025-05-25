"""
Pydantic models for agent communication, tool I/O, and system messaging.
Implements checklist requirements for TaskRequest, TaskResult, ContextPassingModel, ErrorResponse, ProgressUpdate, and tool I/O models.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class TaskRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent to execute (e.g., architect, planner, code_generator, etc.)")
    task_description: str = Field(..., min_length=5, max_length=2000)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_id: Optional[str] = None
    complexity: Optional[str] = Field(None, description="Task complexity (simple, medium, complex, enterprise)")
    priority: Optional[str] = Field(None, description="Task priority (low, medium, high, critical)")

class TaskResult(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    agent_type: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ContextPassingModel(BaseModel):
    context: Dict[str, Any]
    previous_agent: Optional[str] = None
    next_agent: Optional[str] = None
    handoff_reason: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[int] = None
    recovery_suggestion: Optional[str] = None
    timestamp: Optional[str] = None

class ProgressUpdate(BaseModel):
    task_id: str
    status: str = Field(..., description="Status (pending, running, completed, failed, etc.)")
    progress: float = Field(..., ge=0.0, le=1.0)
    message: Optional[str] = None
    timestamp: Optional[str] = None

# Tool I/O models (example for code generation tool)
class CodeGenInput(BaseModel):
    language: str
    requirements: Dict[str, Any]
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CodeGenOutput(BaseModel):
    code: str
    files: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

# Add additional tool I/O models as needed for other CrewAI tools
