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

from crewai import Agent, Task, Crew, Process
from crewai.agent import Agent as CrewAIAgent
from crewai.task import Task as CrewAITask
from crewai.crew import Crew as CrewAICrew
from langchain_openai import ChatOpenAI
CREWAI_AVAILABLE = True

# Import custom tools
from agents.crewai_tools import CREWAI_TOOLS, get_tool, get_all_tools

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
    agents: List<AgentInstance>
    tasks: List[CrewTask]
    crew: Optional[Any] = None
    status: str = "created"
    process_type: str = "sequential"
    manager_agent: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

class EnhancedAgentOrchestrator:
    """Enhanced CrewAI orchestrator for autonomous AI architecture tasks"""
    
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
            
        except Exception as e:
            logger.error(f"Failed to create agent instance {agent_type.value}: {e}")
            raise

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
                         metadata: Optional[Dict[str, Any]] = None) -> CrewTask:
        """Create a new task for execution"""
        
        task = CrewTask(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            agent_type=agent_type,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.task_queue.append(task)
        logger.info(f"Created task: {title} ({task.id})")
        
        return task

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
        """Execute the planning phase with CrewAI (no simulated progress)"""
        # Create planning agent
        planner = await self.create_agent_instance(AgentType.PLANNER, goal_text)
        # Emit agent start event
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
            planning_task = Task(
                description=f"Analyze the following goal and create a comprehensive plan: {goal_text}",
                agent=planner.crew_agent,
                expected_output="A detailed project plan with phases, tasks, and recommendations"
            )
            try:
                crew = Crew(
                    agents=[planner.crew_agent],
                    tasks=[planning_task],
                    process=Process.sequential,
                    verbose=True
                )
                # Run CrewAI task (blocking)
                result = await asyncio.get_event_loop().run_in_executor(None, crew.kickoff)
                # Emit output event
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
        # Mark agent as completed
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
        """Execute the architecture design phase (no simulated progress)"""
        architect = await self.create_agent_instance(AgentType.ARCHITECT, goal_text)
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
        # CrewAI-driven architecture design
        if CREWAI_AVAILABLE and architect.crew_agent:
            architecture_task = Task(
                description=f"Design a robust, scalable architecture for the following goal: {goal_text}",
                agent=architect.crew_agent,
                expected_output="A detailed architecture diagram and description"
            )
            try:
                crew = Crew(
                    agents=[architect.crew_agent],
                    tasks=[architecture_task],
                    process=Process.sequential,
                    verbose=True
                )
                result = await asyncio.get_event_loop().run_in_executor(None, crew.kickoff)
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "architecture",
                            "title": "System Architecture Design",
                            "content": str(result),
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": architect.id
                        }
                    }
                }
            except Exception as e:
                logger.error(f"Architecture phase failed: {e}")
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "error",
                            "title": "Architecture Phase Error",
                            "content": f"Architecture failed: {str(e)}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": architect.id
                        }
                    }
                }
        architect.status = "completed"
        architect.progress = 1.0
        architect.updated_at = datetime.utcnow().isoformat()
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

    async def _execute_implementation_phase(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the implementation planning phase (no simulated progress)"""
        coder = await self.create_agent_instance(AgentType.CODE_EXECUTOR, goal_text)
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
        if CREWAI_AVAILABLE and coder.crew_agent:
            implementation_task = Task(
                description=f"Plan and generate the implementation strategy for the following goal: {goal_text}",
                agent=coder.crew_agent,
                expected_output="A detailed implementation plan and code generation strategy"
            )
            try:
                crew = Crew(
                    agents=[coder.crew_agent],
                    tasks=[implementation_task],
                    process=Process.sequential,
                    verbose=True
                )
                result = await asyncio.get_event_loop().run_in_executor(None, crew.kickoff)
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "implementation",
                            "title": "Implementation Strategy",
                            "content": str(result),
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": coder.id
                        }
                    }
                }
            except Exception as e:
                logger.error(f"Implementation phase failed: {e}")
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "error",
                            "title": "Implementation Phase Error",
                            "content": f"Implementation failed: {str(e)}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": coder.id
                        }
                    }
                }
        coder.status = "completed"
        coder.progress = 1.0
        coder.updated_at = datetime.utcnow().isoformat()
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

    async def _execute_documentation_phase(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the documentation phase (no simulated progress)"""
        doc_agent = await self.create_agent_instance(AgentType.DOCUMENTATION_GENERATOR, goal_text)
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
        if CREWAI_AVAILABLE and doc_agent.crew_agent:
            documentation_task = Task(
                description=f"Generate comprehensive documentation for the following goal: {goal_text}",
                agent=doc_agent.crew_agent,
                expected_output="Comprehensive user and developer documentation"
            )
            try:
                crew = Crew(
                    agents=[doc_agent.crew_agent],
                    tasks=[documentation_task],
                    process=Process.sequential,
                    verbose=True
                )
                result = await asyncio.get_event_loop().run_in_executor(None, crew.kickoff)
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "documentation",
                            "title": "Documentation Generated",
                            "content": str(result),
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": doc_agent.id
                        }
                    }
                }
            except Exception as e:
                logger.error(f"Documentation phase failed: {e}")
                yield {
                    "type": "output_update",
                    "data": {
                        "output": {
                            "id": str(uuid.uuid4()),
                            "goalId": goal_id,
                            "type": "error",
                            "title": "Documentation Phase Error",
                            "content": f"Documentation failed: {str(e)}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent_id": doc_agent.id
                        }
                    }
                }
        doc_agent.status = "completed"
        doc_agent.progress = 1.0
        doc_agent.updated_at = datetime.utcnow().isoformat()
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

    # Maintain backward compatibility with existing process_goal method
    async def process_goal(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a goal using CrewAI orchestration only (no legacy fallback)"""
        if not CREWAI_AVAILABLE:
            logger.error("CrewAI is not available. Cannot process goal.")
            yield {
                "type": "goal_update",
                "goal_id": goal_id,
                "status": "error",
                "error": "CrewAI is not available. Please install CrewAI and dependencies."
            }
            return
        # Delegate to CrewAI-centric orchestration
        async for update in self.process_goal_with_crewai(goal_text, goal_id):
            yield update
    
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
    
    async def get_execution_metrics(self) -> Dict[str, Any]:
        """Get comprehensive execution metrics"""
        return {
            **self.execution_metrics,
            "active_agents": len(self.agent_instances),
            "active_sessions": len([s for s in self.crew_sessions.values() if s.status == "running"]),
            "total_sessions": len(self.crew_sessions),
            "queue_size": len(self.task_queue)
        }
    
    async def cleanup_resources(self) -> None:
        """Clean up completed sessions and unused resources"""
        try:
            # Clean up completed sessions older than 1 hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            sessions_to_remove = []
            for session_id, session in self.crew_sessions.items():
                if session.status in ["completed", "failed"] and session.completed_at:
                    completed_time = datetime.fromisoformat(session.completed_at.replace('Z', '+00:00'))
                    if completed_time < cutoff_time:
                        sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.crew_sessions[session_id]
                logger.debug(f"Cleaned up old session: {session_id}")
            
            # Clean up completed tasks
            self.completed_tasks = {k: v for k, v in self.completed_tasks.items() 
                                  if datetime.fromisoformat(v.completed_at or v.updated_at) > cutoff_time}
            
            # Clean up failed tasks older than 24 hours
            day_cutoff = datetime.utcnow() - timedelta(hours=24)
            self.failed_tasks = {k: v for k, v in self.failed_tasks.items() 
                               if datetime.fromisoformat(v.updated_at) > day_cutoff}
            
            logger.info("Resource cleanup completed")
            
        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator"""
        try:
            logger.info("Shutting down Enhanced Agent Orchestrator...")
            
            # Stop all running sessions
            for session in self.crew_sessions.values():
                if session.status == "running":
                    session.status = "stopped"
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
            # Final cleanup
            await self.cleanup_resources()
            
            logger.info("Enhanced Agent Orchestrator shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def push_to_github(self, commit_message: str = "Update orchestrator state") -> bool:
        """Push the current orchestrator state or code changes to GitHub (placeholder for integration)"""
        # NOTE: Actual implementation requires repo URL, authentication, and gitpython or subprocess
        try:
            import subprocess
            # Stage all changes
            subprocess.run(["git", "add", "-A"], check=True)
            # Commit
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            # Push
            subprocess.run(["git", "push"], check=True)
            logger.info("Successfully pushed orchestrator state to GitHub.")
            return True
        except Exception as e:
            logger.error(f"Failed to push to GitHub: {e}")
            return False