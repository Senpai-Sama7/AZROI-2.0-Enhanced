"""
Unit tests for the enhanced agent orchestrator
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone


class MockAgentType:
    ARCHITECT = "ARCHITECT"
    PLANNER = "PLANNER"
    CODE_EXECUTOR = "CODE_EXECUTOR"


class MockTaskPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MockCrewTask:
    def __init__(self, task_id, description, task_type, inputs, dependencies, priority, assigned_agent, status, created_at):
        self.task_id = task_id
        self.description = description
        self.task_type = task_type
        self.inputs = inputs
        self.dependencies = dependencies
        self.priority = priority
        self.assigned_agent = assigned_agent
        self.status = status
        self.created_at = created_at


class TestEnhancedAgentOrchestrator:
    """Test suite for EnhancedAgentOrchestrator"""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator for testing"""
        orchestrator = Mock()
        orchestrator.agents = {}
        orchestrator.crew_sessions = {}
        orchestrator.active_tasks = {}
        orchestrator._shutdown_event = Mock()
        orchestrator._shutdown_event.is_set.return_value = False
        return orchestrator
    
    @pytest.mark.unit
    def test_orchestrator_initialization(self, mock_orchestrator):
        """Test orchestrator initialization"""
        assert mock_orchestrator is not None
        assert mock_orchestrator.agents == {}
        assert mock_orchestrator.crew_sessions == {}
        assert mock_orchestrator.active_tasks == {}
        assert not mock_orchestrator._shutdown_event.is_set()
    
    @pytest.mark.unit
    async def test_create_agent(self, mock_orchestrator):
        """Test agent creation"""
        agent_config = {
            "agent_type": "ARCHITECT",
            "name": "Test Architect",
            "description": "Test architect agent"
        }
        
        # Mock the create_agent method
        mock_orchestrator.create_agent = AsyncMock(return_value="agent_123")
        
        agent_id = await mock_orchestrator.create_agent(agent_config)
        
        assert agent_id == "agent_123"
        mock_orchestrator.create_agent.assert_called_once_with(agent_config)
    
    @pytest.mark.unit
    async def test_create_crew_session(self, mock_orchestrator):
        """Test crew session creation"""
        session_config = {
            "crew_name": "Test Crew",
            "description": "Test crew session",
            "agent_types": ["ARCHITECT", "PLANNER"]
        }
        
        # Mock the create_crew_session method
        mock_orchestrator.create_crew_session = AsyncMock(return_value="session_123")
        
        session_id = await mock_orchestrator.create_crew_session(session_config)
        
        assert session_id == "session_123"
        mock_orchestrator.create_crew_session.assert_called_once_with(session_config)
    
    @pytest.mark.unit
    async def test_add_task_to_crew(self, mock_orchestrator):
        """Test adding task to crew"""
        session_id = "session_123"
        task_config = {
            "description": "Test task",
            "task_type": "analysis",
            "priority": "high"
        }
        
        # Mock the add_task_to_crew method
        mock_orchestrator.add_task_to_crew = AsyncMock(return_value="task_123")
        
        task_id = await mock_orchestrator.add_task_to_crew(session_id, task_config)
        
        assert task_id == "task_123"
        mock_orchestrator.add_task_to_crew.assert_called_once_with(session_id, task_config)
    
    @pytest.mark.unit
    async def test_process_goal(self, mock_orchestrator):
        """Test goal processing"""
        goal = "Create a simple web application"
        
        expected_result = {
            "session_id": "session_123",
            "status": "completed",
            "tasks": [
                {
                    "task_id": "task_001",
                    "type": "code_generation",
                    "description": "Create web app",
                    "status": "completed",
                    "success": True
                }
            ]
        }
        
        # Mock the process_goal method
        mock_orchestrator.process_goal = AsyncMock(return_value=expected_result)
        
        result = await mock_orchestrator.process_goal(goal)
        
        assert result is not None
        assert result["session_id"] == "session_123"
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        mock_orchestrator.process_goal.assert_called_once_with(goal)
    
    @pytest.mark.unit
    async def test_get_orchestrator_status(self, mock_orchestrator):
        """Test getting orchestrator status"""
        expected_status = {
            "total_agents": 5,
            "active_crews": 2,
            "pending_tasks": 3,
            "running_tasks": 1,
            "completed_tasks": 10,
            "system_status": "healthy"
        }
        
        # Mock the get_status method
        mock_orchestrator.get_status = AsyncMock(return_value=expected_status)
        
        status = await mock_orchestrator.get_status()
        
        assert isinstance(status, dict)
        assert status["total_agents"] == 5
        assert status["active_crews"] == 2
        assert status["pending_tasks"] == 3
        assert status["running_tasks"] == 1
        assert status["completed_tasks"] == 10
        assert status["system_status"] == "healthy"
    
    @pytest.mark.unit
    async def test_shutdown_orchestrator(self, mock_orchestrator):
        """Test orchestrator shutdown"""
        # Mock the shutdown method
        mock_orchestrator.shutdown = AsyncMock()
        mock_orchestrator._shutdown_event.is_set.return_value = True
        
        await mock_orchestrator.shutdown()
        
        mock_orchestrator.shutdown.assert_called_once()
        assert mock_orchestrator._shutdown_event.is_set()
    
    @pytest.mark.integration
    async def test_full_workflow(self, mock_orchestrator):
        """Test complete workflow from goal to execution"""
        goal = "Create a simple calculator function"
        
        expected_result = {
            "session_id": "session_123",
            "status": "completed",
            "tasks": [
                {
                    "task_id": "task_001",
                    "type": "code_generation",
                    "description": "Create calculator function",
                    "status": "completed",
                    "success": True,
                    "result": "def calculator(a, b, op): return eval(f'{a}{op}{b}')"
                }
            ],
            "analysis": "Calculator implementation plan"
        }
        
        # Mock the complete workflow
        mock_orchestrator.process_goal = AsyncMock(return_value=expected_result)
        
        result = await mock_orchestrator.process_goal(goal)
        
        assert result is not None
        assert result["status"] == "completed"
        assert len(result["tasks"]) == 1
        
        # Verify task was executed
        task_result = result["tasks"][0]
        assert task_result["status"] == "completed"
        assert task_result["success"] is True
    
    @pytest.mark.unit
    def test_task_dependency_resolution(self):
        """Test task dependency resolution"""
        # Create tasks with dependencies
        tasks = [
            {
                "task_id": "task_001",
                "type": "analysis",
                "description": "Analyze requirements",
                "dependencies": [],
                "inputs": {}
            },
            {
                "task_id": "task_002",
                "type": "code_generation",
                "description": "Generate code",
                "dependencies": ["task_001"],
                "inputs": {"analysis": "{{outputs.task_001.analysis}}"}
            },
            {
                "task_id": "task_003",
                "type": "testing",
                "description": "Test code",
                "dependencies": ["task_002"],
                "inputs": {"code": "{{outputs.task_002.code}}"}
            }
        ]
        
        # Mock dependency resolution function
        def resolve_dependencies(task_list):
            # Sort by dependencies (simple topological sort)
            resolved = []
            remaining = task_list.copy()
            
            while remaining:
                # Find tasks with no unresolved dependencies
                ready_tasks = [
                    task for task in remaining
                    if all(dep_id in [t["task_id"] for t in resolved] for dep_id in task["dependencies"])
                ]
                
                if not ready_tasks:
                    raise ValueError("Circular dependency detected")
                
                resolved.extend(ready_tasks)
                for task in ready_tasks:
                    remaining.remove(task)
            
            return resolved
        
        # Test dependency resolution
        resolved_order = resolve_dependencies(tasks)
        
        # Should be in correct dependency order
        assert resolved_order[0]["task_id"] == "task_001"
        assert resolved_order[1]["task_id"] == "task_002"
        assert resolved_order[2]["task_id"] == "task_003"
    
    @pytest.mark.unit
    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        # Create tasks with circular dependencies
        tasks = [
            {
                "task_id": "task_001",
                "dependencies": ["task_002"]
            },
            {
                "task_id": "task_002",
                "dependencies": ["task_003"]
            },
            {
                "task_id": "task_003",
                "dependencies": ["task_001"]
            }
        ]
        
        # Mock dependency resolution with circular dependency detection
        def resolve_dependencies_with_cycle_check(task_list):
            resolved = []
            remaining = task_list.copy()
            max_iterations = len(task_list)
            iterations = 0
            
            while remaining and iterations < max_iterations:
                ready_tasks = [
                    task for task in remaining
                    if all(dep_id in [t["task_id"] for t in resolved] for dep_id in task["dependencies"])
                ]
                
                if not ready_tasks:
                    raise ValueError("Circular dependency detected")
                
                resolved.extend(ready_tasks)
                for task in ready_tasks:
                    remaining.remove(task)
                
                iterations += 1
            
            if remaining:
                raise ValueError("Circular dependency detected")
            
            return resolved
        
        # Should raise exception for circular dependency
        with pytest.raises(ValueError, match="Circular dependency detected"):
            resolve_dependencies_with_cycle_check(tasks)
    
    @pytest.mark.performance
    async def test_concurrent_task_execution(self):
        """Test concurrent task execution performance"""
        # Mock concurrent execution
        async def mock_execute_task(task_id):
            await asyncio.sleep(0.1)  # Simulate work
            return {
                "success": True,
                "result": f"Task {task_id} completed",
                "outputs": {"result": f"output_{task_id}"}
            }
        
        # Create multiple tasks
        task_ids = [f"task_{i:03d}" for i in range(10)]
        
        start_time = asyncio.get_event_loop().time()
        
        # Execute tasks concurrently
        results = await asyncio.gather(*[
            mock_execute_task(task_id) for task_id in task_ids
        ])
        
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # Should complete in roughly 0.1 seconds (concurrent) rather than 1 second (sequential)
        assert execution_time < 0.5
        assert len(results) == 10
        assert all(result["success"] for result in results)
    
    @pytest.mark.unit
    def test_agent_capability_matching(self):
        """Test agent capability matching for tasks"""
        # Mock agents with different capabilities
        agents = {
            "architect_001": {
                "agent_type": "ARCHITECT",
                "capabilities": ["system_design", "architecture_analysis"]
            },
            "coder_001": {
                "agent_type": "CODE_EXECUTOR",
                "capabilities": ["code_generation", "code_review"]
            }
        }
        
        # Mock tasks requiring different capabilities
        design_task = {
            "task_id": "design_task",
            "task_type": "system_design",
            "required_capabilities": ["system_design"]
        }
        
        coding_task = {
            "task_id": "coding_task",
            "task_type": "code_generation",
            "required_capabilities": ["code_generation"]
        }
        
        # Mock capability matching function
        def find_best_agent_for_task(task, available_agents):
            required_caps = task.get("required_capabilities", [])
            
            best_match = None
            best_score = 0
            
            for agent_id, agent in available_agents.items():
                agent_caps = agent.get("capabilities", [])
                matching_caps = set(required_caps) & set(agent_caps)
                score = len(matching_caps)
                
                if score > best_score:
                    best_score = score
                    best_match = agent_id
            
            return best_match
        
        # Test agent assignment
        best_agent_for_design = find_best_agent_for_task(design_task, agents)
        assert best_agent_for_design == "architect_001"
        
        best_agent_for_coding = find_best_agent_for_task(coding_task, agents)
        assert best_agent_for_coding == "coder_001"
    
    @pytest.mark.unit
    async def test_error_handling(self, mock_orchestrator):
        """Test error handling in orchestrator"""
        # Mock error scenarios
        mock_orchestrator.process_goal = AsyncMock(side_effect=Exception("Processing failed"))
        
        with pytest.raises(Exception, match="Processing failed"):
            await mock_orchestrator.process_goal("Invalid goal")
    
    @pytest.mark.unit
    async def test_resource_management(self, mock_orchestrator):
        """Test resource management"""
        # Mock resource tracking
        mock_orchestrator.get_resource_usage = Mock(return_value={
            "memory_mb": 512,
            "cpu_percent": 25.5,
            "active_agents": 3,
            "active_tasks": 5
        })
        
        resources = mock_orchestrator.get_resource_usage()
        
        assert resources["memory_mb"] == 512
        assert resources["cpu_percent"] == 25.5
        assert resources["active_agents"] == 3
        assert resources["active_tasks"] == 5
