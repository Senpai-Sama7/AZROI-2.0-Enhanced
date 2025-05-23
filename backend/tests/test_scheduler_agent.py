import pytest
from backend.agents.scheduler_agent import SchedulerAgent

def test_scheduler_health():
    agent = SchedulerAgent()
    healthy, msg = agent.health_check()
    assert healthy
    assert "healthy" in msg.lower()

def test_scheduler_schedule():
    agent = SchedulerAgent()
    result = agent.handle_task({"run_at": "2025-05-23T10:00:00Z", "action": "backup"})
    assert "Task scheduled" in result
    missing = agent.handle_task({"action": "backup"})
    assert "Missing" in missing
