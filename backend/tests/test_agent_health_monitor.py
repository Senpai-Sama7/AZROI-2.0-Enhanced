import time
from backend.agents.web_automation_agent import WebAutomationAgent
from backend.agents.agent_health_monitor import AgentHealthMonitor

def test_agent_health_monitor():
    agent = WebAutomationAgent(headless=True)
    monitor = AgentHealthMonitor({"web_automation": agent}, interval=1)
    try:
        time.sleep(2)
        status = monitor.get_status()
        assert status["web_automation"] is True
    finally:
        agent.close()
        monitor.stop()
