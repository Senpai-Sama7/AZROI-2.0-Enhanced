import pytest
import unittest.mock as mock
import time
from backend.core_orchestration.agent_orchestrator import AgentOrchestrator
from backend.agents.file_manager_agent import FileManagerAgent
from backend.agents.notification_agent import NotificationAgent
from backend.agents.scheduler_agent import SchedulerAgent
from backend.agents.cognitive_monitor_agent import CognitiveMonitorAgent
from backend.agents.web_automation_agent import WebAutomationAgent

# Test for the cognitive monitor agent - this doesn't need the orchestrator
def test_cognitive_monitor_agent():
    # Create the agent directly
    cognitive_agent = CognitiveMonitorAgent()
    
    # Test hallucination detection
    hallucination_subtask = {"result": "Lorem ipsum as an AI I cannot do that"}
    issues = cognitive_agent.analyze(hallucination_subtask, {"goal": "Test goal"})
    assert len(issues) > 0, "Should detect hallucination markers"
    
    # Test goal drift detection
    drift_subtask = {"title": "Completely unrelated"}
    issues = cognitive_agent.analyze(drift_subtask, {"goal": "Build a web application"})
    assert len(issues) > 0, "Should detect goal drift"
    
    # Test no issues
    good_subtask = {"title": "Build app components", "result": "Components successfully built"}
    issues = cognitive_agent.analyze(good_subtask, {"goal": "Build a web application"})
    assert len(issues) == 0, "Should not detect issues in valid subtask"

# Test the advanced features of the optimized cognitive monitor agent
def test_cognitive_monitor_agent_advanced():
    cognitive_agent = CognitiveMonitorAgent()
    
    # Test early exit functionality
    complex_subtask = {
        "result": "Lorem ipsum dolor sit amet",
        "error": "Logical contradiction detected",
        "title": "Unrelated task"
    }
    
    # Should find all issues (3 types)
    all_issues = cognitive_agent.analyze(complex_subtask, {"goal": "Build a web application"})
    assert len(all_issues) >= 2, "Should detect multiple issues"
    
    # Should exit after finding first issue
    early_exit_issues = cognitive_agent.analyze(complex_subtask, {"goal": "Build a web application"}, early_exit=True)
    assert len(early_exit_issues) == 1, "Should only return the first issue with early exit"
    
    # Test batch processing
    subtasks = [
        {"id": "1", "title": "Build components", "result": "Components successfully built"},
        {"id": "2", "title": "Unrelated task", "result": "Lorem ipsum"},
        {"id": "3", "title": "Configure server", "error": "Logic error encountered"}
    ]
    
    batch_results = cognitive_agent.analyze_batch(subtasks, {"goal": "Build a web application with server"})
    assert "2" in batch_results, "Should detect issues in the second subtask"
    assert "3" in batch_results, "Should detect issues in the third subtask"
    assert "1" not in batch_results, "Should not detect issues in the first subtask"

# Test performance optimization of the cognitive monitor agent
def test_cognitive_monitor_agent_performance():
    cognitive_agent = CognitiveMonitorAgent()
    
    # Create a large test case
    large_result = "This is a large result " * 1000
    large_subtask = {"result": large_result, "title": "Performance test"}
    
    # Measure performance
    start_time = time.time()
    cognitive_agent.analyze(large_subtask, {"goal": "Test performance"})
    end_time = time.time()
    
    # Check if analysis completes in reasonable time (should be fast)
    execution_time = end_time - start_time
    assert execution_time < 0.1, f"Analysis should be fast (took {execution_time:.4f} seconds)"
    
    # Test caching effectiveness by running multiple times with same goal
    start_time = time.time()
    for _ in range(10):
        cognitive_agent.analyze({"title": f"Task {_}"}, {"goal": "Same goal used repeatedly"})
    cached_time = time.time() - start_time
    
    # Reset cache
    cognitive_agent.goal_keywords_cache = {}
    
    # Run again with different goals
    start_time = time.time()
    for i in range(10):
        cognitive_agent.analyze({"title": f"Task {i}"}, {"goal": f"Different goal {i}"})
    uncached_time = time.time() - start_time
    
    # Cached execution should be faster, but we can't assert exact times
    # Just log the results for information
    print(f"Cached execution time: {cached_time:.4f}s, Uncached: {uncached_time:.4f}s")
    
# Tests for other agents
def test_file_manager_agent_selection():
    file_agent = FileManagerAgent()
    healthy, _ = file_agent.health_check()
    assert healthy, "File manager agent should be healthy"
    
    task = {"action": "list", "path": "."}
    # Just test that it doesn't throw an exception
    try:
        file_agent.handle_task(task)
        assert True  # If we get here, it didn't crash
    except Exception as e:
        assert False, f"File manager agent should not throw exception: {e}"

def test_notification_agent_selection():
    notify_agent = NotificationAgent()
    healthy, _ = notify_agent.health_check()
    assert healthy, "Notification agent should be healthy"
    
    result = notify_agent.handle_task({"recipient": "test@example.com", "message": "Test"})
    assert "Notification sent" in result

def test_scheduler_agent_selection():
    scheduler_agent = SchedulerAgent()
    healthy, _ = scheduler_agent.health_check()
    assert healthy, "Scheduler agent should be healthy"
    
    result = scheduler_agent.handle_task({"run_at": "2025-06-01T12:00:00Z", "action": "backup"})
    assert "Task scheduled" in result
