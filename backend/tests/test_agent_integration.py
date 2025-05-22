#!/usr/bin/env python3

import asyncio
import json
import logging
import pytest
from unittest.mock import MagicMock, patch

from backend.core_orchestration.agent_orchestrator import AgentOrchestrator
from backend.core_orchestration.monitoring_system import MonitoringSystem
from backend.tools.memory_manager import MemoryManager
from backend.core_orchestration.llm_router import LLMRouter
from backend.core_orchestration.safety_sandbox import SafetySandbox

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
class TestAgentIntegration:
    """Integration tests for agent interactions through the orchestrator."""
    
    async def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock dependencies
        self.mock_llm_router = MagicMock(spec=LLMRouter)
        self.mock_memory_manager = MagicMock(spec=MemoryManager)
        self.mock_monitoring_system = MagicMock(spec=MonitoringSystem)
        self.mock_safety_sandbox = MagicMock(spec=SafetySandbox)
        
        # Configure mocks
        async def mock_generate_text(*args, **kwargs):
            # Simplified implementation that returns a sample response
            return json.dumps([
                {"task": "Initialize project structure", "type": "code_generation", "details": {"language": "python"}},
                {"task": "Create Dockerfile", "type": "dockerfile_generation", "details": {}},
                {"task": "Deploy to Cloud Run", "type": "cloud_deployment", "details": {}}
            ])
        
        async def mock_get_llm(model_name):
            llm_mock = MagicMock()
            llm_mock.invoke = MagicMock(return_value="Test response")
            return llm_mock
        
        self.mock_llm_router.generate_text = mock_generate_text
        self.mock_llm_router.get_llm = mock_get_llm
        
        # Test config with required settings
        self.test_config = {
            "gcp_config_defaults": {
                "project_id": "test-project",
                "region": "us-central1",
                "gcs_bucket_name": "test-bucket",
                "artifact_registry_repository": "test-repo"
            }
        }
        
        # Create the orchestrator
        self.agent_orchestrator = AgentOrchestrator(
            llm_router=self.mock_llm_router,
            memory_manager=self.mock_memory_manager,
            monitoring_system=self.mock_monitoring_system,
            safety_sandbox=self.mock_safety_sandbox,
            config=self.test_config
        )
        
        # Mock the update task state method
        async def mock_update_task_state(goal_id, state_update):
            logger.info(f"Task state update for {goal_id}: {state_update}")
            return True
        
        self.agent_orchestrator._update_task_state = mock_update_task_state
    
    @patch("backend.core_orchestration.agent_orchestrator.Agent")
    @patch("backend.core_orchestration.agent_orchestrator.Crew")
    @patch("backend.core_orchestration.agent_orchestrator.Task")
    async def test_orchestration_flow(self, mock_task, mock_crew, mock_agent):
        """Test the basic orchestration flow."""
        # Configure mocks
        mock_task_instance = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "Crew process completed successfully."
        
        mock_task.return_value = mock_task_instance
        mock_crew.return_value = mock_crew_instance
        
        # Mock agent creation methods
        test_goal = "Create a simple Python web server with Docker and deploy to Cloud Run"
        test_goal_id = "test-goal-123"
        
        # Execute the orchestration process
        try:
            await self.agent_orchestrator.start_orchestration(
                goal_id=test_goal_id,
                goal=test_goal
            )
            
            # Check that the crew was created and kicked off
            mock_crew.assert_called_once()
            mock_crew_instance.kickoff.assert_called_once()
        except Exception as e:
            pytest.fail(f"Orchestration process failed with error: {str(e)}")
    
    @patch("backend.agents.cloud_agent.CloudAgent.deploy_to_cloud_run")
    @patch("backend.agents.code_execution_agent.CodeExecutionAgent.generate_code")
    @patch("backend.agents.planner_agent.PlannerAgent.create_implementation_plan")
    async def test_end_to_end_flow(self, mock_plan, mock_generate, mock_deploy):
        """Test an end-to-end user goal flow (mocked implementations)."""
        # Configure mocks to return specific test data
        mock_plan.return_value = json.dumps([
            {"task": "Create Docker web app", "type": "code_generation", "order": 1},
            {"task": "Deploy to Cloud Run", "type": "cloud_deployment", "order": 2}
        ])
        
        mock_generate.return_value = json.dumps({
            "success": True,
            "code_path": "/tmp/test_app",
            "files_created": ["app.py", "Dockerfile", "requirements.txt"]
        })
        
        mock_deploy.return_value = json.dumps({
            "success": True,
            "service_name": "test-web-app",
            "service_url": "https://test-web-app-abc123.run.app"
        })
        
        # Run the test with a specific goal
        test_goal = "Create and deploy a Python FastAPI service with a /hello endpoint"
        test_goal_id = "test-specific-goal-456"
        
        # Execute with patched agent methods
        with patch("backend.core_orchestration.agent_orchestrator.Crew") as mock_crew:
            # Configure the mock crew
            mock_crew_instance = MagicMock()
            mock_crew_instance.kickoff.return_value = {
                "final_output": "Successfully created and deployed the Python FastAPI service.",
                "service_url": "https://test-web-app-abc123.run.app"
            }
            mock_crew.return_value = mock_crew_instance
            
            # Run the orchestration
            await self.agent_orchestrator.start_orchestration(
                goal_id=test_goal_id,
                goal=test_goal
            )
            
            # Verify the orchestration ran successfully
            mock_crew.assert_called_once()
            mock_crew_instance.kickoff.assert_called_once()
