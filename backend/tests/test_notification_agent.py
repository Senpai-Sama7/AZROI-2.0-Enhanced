import pytest
from backend.agents.notification_agent import NotificationAgent

def test_notification_health():
    agent = NotificationAgent()
    healthy, msg = agent.health_check()
    assert healthy
    assert "healthy" in msg.lower()

def test_notification_send():
    agent = NotificationAgent()
    result = agent.handle_task({"recipient": "user@example.com", "message": "Hello!"})
    assert "Notification sent" in result
    missing = agent.handle_task({"recipient": "user@example.com"})
    assert "Missing" in missing
