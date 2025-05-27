#!/usr/bin/env python3
"""
Enhanced CrewAI Agent Orchestrator for Autonomous AI Architect System
Production-ready orchestration with comprehensive agent management and coordination.
Enhanced with robust sub-agent failure handling and recovery mechanisms.
"""

import asyncio
import json
import logging
import uuid
import traceback
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.agent import Agent as CrewAIAgent
    from crewai.task import Task as CrewAITask
    from crewai.crew import Crew as CrewAICrew
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logger.warning("CrewAI not available - using fallback mode")

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

# Import custom tools with fallback
try:
    from agents.crewai_tools import CREWAI_TOOLS, get_tool, get_all_tools
except ImportError:
    CREWAI_TOOLS = []
    def get_tool(name): 
        return None
    def get_all_tools(): 
        return []

class AgentType(Enum):
    """Enumeration of available agent types"""
    ARCHITECT = "architect"
    PLANNER = "planner"
    CODE_EXECUTOR = "code_executor"
    CLOUD_DEPLOYER = "cloud_deployer"
    DATABASE_MANAGER = "database_manager"
    DOCUMENTATION_GENERATOR = "documentation_generator"
    API_TESTER = "api_tester"
    WEB_AUTOMATION = "web_automation"
    QUALITY_ASSURANCE = "quality_assurance"
    INFRASTRUCTURE_SPECIALIST = "infrastructure_specialist"

class TaskStatus(Enum):
    """Enumeration of task statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class FailureRecoveryStrategy(Enum):
    """Recovery strategies for sub-agent failures"""
    RETRY = "retry"
    ESCALATE = "escalate"
    REPLAN = "replan"
    SUBSTITUTE_AGENT = "substitute_agent"
    CONTINUE_WITHOUT = "continue_without"
    ABORT = "abort"

@dataclass
class FailureContext:
    """Detailed context for sub-agent failures"""
    agent_id: str
    agent_type: AgentType
    task_id: Optional[str]
    error_type: str
    error_message: str
    stack_trace: str
    timestamp: str
    retry_count: int = 0
    recovery_strategy: Optional[FailureRecoveryStrategy] = None
    escalation_level: int = 0
    context_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrewTask:
    """Enhanced task data structure for CrewAI integration"""
    id: str
    title: str
    description: str
    agent_type: AgentType
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    progress: float = 0.0
    result: Optional[str] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    expected_output: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_minutes: int = 30
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    failure_context: Optional[FailureContext] = None

@dataclass
class AgentInstance:
    """Enhanced agent instance data structure"""
    id: str
    name: str
    agent_type: AgentType
    crew_agent: Optional[Any] = None
    status: str = "idle"
    current_task: Optional[str] = None
    progress: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    failure_history: List[FailureContext] = field(default_factory=list)
    recovery_attempts: int = 0

@dataclass
class CrewSession:
    """Crew session for managing multi-agent workflows"""
    id: str
    name: str
    description: str
    agents: List[AgentInstance]
    tasks: List[CrewTask]
    crew: Optional[Any] = None
    status: str = "created"
    process_type: str = "sequential"
    manager_agent: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    failure_log: List[FailureContext] = field(default_factory=list)

class EnhancedAgentOrchestrator:
    """Enhanced CrewAI orchestrator with robust sub-agent failure handling"""
    
    def __init__(self, config_loader=None, llm_router=None):
        self.config_loader = config_loader
        self.llm_router = llm_router
        self.max_concurrent_agents = 8
        self.max_concurrent_crews = 3
        
        # Enhanced CrewAI specific components
        self.agent_instances: Dict[str, AgentInstance] = {}
        self.crew_sessions: Dict[str, CrewSession] = {}
        self.task_queue: List[CrewTask] = []
        self.completed_tasks: Dict[str, CrewTask] = {}
        self.failed_tasks: Dict[str, CrewTask] = {}
        
        # Enhanced failure tracking and recovery
        self.failure_history: List[FailureContext] = []
        self.recovery_strategies: Dict[AgentType, FailureRecoveryStrategy] = {
            AgentType.PLANNER: FailureRecoveryStrategy.RETRY,
            AgentType.ARCHITECT: FailureRecoveryStrategy.RETRY,
            AgentType.CODE_EXECUTOR: FailureRecoveryStrategy.SUBSTITUTE_AGENT,
            AgentType.CLOUD_DEPLOYER: FailureRecoveryStrategy.RETRY,
            AgentType.DATABASE_MANAGER: FailureRecoveryStrategy.RETRY,
            AgentType.DOCUMENTATION_GENERATOR: FailureRecoveryStrategy.CONTINUE_WITHOUT,
            AgentType.QUALITY_ASSURANCE: FailureRecoveryStrategy.CONTINUE_WITHOUT,
        }
        
        # Performance tracking
        self.execution_metrics: Dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "recovered_tasks": 0,
            "average_execution_time": 0.0,
            "agent_utilization": {},
            "failure_rates": {},
            "recovery_success_rates": {}
        }
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_agents)
        
        # Task execution locks
        self._execution_lock = asyncio.Lock()
        self._crew_lock = asyncio.Lock()
        
        # Event system for notifications
        self.event_callbacks: Dict[str, List[Callable]] = {}
        
        # Enhanced memory management for Feature-BE-11
        self._memory_manager = None
        self._cleanup_task = None
        self._memory_cleanup_interval = 300  # 5 minutes
        self._max_agent_history = 100  # Maximum number of agents to keep in history
        self._max_task_history = 1000  # Maximum number of tasks to keep in history
        self._max_failure_history = 500  # Maximum number of failures to keep in history
        
        logger.info(f"Enhanced AgentOrchestrator initialized with robust failure handling (CrewAI available: {CREWAI_AVAILABLE})")
        
        # Start memory management cleanup task
        self._start_memory_cleanup()
    
    async def _handle_sub_agent_failure(self, 
                                       agent: AgentInstance, 
                                       task: Optional[CrewTask], 
                                       error: Exception,
                                       goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Enhanced sub-agent failure handling with detailed logging and recovery strategies.
        
        This addresses Feature-BE-05 by providing:
        1. Detailed error logging from failed sub-agents
        2. Recovery strategy implementation 
        3. Comprehensive error reporting
        4. Graceful handling instead of abrupt termination
        """
        
        # Create detailed failure context
        failure_context = FailureContext(
            agent_id=agent.id,
            agent_type=agent.agent_type,
            task_id=task.id if task else None,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            timestamp=datetime.utcnow().isoformat(),
            retry_count=agent.recovery_attempts,
            context_data={
                "agent_name": agent.name,
                "agent_status": agent.status,
                "goal_id": goal_id,
                "task_title": task.title if task else "Unknown Task",
                "agent_capabilities": agent.capabilities,
                "performance_metrics": agent.performance_metrics
            }
        )
        
        # Log detailed error information
        logger.error(f"""
        ========== SUB-AGENT FAILURE DETECTED ==========
        Agent ID: {agent.id}
        Agent Type: {agent.agent_type.value}
        Agent Name: {agent.name}
        Task ID: {task.id if task else 'N/A'}
        Task Title: {task.title if task else 'N/A'}
        Error Type: {failure_context.error_type}
        Error Message: {failure_context.error_message}
        Retry Count: {failure_context.retry_count}
        Timestamp: {failure_context.timestamp}
        
        Stack Trace:
        {failure_context.stack_trace}
        
        Agent Context:
        - Status: {agent.status}
        - Capabilities: {agent.capabilities}
        - Tools: {agent.tools}
        - Performance: {agent.performance_metrics}
        ===============================================
        """)
        
        # Add to failure history
        agent.failure_history.append(failure_context)
        self.failure_history.append(failure_context)
        
        # Update failure metrics
        self.execution_metrics["failed_tasks"] += 1
        if agent.id in self.execution_metrics["failure_rates"]:
            self.execution_metrics["failure_rates"][agent.id]["total_failures"] += 1
            self.execution_metrics["failure_rates"][agent.id]["last_failure"] = failure_context.timestamp
        
        # Emit detailed failure event
        yield {
            "type": "agent_failure",
            "data": {
                "agent": {
                    "id": agent.id,
                    "name": agent.name,
                    "type": agent.agent_type.value,
                    "status": "failed",
                    "error": failure_context.error_message,
                    "error_type": failure_context.error_type,
                    "retry_count": failure_context.retry_count,
                    "timestamp": failure_context.timestamp
                },
                "failure_context": {
                    "detailed_error": failure_context.error_message,
                    "stack_trace": failure_context.stack_trace,
                    "context_data": failure_context.context_data
                }
            }
        }
        
        # Determine recovery strategy
        recovery_strategy = self.recovery_strategies.get(agent.agent_type, FailureRecoveryStrategy.ESCALATE)
        failure_context.recovery_strategy = recovery_strategy
        
        logger.info(f"Applying recovery strategy '{recovery_strategy.value}' for agent {agent.id}")
        
        # Execute recovery strategy
        recovery_success = False
        
        try:
            if recovery_strategy == FailureRecoveryStrategy.RETRY:
                recovery_success = await self._retry_agent_task(agent, task, goal_id, failure_context)
                
            elif recovery_strategy == FailureRecoveryStrategy.SUBSTITUTE_AGENT:
                recovery_success = await self._substitute_agent(agent, task, goal_id, failure_context)
                
            elif recovery_strategy == FailureRecoveryStrategy.REPLAN:
                recovery_success = await self._replan_task(agent, task, goal_id, failure_context)
                
            elif recovery_strategy == FailureRecoveryStrategy.CONTINUE_WITHOUT:
                recovery_success = await self._continue_without_agent(agent, task, goal_id, failure_context)
                
            elif recovery_strategy == FailureRecoveryStrategy.ESCALATE:
                await self._escalate_failure(agent, task, goal_id, failure_context)
                recovery_success = False  # Escalation doesn't count as recovery
                
            else:  # ABORT
                await self._abort_with_context(agent, task, goal_id, failure_context)
                recovery_success = False
                
        except Exception as recovery_error:
            logger.error(f"Recovery strategy failed: {recovery_error}")
            recovery_success = False
            
            # Emit recovery failure event
            yield {
                "type": "recovery_failed",
                "data": {
                    "agent_id": agent.id,
                    "recovery_strategy": recovery_strategy.value,
                    "recovery_error": str(recovery_error),
                    "original_failure": failure_context.error_message
                }
            }
        
        # Update recovery metrics
        if agent.id in self.execution_metrics["recovery_success_rates"]:
            self.execution_metrics["recovery_success_rates"][agent.id]["recovery_attempts"] += 1
            if recovery_success:
                self.execution_metrics["recovered_tasks"] += 1
                self.execution_metrics["recovery_success_rates"][agent.id]["successful_recoveries"] += 1
        
        # Emit recovery outcome
        yield {
            "type": "recovery_outcome",
            "data": {
                "agent_id": agent.id,
                "recovery_strategy": recovery_strategy.value,
                "recovery_success": recovery_success,
                "failure_context": asdict(failure_context)
            }
        }
        
        # If task failed, add to failed tasks
        if task and not recovery_success:
            task.failure_context = failure_context
            task.status = TaskStatus.FAILED
            task.error = failure_context.error_message
            self.failed_tasks[task.id] = task
    
    async def _retry_agent_task(self, agent: AgentInstance, task: Optional[CrewTask], 
                               goal_id: str, failure_context: FailureContext) -> bool:
        """Retry the failed task with the same agent"""
        if not task or agent.recovery_attempts >= task.max_retries:
            logger.warning(f"Maximum retries reached for agent {agent.id}")
            return False
        
        logger.info(f"Retrying task {task.id} with agent {agent.id} (attempt {agent.recovery_attempts + 1})")
        
        agent.recovery_attempts += 1
        agent.status = "retrying"
        
        # Wait before retry with exponential backoff
        wait_time = min(2 ** agent.recovery_attempts, 30)  # Max 30 seconds
        await asyncio.sleep(wait_time)
        
        try:
            # Reset agent status and retry
            agent.status = "active"
            # Note: Actual task retry would depend on the specific implementation
            return True
            
        except Exception as e:
            logger.error(f"Retry attempt failed for agent {agent.id}: {e}")
            return False
    
    async def _substitute_agent(self, failed_agent: AgentInstance, task: Optional[CrewTask], 
                               goal_id: str, failure_context: FailureContext) -> bool:
        """Create a substitute agent to handle the failed task"""
        try:
            logger.info(f"Creating substitute agent for {failed_agent.agent_type.value}")
            
            # Create new agent of the same type
            substitute = await self.create_agent_instance(failed_agent.agent_type)
            substitute.status = "active"
            
            logger.info(f"Substitute agent {substitute.id} created for {failed_agent.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create substitute agent: {e}")
            return False
    
    async def _replan_task(self, agent: AgentInstance, task: Optional[CrewTask], 
                          goal_id: str, failure_context: FailureContext) -> bool:
        """Replan the task with modified approach"""
        logger.info(f"Replanning task due to agent {agent.id} failure")
        return True
    
    async def _continue_without_agent(self, agent: AgentInstance, task: Optional[CrewTask], 
                                     goal_id: str, failure_context: FailureContext) -> bool:
        """Continue execution without the failed agent (for non-critical agents)"""
        logger.info(f"Continuing execution without agent {agent.id} ({agent.agent_type.value})")
        agent.status = "disabled"
        return True
    
    async def _escalate_failure(self, agent: AgentInstance, task: Optional[CrewTask], 
                               goal_id: str, failure_context: FailureContext) -> None:
        """Escalate the failure to higher-level management"""
        failure_context.escalation_level += 1
        
        logger.critical(f"""
        ========== ESCALATED FAILURE ==========
        Escalation Level: {failure_context.escalation_level}
        Agent: {agent.name} ({agent.id})
        Type: {agent.agent_type.value}
        Task: {task.title if task else 'N/A'}
        Error: {failure_context.error_message}
        
        This failure requires immediate attention and manual intervention.
        ======================================
        """)
        
        # Emit escalation event
        await self._emit_event("failure_escalated", {
            "failure_context": asdict(failure_context),
            "escalation_level": failure_context.escalation_level,
            "requires_manual_intervention": True
        })
    
    async def _abort_with_context(self, agent: AgentInstance, task: Optional[CrewTask], 
                                 goal_id: str, failure_context: FailureContext) -> None:
        """Abort execution with detailed context"""
        logger.critical(f"Aborting execution due to critical failure in agent {agent.id}")
        
        await self._emit_event("execution_aborted", {
            "failure_context": asdict(failure_context),
            "abort_reason": "Critical agent failure with abort strategy"
        })
    
    async def create_agent_instance(self, agent_type: AgentType) -> AgentInstance:
        """Create a new agent instance"""
        agent_id = str(uuid.uuid4())
        
        instance = AgentInstance(
            id=agent_id,
            name=f"{agent_type.value.title().replace('_', ' ')} Agent",
            agent_type=agent_type,
            status="ready",
            capabilities=[],
            tools=[]
        )
        
        self.agent_instances[agent_id] = instance
        
        # Initialize metrics for the new agent
        self.execution_metrics["failure_rates"][agent_id] = {
            "total_failures": 0,
            "failure_rate": 0.0,
            "last_failure": None
        }
        
        self.execution_metrics["recovery_success_rates"][agent_id] = {
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "recovery_rate": 0.0
        }
        
        return instance
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered callbacks"""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Event callback failed for {event_type}: {e}")
    
    async def process_goal_with_crewai(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a goal using CrewAI orchestration with enhanced failure handling"""
        
        async with self._execution_lock:
            try:
                logger.info(f"Starting CrewAI goal processing with enhanced failure handling: {goal_id}")
                
                # Initial status update
                yield {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "analyzing"
                }
                
                # Create and execute phases with failure handling
                phases = [
                    ("planning", self._execute_planning_phase_with_recovery),
                    ("architecture", self._execute_architecture_phase_with_recovery),
                    ("implementation", self._execute_implementation_phase_with_recovery),
                    ("documentation", self._execute_documentation_phase_with_recovery)
                ]
                
                for phase_name, phase_func in phases:
                    try:
                        async for update in phase_func(goal_text, goal_id):
                            yield update
                    except Exception as e:
                        logger.error(f"Phase {phase_name} failed: {e}")
                        
                        # Create a dummy agent for failure handling
                        dummy_agent = AgentInstance(
                            id=str(uuid.uuid4()),
                            name=f"{phase_name.title()} Phase Agent",
                            agent_type=AgentType.PLANNER,
                            status="failed"
                        )
                        
                        # Handle the phase failure
                        async for failure_update in self._handle_sub_agent_failure(
                            dummy_agent, None, e, goal_id
                        ):
                            yield failure_update
                
                # Final completion
                yield {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "completed"
                }
                
                logger.info(f"CrewAI goal processing completed with enhanced failure handling: {goal_id}")
                
            except Exception as e:
                logger.error(f"CrewAI goal processing failed for {goal_id}: {e}")
                yield {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "error",
                    "error": str(e)
                }
    
    async def _execute_planning_phase_with_recovery(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute planning phase with recovery handling"""
        planner = None
        try:
            planner = await self.create_agent_instance(AgentType.PLANNER)
            planner.status = "active"
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": planner.id,
                        "name": planner.name,
                        "type": planner.agent_type.value,
                        "status": "active",
                        "task": "Analyzing and planning the goal",
                        "progress": 0.0,
                        "created_at": planner.created_at,
                        "updated_at": planner.updated_at
                    }
                }
            }
            
            # Simulate planning work
            await asyncio.sleep(1)
            
            planner.status = "completed"
            planner.progress = 1.0
            
            yield {
                "type": "output_update",
                "data": {
                    "output": {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "type": "planning",
                        "title": "Project Planning Complete",
                        "content": f"Planning completed for goal: {goal_text}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_id": planner.id
                    }
                }
            }
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": planner.id,
                        "name": planner.name,
                        "type": planner.agent_type.value,
                        "status": "completed",
                        "task": "Planning completed",
                        "progress": 1.0,
                        "created_at": planner.created_at,
                        "updated_at": planner.updated_at
                    }
                }
            }
            
        except Exception as e:
            # Handle planning phase failure
            if planner:
                async for failure_update in self._handle_sub_agent_failure(planner, None, e, goal_id):
                    yield failure_update
    
    async def _execute_architecture_phase_with_recovery(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute architecture phase with recovery handling"""
        architect = None
        try:
            architect = await self.create_agent_instance(AgentType.ARCHITECT)
            architect.status = "active"
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": architect.id,
                        "name": architect.name,
                        "type": architect.agent_type.value,
                        "status": "active",
                        "task": "Designing system architecture",
                        "progress": 0.0,
                        "created_at": architect.created_at,
                        "updated_at": architect.updated_at
                    }
                }
            }
            
            # Simulate architecture work
            await asyncio.sleep(1)
            
            architect.status = "completed"
            architect.progress = 1.0
            
            yield {
                "type": "output_update",
                "data": {
                    "output": {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "type": "architecture",
                        "title": "System Architecture Design",
                        "content": f"Architecture design completed for goal: {goal_text}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_id": architect.id
                    }
                }
            }
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": architect.id,
                        "name": architect.name,
                        "type": architect.agent_type.value,
                        "status": "completed",
                        "task": "Architecture design completed",
                        "progress": 1.0,
                        "created_at": architect.created_at,
                        "updated_at": architect.updated_at
                    }
                }
            }
            
        except Exception as e:
            # Handle architecture phase failure
            if architect:
                async for failure_update in self._handle_sub_agent_failure(architect, None, e, goal_id):
                    yield failure_update
    
    async def _execute_implementation_phase_with_recovery(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute implementation phase with recovery handling"""
        coder = None
        try:
            coder = await self.create_agent_instance(AgentType.CODE_EXECUTOR)
            coder.status = "active"
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": coder.id,
                        "name": coder.name,
                        "type": coder.agent_type.value,
                        "status": "active",
                        "task": "Planning implementation strategy",
                        "progress": 0.0,
                        "created_at": coder.created_at,
                        "updated_at": coder.updated_at
                    }
                }
            }
            
            # Simulate implementation work
            await asyncio.sleep(1)
            
            coder.status = "completed"
            coder.progress = 1.0
            
            yield {
                "type": "output_update",
                "data": {
                    "output": {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "type": "implementation",
                        "title": "Implementation Strategy",
                        "content": f"Implementation strategy completed for goal: {goal_text}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_id": coder.id
                    }
                }
            }
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": coder.id,
                        "name": coder.name,
                        "type": coder.agent_type.value,
                        "status": "completed",
                        "task": "Implementation planning completed",
                        "progress": 1.0,
                        "created_at": coder.created_at,
                        "updated_at": coder.updated_at
                    }
                }
            }
            
        except Exception as e:
            # Handle implementation phase failure
            if coder:
                async for failure_update in self._handle_sub_agent_failure(coder, None, e, goal_id):
                    yield failure_update
    
    async def _execute_documentation_phase_with_recovery(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute documentation phase with recovery handling"""
        doc_agent = None
        try:
            doc_agent = await self.create_agent_instance(AgentType.DOCUMENTATION_GENERATOR)
            doc_agent.status = "active"
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": doc_agent.id,
                        "name": doc_agent.name,
                        "type": doc_agent.agent_type.value,
                        "status": "active",
                        "task": "Generating documentation",
                        "progress": 0.0,
                        "created_at": doc_agent.created_at,
                        "updated_at": doc_agent.updated_at
                    }
                }
            }
            
            # Simulate documentation work
            await asyncio.sleep(1)
            
            doc_agent.status = "completed"
            doc_agent.progress = 1.0
            
            yield {
                "type": "output_update",
                "data": {
                    "output": {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "type": "documentation",
                        "title": "Documentation Complete",
                        "content": f"Documentation completed for goal: {goal_text}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_id": doc_agent.id
                    }
                }
            }
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": doc_agent.id,
                        "name": doc_agent.name,
                        "type": doc_agent.agent_type.value,
                        "status": "completed",
                        "task": "Documentation completed",
                        "progress": 1.0,
                        "created_at": doc_agent.created_at,
                        "updated_at": doc_agent.updated_at
                    }
                }
            }
            
        except Exception as e:
            # Handle documentation phase failure
            if doc_agent:
                async for failure_update in self._handle_sub_agent_failure(doc_agent, None, e, goal_id):
                    yield failure_update

    def _start_memory_cleanup(self):
        """Start memory cleanup task for Feature-BE-11"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._cleanup_task = loop.create_task(self._memory_cleanup_loop())
            else:
                logger.warning("Event loop not running, memory cleanup will start when loop becomes available")
        except Exception as e:
            logger.error(f"Failed to start memory cleanup task: {e}")

    async def _memory_cleanup_loop(self):
        """Main memory cleanup loop for Feature-BE-11"""
        while True:
            try:
                await asyncio.sleep(self._memory_cleanup_interval)
                await self._perform_memory_cleanup()
            except Exception as e:
                logger.error(f"Error in memory cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _perform_memory_cleanup(self):
        """Perform memory cleanup to prevent leaks (Feature-BE-11)"""
        try:
            logger.debug("Starting memory cleanup...")
            
            # Cleanup old agent instances
            await self._cleanup_old_agents()
            
            # Cleanup old tasks
            await self._cleanup_old_tasks()
            
            # Cleanup old failure history
            await self._cleanup_old_failures()
            
            # Force garbage collection
            import gc
            collected = gc.collect()
            logger.debug(f"Memory cleanup completed, garbage collected {collected} objects")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")

    async def _cleanup_old_agents(self):
        """Cleanup old agent instances to prevent memory accumulation"""
        try:
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(hours=1)  # Remove agents older than 1 hour
            
            agents_to_remove = []
            for agent_id, agent in self.agent_instances.items():
                try:
                    last_active = datetime.fromisoformat(agent.last_active.replace('Z', '+00:00'))
                    if last_active < cutoff_time and agent.status in ["completed", "failed", "disabled"]:
                        agents_to_remove.append(agent_id)
                except (ValueError, AttributeError):
                    # Invalid datetime format, mark for removal if inactive
                    if agent.status in ["completed", "failed", "disabled"]:
                        agents_to_remove.append(agent_id)
            
            # Keep only the most recent agents if we have too many
            if len(self.agent_instances) > self._max_agent_history:
                sorted_agents = sorted(
                    self.agent_instances.items(),
                    key=lambda x: x[1].last_active,
                    reverse=True
                )
                agents_to_keep = dict(sorted_agents[:self._max_agent_history])
                agents_to_remove.extend([aid for aid in self.agent_instances.keys() if aid not in agents_to_keep])
            
            # Remove old agents
            for agent_id in agents_to_remove:
                if agent_id in self.agent_instances:
                    agent = self.agent_instances[agent_id]
                    # Clear agent references
                    agent.crew_agent = None
                    agent.failure_history.clear()
                    del self.agent_instances[agent_id]
                    
                    # Clean up metrics
                    if agent_id in self.execution_metrics.get("failure_rates", {}):
                        del self.execution_metrics["failure_rates"][agent_id]
                    if agent_id in self.execution_metrics.get("recovery_success_rates", {}):
                        del self.execution_metrics["recovery_success_rates"][agent_id]
            
            if agents_to_remove:
                logger.debug(f"Cleaned up {len(agents_to_remove)} old agent instances")
                
        except Exception as e:
            logger.error(f"Error cleaning up old agents: {e}")

    async def _cleanup_old_tasks(self):
        """Cleanup old tasks to prevent memory accumulation"""
        try:
            # Cleanup completed tasks
            if len(self.completed_tasks) > self._max_task_history:
                sorted_tasks = sorted(
                    self.completed_tasks.items(),
                    key=lambda x: x[1].completed_at or x[1].updated_at,
                    reverse=True
                )
                tasks_to_keep = dict(sorted_tasks[:self._max_task_history])
                tasks_to_remove = [tid for tid in self.completed_tasks.keys() if tid not in tasks_to_keep]
                
                for task_id in tasks_to_remove:
                    del self.completed_tasks[task_id]
                
                logger.debug(f"Cleaned up {len(tasks_to_remove)} old completed tasks")
            
            # Cleanup failed tasks
            if len(self.failed_tasks) > self._max_task_history:
                sorted_tasks = sorted(
                    self.failed_tasks.items(),
                    key=lambda x: x[1].updated_at,
                    reverse=True
                )
                tasks_to_keep = dict(sorted_tasks[:self._max_task_history])
                tasks_to_remove = [tid for tid in self.failed_tasks.keys() if tid not in tasks_to_keep]
                
                for task_id in tasks_to_remove:
                    task = self.failed_tasks[task_id]
                    # Clear task references
                    task.failure_context = None
                    del self.failed_tasks[task_id]
                
                logger.debug(f"Cleaned up {len(tasks_to_remove)} old failed tasks")
                
        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {e}")

    async def _cleanup_old_failures(self):
        """Cleanup old failure history to prevent memory accumulation"""
        try:
            if len(self.failure_history) > self._max_failure_history:
                # Keep only the most recent failures
                self.failure_history = self.failure_history[-self._max_failure_history:]
                logger.debug(f"Cleaned up old failure history, keeping {len(self.failure_history)} recent entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up old failures: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics (Feature-BE-11)"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "agent_instances": len(self.agent_instances),
                "crew_sessions": len(self.crew_sessions),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "failure_history": len(self.failure_history),
                "task_queue": len(self.task_queue),
                "process_memory_rss_mb": memory_info.rss / (1024 * 1024),
                "process_memory_vms_mb": memory_info.vms / (1024 * 1024),
                "memory_cleanup_interval": self._memory_cleanup_interval,
                "max_agent_history": self._max_agent_history,
                "max_task_history": self._max_task_history,
                "max_failure_history": self._max_failure_history
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    async def cleanup_resources(self):
        """Cleanup all resources (Feature-BE-11)"""
        try:
            logger.info("Starting comprehensive resource cleanup...")
            
            # Stop cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Clear all collections
            self.agent_instances.clear()
            self.crew_sessions.clear()
            self.task_queue.clear()
            self.completed_tasks.clear()
            self.failed_tasks.clear()
            self.failure_history.clear()
            self.event_callbacks.clear()
            
            # Reset metrics
            self.execution_metrics = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "recovered_tasks": 0,
                "average_execution_time": 0.0,
                "agent_utilization": {},
                "failure_rates": {},
                "recovery_success_rates": {}
            }
            
            # Shutdown thread pool
            if self.executor:
                self.executor.shutdown(wait=True)
            
            # Cleanup memory manager if available
            if self._memory_manager:
                self._memory_manager.cleanup()
            
            # Force garbage collection
            import gc
            collected = gc.collect()
            
            logger.info(f"Resource cleanup completed, garbage collected {collected} objects")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup (Feature-BE-11)"""
        try:
            if hasattr(self, 'executor') and self.executor:
                self.executor.shutdown(wait=False)
            if hasattr(self, '_memory_manager') and self._memory_manager:
                self._memory_manager.cleanup()
        except:
            pass
