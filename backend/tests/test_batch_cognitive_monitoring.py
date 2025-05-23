import pytest
import asyncio
from unittest.mock import MagicMock, patch

# This needs to be patched before importing AgentOrchestrator
with patch('backend.agents.web_automation_agent.WebAutomationAgent', MagicMock()) as mock_web_agent:
    from backend.core_orchestration.agent_orchestrator import AgentOrchestrator

class TestBatchCognitiveMonitoring:
    """Tests for the batch cognitive monitoring functionality in AgentOrchestrator"""
    
    @pytest.fixture
    def orchestrator_with_mocks(self):
        """Create an orchestrator with mocked dependencies"""
        llm_router = MagicMock()
        memory_manager = MagicMock()
        safety_sandbox = MagicMock()
        monitoring_system = MagicMock()
        
        # Create the orchestrator with mocked dependencies
        orchestrator = AgentOrchestrator(
            llm_router=llm_router,
            memory_manager=memory_manager,
            safety_sandbox=safety_sandbox,
            monitoring_system=monitoring_system,
            config={}
        )
        
        # Mock the cognitive_monitor_agent
        orchestrator.cognitive_monitor_agent = MagicMock()
        orchestrator.cognitive_monitor_agent.analyze_batch.return_value = {
            "1": ["Issue 1", "Issue 2"],
            "3": ["Issue 3"]
        }
        
        # Mock the add_agent_feedback method
        orchestrator.add_agent_feedback = MagicMock()
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_batch_cognitive_monitoring_success(self, orchestrator_with_mocks):
        """Test successful batch cognitive monitoring"""
        orchestrator = orchestrator_with_mocks
        
        # Set up the active orchestrations
        orchestrator.active_orchestrations = {
            "goal123": {
                "goal": "Test goal",
                "plan": {
                    "subtasks": [
                        {"id": "1", "title": "Task 1"},
                        {"id": "2", "title": "Task 2"},
                        {"id": "3", "title": "Task 3"}
                    ]
                }
            }
        }
        
        # Call the batch monitoring function
        results = await orchestrator.batch_cognitive_monitoring("goal123")
        
        # Check that the cognitive monitor agent's analyze_batch method was called correctly
        orchestrator.cognitive_monitor_agent.analyze_batch.assert_called_once()
        
        # Check the results
        assert "1" in results
        assert "3" in results
        assert len(results["1"]) == 2
        assert len(results["3"]) == 1
        
        # Check that add_agent_feedback was called for each issue
        assert orchestrator.add_agent_feedback.call_count == 2
    
    @pytest.mark.asyncio
    async def test_batch_cognitive_monitoring_no_goal(self, orchestrator_with_mocks):
        """Test batch monitoring with non-existent goal"""
        orchestrator = orchestrator_with_mocks
        
        # Empty active orchestrations
        orchestrator.active_orchestrations = {}
        
        # Call the batch monitoring function with a non-existent goal
        results = await orchestrator.batch_cognitive_monitoring("nonexistent")
        
        # Check that the result is an empty dict
        assert results == {}
        
        # Check that analyze_batch was not called
        orchestrator.cognitive_monitor_agent.analyze_batch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_batch_cognitive_monitoring_exception(self, orchestrator_with_mocks):
        """Test batch monitoring with an exception"""
        orchestrator = orchestrator_with_mocks
        
        # Set up the active orchestrations
        orchestrator.active_orchestrations = {
            "goal123": {
                "goal": "Test goal",
                "plan": {
                    "subtasks": [
                        {"id": "1", "title": "Task 1"},
                        {"id": "2", "title": "Task 2"},
                        {"id": "3", "title": "Task 3"}
                    ]
                }
            }
        }
        
        # Make analyze_batch raise an exception
        orchestrator.cognitive_monitor_agent.analyze_batch.side_effect = Exception("Test exception")
        
        # Call the batch monitoring function
        results = await orchestrator.batch_cognitive_monitoring("goal123")
        
        # Check that the result is an empty dict
        assert results == {}
        
        # Check that analyze_batch was called
        orchestrator.cognitive_monitor_agent.analyze_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_cognitive_monitoring_performance(self, orchestrator_with_mocks):
        """Test the performance benefit of batch monitoring"""
        import time
        orchestrator = orchestrator_with_mocks
        
        # Create a large plan with many subtasks
        subtasks = []
        for i in range(100):
            subtasks.append({"id": str(i), "title": f"Task {i}"})
        
        orchestrator.active_orchestrations = {
            "goal123": {
                "goal": "Test goal",
                "plan": {
                    "subtasks": subtasks
                }
            }
        }
        
        # Mock analyze to simulate individual task analysis
        orchestrator.cognitive_monitor_agent.analyze = MagicMock(return_value=[])
        
        # Reset analyze_batch to return empty dict
        orchestrator.cognitive_monitor_agent.analyze_batch = MagicMock(return_value={})
        
        # Measure time for batch analysis
        start_time = time.time()
        await orchestrator.batch_cognitive_monitoring("goal123")
        batch_time = time.time() - start_time
        
        # Measure time for individual analysis (simulated)
        start_time = time.time()
        for subtask in subtasks:
            orchestrator.cognitive_monitor_agent.analyze(subtask, orchestrator.active_orchestrations["goal123"])
        individual_time = time.time() - start_time
        
        # Just log the performance difference - we can't assert exact timing
        print(f"Batch time: {batch_time:.4f}s, Individual time: {individual_time:.4f}s")
        print(f"Performance improvement: {individual_time/batch_time:.2f}x")
        
        # Just verify that analyze_batch was called once
        orchestrator.cognitive_monitor_agent.analyze_batch.assert_called_once()
