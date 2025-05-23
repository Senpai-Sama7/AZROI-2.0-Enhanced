import pytest
from backend.agents.web_automation_agent import WebAutomationAgent

def test_open_url():
    agent = WebAutomationAgent(headless=True)
    try:
        agent.open_url("https://www.example.com")
        assert "Example Domain" in agent.driver.title
    finally:
        agent.close()

def test_health_check():
    agent = WebAutomationAgent(headless=True)
    try:
        assert agent.health_check() is True
    finally:
        agent.close()
