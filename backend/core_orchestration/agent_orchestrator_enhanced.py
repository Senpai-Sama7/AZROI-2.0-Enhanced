#!/usr/bin/env python3
"""
Enhanced CrewAI Agent Orchestrator for Autonomous AI Architect System
Production-ready orchestration with comprehensive agent management and coordination.
"""

import asyncio
import json
import logging
import uuid
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.agent import Agent as CrewAIAgent
    from crewai.task import Task as CrewAITask
    from crewai.crew import Crew as CrewAICrew
    CREWAI_AVAILABLE = True
except ImportError as e:
    CREWAI_AVAILABLE = False
    logging.warning(f"CrewAI not available: {e}")
    # Create dummy classes for when CrewAI is not available
    class Agent:
        def __init__(self, *args, **kwargs):
            self.role = kwargs.get('role', 'dummy')
            self.goal = kwargs.get('goal', 'dummy goal')
            self.backstory = kwargs.get('backstory', 'dummy backstory')
    
    class Task:
        def __init__(self, *args, **kwargs):
            self.description = kwargs.get('description', 'dummy task')
            self.agent = kwargs.get('agent')
    
    class Crew:
        def __init__(self, *args, **kwargs):
            self.agents = kwargs.get('agents', [])
            self.tasks = kwargs.get('tasks', [])
        
        def kickoff(self):
            return "CrewAI not available - dummy result"
    
    class Process:
        sequential = "sequential"
        hierarchical = "hierarchical"

# Import custom tools
try:
    from ..agents.crewai_tools import CREWAI_TOOLS, get_tool, get_all_tools
except ImportError:
    try:
        from agents.crewai_tools import CREWAI_TOOLS, get_tool, get_all_tools
    except ImportError:
        CREWAI_TOOLS = {}
        def get_tool(name): return None
        def get_all_tools(): return []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Legacy Agent class for backward compatibility
@dataclass
class Agent:
    """Legacy agent data structure for backward compatibility"""
    id: str
    name: str
    type: str
    status: str
    task: Optional[str] = None
    progress: float = 0.0
    created_at: str = ""
    updated_at: str = ""

class EnhancedAgentOrchestrator:
    """Enhanced CrewAI orchestrator for autonomous AI architecture tasks"""
    
    def __init__(self, config_loader=None, llm_router=None):
        self.config_loader = config_loader
        self.llm_router = llm_router
        self.max_concurrent_agents = 8
        self.max_concurrent_crews = 3
        
        # Legacy support
        self.active_agents: Dict[str, Agent] = {}
        
        # Enhanced CrewAI specific components
        self.agent_instances: Dict[str, AgentInstance] = {}
        self.crew_sessions: Dict[str, CrewSession] = {}
        self.task_queue: List[CrewTask] = []
        self.completed_tasks: Dict[str, CrewTask] = {}
        self.failed_tasks: Dict[str, CrewTask] = {}
        
        # Performance tracking
        self.execution_metrics: Dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0.0,
            "agent_utilization": {}
        }
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_agents)
        
        # Task execution locks
        self._execution_lock = asyncio.Lock()
        self._crew_lock = asyncio.Lock()
        
        # Event system for notifications
        self.event_callbacks: Dict[str, List[Callable]] = {}
        
        logger.info(f"Enhanced AgentOrchestrator initialized (CrewAI available: {CREWAI_AVAILABLE})")
    
    async def initialize(self) -> None:
        """Initialize the orchestrator and create default agents"""
        try:
            await self.reload_config()
            await self._initialize_default_agents()
            logger.info("Enhanced AgentOrchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def _initialize_default_agents(self) -> None:
        """Initialize default agent instances for each type"""
        default_agents = [
            AgentType.ARCHITECT,
            AgentType.PLANNER,
            AgentType.CODE_EXECUTOR,
            AgentType.CLOUD_DEPLOYER
        ]
        
        for agent_type in default_agents:
            try:
                await self.create_agent_instance(agent_type)
            except Exception as e:
                logger.warning(f"Failed to create default agent {agent_type}: {e}")
    
    async def reload_config(self):
        """Reload configuration from config loader"""
        try:
            if self.config_loader:
                config = await self.config_loader.get_config()
                self.max_concurrent_agents = config.get('max_concurrent_agents', 8)
                self.max_concurrent_crews = config.get('max_concurrent_crews', 3)
                logger.info(f"Configuration reloaded: max_concurrent_agents={self.max_concurrent_agents}")
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")

    async def create_agent_instance(self, 
                                  agent_type: AgentType, 
                                  goal_context: str = "",
                                  custom_tools: Optional[List[str]] = None) -> AgentInstance:
        """Create a new enhanced agent instance for a specific type"""
        try:
            agent_id = str(uuid.uuid4())
            
            # Get agent capabilities and tools
            capabilities = self._get_agent_capabilities(agent_type)
            tools = custom_tools or self._get_agent_tools(agent_type)
            
            instance = AgentInstance(
                id=agent_id,
                name=f"{agent_type.value.title().replace('_', ' ')} Agent",
                agent_type=agent_type,
                status="initializing",
                capabilities=capabilities,
                tools=tools
            )
            
            if CREWAI_AVAILABLE:
                # Create CrewAI agent based on type
                crew_agent = await self._create_enhanced_crew_agent(agent_type, goal_context, tools)
                instance.crew_agent = crew_agent
                instance.status = "ready"
            else:
                # Fallback to basic agent
                instance.status = "ready"
                
            self.agent_instances[agent_id] = instance
            
            # Initialize performance metrics
            self.execution_metrics["agent_utilization"][agent_id] = {
                "tasks_completed": 0,
                "total_execution_time": 0.0,
                "success_rate": 1.0,
                "average_task_time": 0.0
            }
            
            logger.info(f"Created enhanced agent instance: {agent_type.value} ({agent_id})")
            await self._emit_event("agent_created", {"agent_id": agent_id, "type": agent_type.value})
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create agent instance {agent_type.value}: {e}")
            raise

    def _get_agent_capabilities(self, agent_type: AgentType) -> List[str]:
        """Get capabilities for each agent type"""
        capabilities_map = {
            AgentType.ARCHITECT: [
                "system_design", "architecture_analysis", "technology_selection",
                "scalability_planning", "security_architecture", "performance_optimization"
            ],
            AgentType.PLANNER: [
                "project_planning", "task_decomposition", "resource_allocation",
                "timeline_estimation", "risk_assessment", "milestone_tracking"
            ],
            AgentType.CODE_EXECUTOR: [
                "code_generation", "refactoring", "debugging", "testing",
                "code_review", "documentation", "version_control"
            ],
            AgentType.CLOUD_DEPLOYER: [
                "infrastructure_provisioning", "deployment_automation", "monitoring_setup",
                "scaling_configuration", "security_hardening", "cost_optimization"
            ],
            AgentType.DATABASE_MANAGER: [
                "database_design", "query_optimization", "data_modeling",
                "backup_strategy", "performance_tuning", "migration_planning"
            ],
            AgentType.QUALITY_ASSURANCE: [
                "test_automation", "code_quality_analysis", "security_scanning",
                "performance_testing", "compliance_checking", "bug_tracking"
            ]
        }
        return capabilities_map.get(agent_type, [])
    
    def _get_agent_tools(self, agent_type: AgentType) -> List[str]:
        """Get tools required for each agent type"""
        tools_map = {
            AgentType.ARCHITECT: ["architecture_analyzer"],
            AgentType.CODE_EXECUTOR: ["code_generator"],
            AgentType.CLOUD_DEPLOYER: ["infrastructure_provisioner"],
            AgentType.QUALITY_ASSURANCE: ["quality_assurance"],
        }
        return tools_map.get(agent_type, [])

    async def _create_enhanced_crew_agent(self, agent_type: AgentType, goal_context: str, tools: List[str]) -> Any:
        """Create an enhanced CrewAI agent for the specified type with tools"""
        if not CREWAI_AVAILABLE:
            return None
            
        try:
            # Get LLM for the agent
            llm = None
            if self.llm_router:
                llm = await self.llm_router.get_llm("gemini-2.5-pro-preview-04-11")
            else:
                # Fallback to ChatOpenAI if available
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
                except ImportError:
                    logger.warning("No LLM available for CrewAI agent")
            
            # Get tools for the agent
            agent_tools = []
            for tool_name in tools:
                tool = get_tool(tool_name)
                if tool:
                    agent_tools.append(tool)
            
            # Agent configurations based on type
            agent_configs = {
                AgentType.ARCHITECT: {
                    "role": "Senior Software Architect",
                    "goal": "Design robust, scalable and maintainable software architectures",
                    "backstory": (
                        "You are an expert software architect with decades of experience "
                        "designing complex systems. You excel at choosing the right technologies, "
                        "considering scalability, maintenance, and best practices."
                    )
                },
                AgentType.PLANNER: {
                    "role": "Strategic Project Planner", 
                    "goal": "Create comprehensive project plans and break down complex goals",
                    "backstory": (
                        "You are a strategic planner who excels at breaking down complex "
                        "projects into manageable tasks and creating detailed roadmaps."
                    )
                },
                AgentType.CODE_EXECUTOR: {
                    "role": "Senior Software Developer",
                    "goal": "Write high-quality, tested, and maintainable code",
                    "backstory": (
                        "You are an experienced developer who writes clean, efficient code "
                        "following best practices and modern development methodologies."
                    )
                },
                AgentType.CLOUD_DEPLOYER: {
                    "role": "Cloud Infrastructure Specialist",
                    "goal": "Deploy and manage cloud infrastructure efficiently and securely",
                    "backstory": (
                        "You are a cloud expert specializing in AWS, Azure, and GCP "
                        "with deep knowledge of DevOps and infrastructure as code."
                    )
                },
                AgentType.DATABASE_MANAGER: {
                    "role": "Database Architect",
                    "goal": "Design and optimize database systems for performance and scalability",
                    "backstory": (
                        "You are a database expert with extensive experience in SQL and NoSQL "
                        "databases, optimization, and data modeling."
                    )
                },
                AgentType.DOCUMENTATION_GENERATOR: {
                    "role": "Technical Documentation Specialist",
                    "goal": "Create comprehensive and user-friendly documentation",
                    "backstory": (
                        "You specialize in creating clear, comprehensive technical documentation "
                        "that helps developers and users understand complex systems."
                    )
                },
                AgentType.QUALITY_ASSURANCE: {
                    "role": "Quality Assurance Engineer",
                    "goal": "Ensure code quality, security, and performance standards",
                    "backstory": (
                        "You are a QA expert who implements comprehensive testing strategies "
                        "and maintains high code quality standards across all projects."
                    )
                },
                AgentType.INFRASTRUCTURE_SPECIALIST: {
                    "role": "Infrastructure & DevOps Engineer",
                    "goal": "Design and manage scalable infrastructure and deployment pipelines",
                    "backstory": (
                        "You are an infrastructure specialist with expertise in cloud platforms, "
                        "container orchestration, and modern DevOps practices."
                    )
                }
            }
            
            config = agent_configs.get(agent_type)
            if not config:
                raise ValueError(f"No configuration found for agent type: {agent_type}")
            
            # Create the CrewAI agent with tools
            crew_agent = Agent(
                role=config["role"],
                goal=config["goal"] + f" Context: {goal_context}" if goal_context else config["goal"],
                backstory=config["backstory"],
                verbose=True,
                allow_delegation=True,
                llm=llm,
                tools=agent_tools
            )
            return crew_agent
            
        except Exception as e:
            logger.error(f"Failed to create CrewAI agent for {agent_type}: {e}")
            raise

    async def create_task(self, 
                         title: str, 
                         description: str, 
                         agent_type: AgentType,
                         dependencies: Optional[List[str]] = None,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         expected_output: str = "",
                         metadata: Optional[Dict[str, Any]] = None) -> CrewTask:
        """Create a new task for execution"""
        
        task = CrewTask(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            agent_type=agent_type,
            dependencies=dependencies or [],
            priority=priority,
            expected_output=expected_output,
            metadata=metadata or {}
        )
        
        self.task_queue.append(task)
        self.execution_metrics["total_tasks"] += 1
        logger.info(f"Created task: {title} ({task.id})")
        
        return task

    async def create_crew_session(self, 
                                name: str, 
                                description: str, 
                                agent_types: List[AgentType],
                                process_type: str = "sequential") -> CrewSession:
        """Create a new crew session for coordinated multi-agent workflows"""
        try:
            session_id = str(uuid.uuid4())
            
            # Create agent instances for the session
            agents = []
            for agent_type in agent_types:
                agent = await self.create_agent_instance(agent_type)
                agents.append(agent)
            
            session = CrewSession(
                id=session_id,
                name=name,
                description=description,
                agents=agents,
                tasks=[],
                process_type=process_type,
                status="created"
            )
            
            self.crew_sessions[session_id] = session
            logger.info(f"Created crew session: {name} ({session_id})")
            await self._emit_event("crew_session_created", {"session_id": session_id, "name": name})
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create crew session: {e}")
            raise

    async def execute_crew_session(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a crew session with coordinated agents"""
        if session_id not in self.crew_sessions:
            raise ValueError(f"Crew session not found: {session_id}")
        
        session = self.crew_sessions[session_id]
        
        async with self._crew_lock:
            try:
                session.status = "running"
                session.started_at = datetime.utcnow().isoformat()
                
                yield {
                    "type": "crew_session_update",
                    "session_id": session_id,
                    "status": "running",
                    "message": f"Starting crew session: {session.name}"
                }
                
                if CREWAI_AVAILABLE and session.tasks:
                    # Create CrewAI crew and tasks
                    crew_agents = [agent.crew_agent for agent in session.agents if agent.crew_agent]
                    crew_tasks = []
                    
                    for task in session.tasks:
                        # Find the appropriate agent for this task
                        task_agent = next(
                            (agent.crew_agent for agent in session.agents 
                             if agent.agent_type == task.agent_type and agent.crew_agent), 
                            None
                        )
                        
                        if task_agent:
                            crew_task = Task(
                                description=task.description,
                                agent=task_agent,
                                expected_output=task.expected_output or "Completed task output"
                            )
                            crew_tasks.append(crew_task)
                    
                    if crew_agents and crew_tasks:
                        # Create and execute the crew
                        crew = Crew(
                            agents=crew_agents,
                            tasks=crew_tasks,
                            process=Process.sequential if session.process_type == "sequential" else Process.hierarchical,
                            verbose=True
                        )
                        
                        session.crew = crew
                        
                        # Execute the crew asynchronously
                        result = await asyncio.get_event_loop().run_in_executor(
                            self.executor, crew.kickoff
                        )
                        
                        session.results["crew_output"] = str(result)
                        
                        yield {
                            "type": "crew_session_output",
                            "session_id": session_id,
                            "output": str(result)
                        }
                
                # Update session completion
                session.status = "completed"
                session.completed_at = datetime.utcnow().isoformat()
                
                yield {
                    "type": "crew_session_update",
                    "session_id": session_id,
                    "status": "completed",
                    "message": f"Crew session completed: {session.name}"
                }
                
                logger.info(f"Crew session completed: {session_id}")
                await self._emit_event("crew_session_completed", {"session_id": session_id})
                
            except Exception as e:
                session.status = "failed"
                error_msg = f"Crew session failed: {str(e)}"
                logger.error(error_msg)
                
                yield {
                    "type": "crew_session_update",
                    "session_id": session_id,
                    "status": "failed",
                    "error": error_msg
                }
                
                await self._emit_event("crew_session_failed", {"session_id": session_id, "error": error_msg})

    async def process_goal_with_crewai(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a goal using CrewAI orchestration"""
        
        async with self._execution_lock:
            try:
                logger.info(f"Starting CrewAI goal processing: {goal_id}")
                
                # Initial status update
                yield {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "analyzing"
                }
                
                # Phase 1: Planning and Analysis
                async for update in self._execute_planning_phase(goal_text, goal_id):
                    yield update
                
                # Phase 2: Architecture Design
                async for update in self._execute_architecture_phase(goal_text, goal_id):
                    yield update
                
                # Phase 3: Implementation Planning
                async for update in self._execute_implementation_phase(goal_text, goal_id):
                    yield update
                
                # Phase 4: Documentation and Deployment
                async for update in self._execute_documentation_phase(goal_text, goal_id):
                    yield update
                
                # Final completion
                yield {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "completed"
                }
                
                logger.info(f"CrewAI goal processing completed: {goal_id}")
                
            except Exception as e:
                logger.error(f"CrewAI goal processing failed for {goal_id}: {e}")
                yield {
                    "type": "goal_update",
                    "goal_id": goal_id,
                    "status": "error",
                    "error": str(e)
                }

    async def _execute_planning_phase(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the planning phase with CrewAI"""
        
        # Create planning agent
        planner = await self.create_agent_instance(AgentType.PLANNER, goal_text)
        
        # Update status
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
        
        if CREWAI_AVAILABLE and planner.crew_agent:
            # Create planning task
            planning_task = Task(
                description=f"Analyze the following goal and create a comprehensive plan: {goal_text}",
                agent=planner.crew_agent,
                expected_output="A detailed project plan with phases, tasks, and recommendations"
            )
            
            # Execute planning
            try:
                crew = Crew(
                    agents=[planner.crew_agent],
                    tasks=[planning_task],
                    process=Process.sequential,
                    verbose=True
                )
                
                # Simulate progress updates
                for progress in [0.3, 0.6, 0.9]:
                    await asyncio.sleep(1)
                    yield {
                        "type": "agent_update", 
                        "data": {
                            "agent": {
                                "id": planner.id,
                                "name": planner.name,
                                "type": planner.agent_type.value,
                                "status": "active",
                                "task": "Analyzing and planning the goal",
                                "progress": progress,
                                "created_at": planner.created_at,
                                "updated_at": datetime.utcnow().isoformat()
                            }
                        }
                    }
                
                # Execute the crew (note: this is synchronous in CrewAI)
                result = await asyncio.get_event_loop().run_in_executor(
                    None, crew.kickoff
                )
                
                # Generate output
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "planning",
                            "title": "Project Planning Complete",
                            "content": str(result),
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": planner.id
                        }
                    }
                }
                
            except Exception as e:
                logger.error(f"Planning phase failed: {e}")
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "error",
                            "title": "Planning Phase Error",
                            "content": f"Planning failed: {str(e)}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": planner.id
                        }
                    }
                }
        else:
            # Fallback to basic planning
            await asyncio.sleep(2)
            yield {
                "type": "output_update",
                "data": {
                    "output": {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "type": "planning",
                        "title": "Basic Planning Complete",
                        "content": f"Basic analysis completed for: {goal_text}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_id": planner.id
                    }
                }
            }
        
        # Complete planning
        planner.status = "completed"
        planner.progress = 1.0
        planner.updated_at = datetime.utcnow().isoformat()
        
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

    async def _execute_architecture_phase(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the architecture design phase"""
        
        # Create architect agent
        architect = await self.create_agent_instance(AgentType.ARCHITECT, goal_text)
        
        # Update status
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
        for progress in [0.25, 0.5, 0.75, 1.0]:
            await asyncio.sleep(1.5)
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": architect.id,
                        "name": architect.name,
                        "type": architect.agent_type.value,
                        "status": "active" if progress < 1.0 else "completed",
                        "task": "Designing system architecture",
                        "progress": progress,
                        "created_at": architect.created_at,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            }
        
        # Generate architecture output
        yield {
            "type": "output_update",
            "data": {
                "output": {
                    "id": str(uuid.uuid4()),
                    "goalId": goal_id,
                    "type": "architecture",
                    "title": "System Architecture Design",
                    "content": f"Architecture design completed for: {goal_text}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": architect.id
                }
            }
        }

    async def _execute_implementation_phase(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the implementation planning phase"""
        
        # Create code execution agent
        coder = await self.create_agent_instance(AgentType.CODE_EXECUTOR, goal_text)
        
        # Update status and simulate work
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
        
        # Simulate implementation planning
        for progress in [0.33, 0.66, 1.0]:
            await asyncio.sleep(1)
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": coder.id,
                        "name": coder.name,
                        "type": coder.agent_type.value,
                        "status": "active" if progress < 1.0 else "completed",
                        "task": "Planning implementation strategy",
                        "progress": progress,
                        "created_at": coder.created_at,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            }
        
        # Generate implementation output
        yield {
            "type": "output_update",
            "data": {
                "output": {
                    "id": str(uuid.uuid4()),
                    "goalId": goal_id,
                    "type": "implementation",
                    "title": "Implementation Strategy",
                    "content": f"Implementation plan created for: {goal_text}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": coder.id
                }
            }
        }

    async def _execute_documentation_phase(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the documentation phase"""
        
        # Create documentation agent
        doc_agent = await self.create_agent_instance(AgentType.DOCUMENTATION_GENERATOR, goal_text)
        
        # Update status and simulate work
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
        for progress in [0.5, 1.0]:
            await asyncio.sleep(1)
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": doc_agent.id,
                        "name": doc_agent.name,
                        "type": doc_agent.agent_type.value,
                        "status": "active" if progress < 1.0 else "completed",
                        "task": "Generating documentation",
                        "progress": progress,
                        "created_at": doc_agent.created_at,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            }
        
        # Generate documentation output
        yield {
            "type": "output_update",
            "data": {
                "output": {
                    "id": str(uuid.uuid4()),
                    "goalId": goal_id,
                    "type": "documentation",
                    "title": "Documentation Generated",
                    "content": f"Documentation created for: {goal_text}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": doc_agent.id
                }
            }
        }

    # Maintain backward compatibility with existing process_goal method
    async def process_goal(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a goal using coordinated agents"""
        try:
            logger.info(f"Starting goal processing: {goal_id}")
            
            # Initial status update
            yield {
                "type": "goal_update",
                "goal_id": goal_id,
                "status": "analyzing"
            }
            
            # Use enhanced CrewAI processing if available
            if CREWAI_AVAILABLE:
                async for update in self.process_goal_with_crewai(goal_text, goal_id):
                    yield update
            else:
                # Fallback to basic processing
                async for update in self._process_goal_basic(goal_text, goal_id):
                    yield update
            
        except Exception as e:
            logger.error(f"Goal processing failed for {goal_id}: {e}")
            yield {
                "type": "goal_update",
                "goal_id": goal_id,
                "status": "error",
                "error": str(e)
            }

    async def _process_goal_basic(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Basic goal processing fallback"""
        # Create planning agent
        planner_agent = Agent(
            id=str(uuid.uuid4()),
            name="Planner Agent",
            type="planner",
            status="active",
            task=f"Analyzing goal: {goal_text}",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        self.active_agents[planner_agent.id] = planner_agent
        
        yield {
            "type": "agent_update",
            "data": {
                "agent": {
                    "id": planner_agent.id,
                    "name": planner_agent.name,
                    "type": planner_agent.type,
                    "status": planner_agent.status,
                    "task": planner_agent.task,
                    "progress": planner_agent.progress,
                    "created_at": planner_agent.created_at,
                    "updated_at": planner_agent.updated_at
                }
            }
        }
        
        # Simulate planning phase
        await asyncio.sleep(1)
        planner_agent.progress = 0.5
        planner_agent.updated_at = datetime.utcnow().isoformat()
        
        yield {
            "type": "agent_update",
            "data": {
                "agent": {
                    "id": planner_agent.id,
                    "name": planner_agent.name,
                    "type": planner_agent.type,
                    "status": planner_agent.status,
                    "task": planner_agent.task,
                    "progress": planner_agent.progress,
                    "created_at": planner_agent.created_at,
                    "updated_at": planner_agent.updated_at
                }
            }
        }
        
        # Generate output
        yield {
            "type": "output_update",
            "data": {
                "output": {
                    "id": str(uuid.uuid4()),
                    "goalId": goal_id,
                    "type": "analysis",
                    "title": "Goal Analysis Complete",
                    "content": f"Successfully analyzed goal: {goal_text}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": planner_agent.id
                }
            }
        }
        
        # Complete planning
        planner_agent.progress = 1.0
        planner_agent.status = "completed"
        planner_agent.updated_at = datetime.utcnow().isoformat()
        
        yield {
            "type": "agent_update",
            "data": {
                "agent": {
                    "id": planner_agent.id,
                    "name": planner_agent.name,
                    "type": planner_agent.type,
                    "status": planner_agent.status,
                    "task": planner_agent.task,
                    "progress": planner_agent.progress,
                    "created_at": planner_agent.created_at,
                    "updated_at": planner_agent.updated_at
                }
            }
        }
        
        # Final status update
        yield {
            "type": "goal_update",
            "goal_id": goal_id,
            "status": "completed"
        }

    async def add_task_to_session(self, session_id: str, task: CrewTask) -> bool:
        """Add a task to an existing crew session"""
        if session_id not in self.crew_sessions:
            return False
        
        session = self.crew_sessions[session_id]
        if session.status != "created":
            logger.warning(f"Cannot add task to session {session_id} with status {session.status}")
            return False
        
        session.tasks.append(task)
        logger.info(f"Added task {task.id} to session {session_id}")
        return True
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a crew session"""
        if session_id not in self.crew_sessions:
            return None
        
        session = self.crew_sessions[session_id]
        return {
            "id": session.id,
            "name": session.name,
            "status": session.status,
            "agent_count": len(session.agents),
            "task_count": len(session.tasks),
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "results": session.results
        }
    
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
    
    def register_event_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for specific event types"""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of active agents"""
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type,
                "status": agent.status,
                "task": agent.task,
                "progress": agent.progress,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            }
            for agent in self.active_agents.values()
        ]
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent"""
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            agent.status = "stopped"
            agent.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Agent stopped: {agent_id}")
            return True
        return False
    
    async def get_execution_metrics(self) -> Dict[str, Any]:
        """Get comprehensive execution metrics"""
        return {
            **self.execution_metrics,
            "active_agents": len(self.agent_instances),
            "active_sessions": len([s for s in self.crew_sessions.values() if s.status == "running"]),
            "total_sessions": len(self.crew_sessions),
            "queue_size": len(self.task_queue)
        }
    
    # Agent management methods for API compatibility
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific agent"""
        if agent_id in self.agent_instances:
            agent = self.agent_instances[agent_id]
            return {
                "id": agent.id,
                "name": agent.name,
                "type": agent.agent_type.value,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "tools": agent.tools,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            }
        
        # Check legacy active agents
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            return {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type,
                "status": agent.status,
                "task": agent.task,
                "progress": agent.progress,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            }
        
        return None

    async def pause_agent(self, agent_id: str) -> bool:
        """Pause a specific agent"""
        if agent_id in self.agent_instances:
            agent = self.agent_instances[agent_id]
            if agent.status in ["ready", "active"]:
                agent.status = "paused"
                agent.updated_at = datetime.utcnow().isoformat()
                logger.info(f"Agent paused: {agent_id}")
                return True
        
        # Check legacy active agents
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            if agent.status in ["ready", "active"]:
                agent.status = "paused"
                agent.updated_at = datetime.utcnow().isoformat()
                logger.info(f"Legacy agent paused: {agent_id}")
                return True
        
        return False

    async def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent"""
        if agent_id in self.agent_instances:
            agent = self.agent_instances[agent_id]
            if agent.status == "paused":
                agent.status = "ready"
                agent.updated_at = datetime.utcnow().isoformat()
                logger.info(f"Agent resumed: {agent_id}")
                return True
        
        # Check legacy active agents
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            if agent.status == "paused":
                agent.status = "active"
                agent.updated_at = datetime.utcnow().isoformat()
                logger.info(f"Legacy agent resumed: {agent_id}")
                return True
        
        return False

    async def reset_agent(self, agent_id: str) -> bool:
        """Reset an agent to initial state"""
        if agent_id in self.agent_instances:
            agent = self.agent_instances[agent_id]
            agent.status = "ready"
            agent.updated_at = datetime.utcnow().isoformat()
            
            # Reset metrics for this agent
            if agent_id in self.execution_metrics["agent_utilization"]:
                self.execution_metrics["agent_utilization"][agent_id].update({
                    "tasks_completed": 0,
                    "total_execution_time": 0.0,
                    "success_rate": 1.0,
                    "average_task_time": 0.0
                })
            
            logger.info(f"Agent reset: {agent_id}")
            return True
        
        # Check legacy active agents
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            agent.status = "ready"
            agent.progress = 0.0
            agent.task = ""
            agent.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Legacy agent reset: {agent_id}")
            return True
        
        return False

    # Task management methods for API compatibility
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific task"""
        # Check task queue
        for task in self.task_queue:
            if task.id == task_id:
                return {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "agent_type": task.agent_type.value,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "progress": task.progress,
                    "dependencies": task.dependencies,
                    "expected_output": task.expected_output,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                    "metadata": task.metadata
                }
        
        # Check completed tasks
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "agent_type": task.agent_type.value,
                "status": task.status.value,
                "priority": task.priority.value,
                "progress": task.progress,
                "dependencies": task.dependencies,
                "expected_output": task.expected_output,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "completed_at": task.completed_at,
                "result": task.result,
                "metadata": task.metadata
            }
        
        # Check failed tasks
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "agent_type": task.agent_type.value,
                "status": task.status.value,
                "priority": task.priority.value,
                "progress": task.progress,
                "dependencies": task.dependencies,
                "expected_output": task.expected_output,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "error": task.error,
                "metadata": task.metadata
            }
        
        return None

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            
            # Move from failed to queue and reset status
            task.status = TaskStatus.PENDING
            task.progress = 0.0
            task.error = ""
            task.updated_at = datetime.utcnow().isoformat()
            
            # Move back to task queue
            self.task_queue.append(task)
            del self.failed_tasks[task_id]
            
            logger.info(f"Task queued for retry: {task_id}")
            return True
        
        return False

    async def skip_task(self, task_id: str) -> bool:
        """Skip a task"""
        # Find task in queue
        for i, task in enumerate(self.task_queue):
            if task.id == task_id:
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.utcnow().isoformat()
                task.result = "Task skipped by user"
                
                # Move to completed tasks as cancelled
                self.completed_tasks[task_id] = task
                self.task_queue.pop(i)
                
                logger.info(f"Task skipped: {task_id}")
                return True
        
        return False

    async def prioritize_task(self, task_id: str) -> bool:
        """Prioritize a task by moving it to front of queue"""
        for i, task in enumerate(self.task_queue):
            if task.id == task_id:
                # Move task to front of queue
                prioritized_task = self.task_queue.pop(i)
                prioritized_task.priority = TaskPriority.CRITICAL
                prioritized_task.updated_at = datetime.utcnow().isoformat()
                self.task_queue.insert(0, prioritized_task)
                
                logger.info(f"Task prioritized: {task_id}")
                return True
        
        return False

    async def get_task_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a task execution (fallback implementation)"""
        # For now, use task_id as execution_id
        task_data = await self.get_task(execution_id)
        if task_data:
            return {
                "execution_id": execution_id,
                "task_id": execution_id,
                "status": task_data["status"],
                "started_at": task_data.get("created_at"),
                "completed_at": task_data.get("completed_at"),
                "result": task_data.get("result"),
                "error": task_data.get("error"),
                "progress": task_data["progress"]
            }
        
        return None

    # Session management methods for API compatibility
    async def pause_crew_session(self, session_id: str) -> bool:
        """Pause a crew session"""
        if session_id not in self.crew_sessions:
            return False
        
        session = self.crew_sessions[session_id]
        if session.status == "running":
            session.status = "paused"
            logger.info(f"Crew session paused: {session_id}")
            return True
        
        return False

    async def stop_crew_session(self, session_id: str) -> bool:
        """Stop a crew session"""
        if session_id not in self.crew_sessions:
            return False
        
        session = self.crew_sessions[session_id]
        if session.status in ["running", "paused"]:
            session.status = "stopped"
            session.completed_at = datetime.utcnow().isoformat()
            logger.info(f"Crew session stopped: {session_id}")
            return True
        
        return False

    async def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a crew session"""
        if session_id not in self.crew_sessions:
            return None
        
        session = self.crew_sessions[session_id]
        
        # Calculate basic metrics
        total_tasks = len(session.tasks)
        completed_tasks = sum(1 for task in session.tasks if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in session.tasks if task.status == TaskStatus.FAILED)
        
        start_time = datetime.fromisoformat(session.started_at) if session.started_at else datetime.utcnow()
        current_time = datetime.utcnow()
        if session.completed_at:
            end_time = datetime.fromisoformat(session.completed_at)
            duration = (end_time - start_time).total_seconds()
        else:
            duration = (current_time - start_time).total_seconds()
        
        return {
            "session_id": session_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "pending_tasks": total_tasks - completed_tasks - failed_tasks,
            "success_rate": completed_tasks / max(1, completed_tasks + failed_tasks),
            "duration_seconds": duration,
            "agent_count": len(session.agents),
            "status": session.status
        }

    async def get_session_collaborations(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get collaboration data for a crew session"""
        if session_id not in self.crew_sessions:
            return None
        
        session = self.crew_sessions[session_id]
        
        # Generate collaboration data based on agent interactions
        collaborations = []
        for i, agent1 in enumerate(session.agents):
            for j, agent2 in enumerate(session.agents[i+1:], i+1):
                # Find tasks that might involve collaboration
                shared_tasks = [
                    task for task in session.tasks 
                    if task.agent_type in [agent1.agent_type, agent2.agent_type]
                ]
                
                if shared_tasks:
                    collaborations.append({
                        "agent1_id": agent1.id,
                        "agent1_type": agent1.agent_type.value,
                        "agent2_id": agent2.id,
                        "agent2_type": agent2.agent_type.value,
                        "shared_tasks": len(shared_tasks),
                        "interaction_type": "task_collaboration"
                    })
        
        return {
            "session_id": session_id,
            "collaborations": collaborations,
            "total_interactions": len(collaborations)
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator"""
        try:
            logger.info("Shutting down Enhanced Agent Orchestrator...")
            
            # Stop all active sessions
            for session_id in list(self.crew_sessions.keys()):
                await self.stop_crew_session(session_id)
            
            # Clear all collections
            self.agent_instances.clear()
            self.active_agents.clear()
            self.task_queue.clear()
            self.completed_tasks.clear()
            self.failed_tasks.clear()
            self.crew_sessions.clear()
            
            logger.info("Enhanced Agent Orchestrator shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during orchestrator shutdown: {e}")
            
    async def cleanup_resources(self) -> None:
        """Clean up completed sessions and unused resources"""
        try:
            current_time = datetime.utcnow()
            sessions_to_remove = []
            
            # Find completed sessions older than 1 hour
            for session_id, session in self.crew_sessions.items():
                if session.status in ["completed", "failed"] and session.completed_at:
                    completed_time = datetime.fromisoformat(session.completed_at)
                    if (current_time - completed_time).total_seconds() > 3600:  # 1 hour
                        sessions_to_remove.append(session_id)
            
            # Remove old completed sessions
            for session_id in sessions_to_remove:
                del self.crew_sessions[session_id]
                logger.info(f"Cleaned up completed session: {session_id}")
            
            # Clean up completed tasks older than 6 hours
            tasks_to_remove = []
            for task_id, task in self.completed_tasks.items():
                if task.completed_at:
                    completed_time = datetime.fromisoformat(task.completed_at)
                    if (current_time - completed_time).total_seconds() > 21600:  # 6 hours
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.completed_tasks[task_id]
            
            logger.info(f"Resource cleanup complete. Removed {len(sessions_to_remove)} sessions and {len(tasks_to_remove)} tasks")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
            
    async def cleanup_completed_agents(self) -> None:
        """Clean up agents that have completed their tasks"""
        try:
            agents_to_remove = []
            
            # Find agents with completed status
            for agent_id, agent in self.agent_instances.items():
                if agent.status == "completed":
                    agents_to_remove.append(agent_id)
            
            # Also check legacy active_agents
            for agent_id, agent in self.active_agents.items():
                if agent.status == "completed":
                    agents_to_remove.append(agent_id)
            
            # Remove completed agents
            for agent_id in agents_to_remove:
                if agent_id in self.agent_instances:
                    del self.agent_instances[agent_id]
                if agent_id in self.active_agents:
                    del self.active_agents[agent_id]
                logger.info(f"Cleaned up completed agent: {agent_id}")
            
            logger.info(f"Agent cleanup complete. Removed {len(agents_to_remove)} completed agents")
            
        except Exception as e:
            logger.error(f"Error during agent cleanup: {e}")
