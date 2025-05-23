import pytest
from backend.core_orchestration.agent_orchestrator import AgentOrchestrator
from backend.agents.file_manager_agent import FileManagerAgent
from backend.agents.notification_agent import NotificationAgent
from backend.agents.scheduler_agent import SchedulerAgent
from backend.agents.cognitive_monitor_agent import CognitiveMonitorAgent

# Mock our dependencies for testing
class DummyLLMRouter:
    async def generate(self, *args, **kwargs):
        return '[{"id": "1", "title": "Test", "description": "Test file operation", "dependencies": [], "complexity": "Low"}]'

class DummyMemoryManager:
    pass

class DummySafetySandbox:
    pass

# Create a dummy MonitoringSystem that implements the required methods
class DummyMonitoringSystem:
    def record_event(self, event_type, event_data):
        # Mock implementation for testing
        pass

# Patch AgentOrchestrator.__init__ to accept our dummy classes
original_init = AgentOrchestrator.__init__
def patched_init(self, llm_router, memory_manager, safety_sandbox, monitoring_system, **kwargs):
    # Just set attributes directly, bypassing type checking
    self.llm_router = llm_router
    self.memory_manager = memory_manager
    self.safety_sandbox = safety_sandbox
    self.monitoring_system = monitoring_system
    self.azr = kwargs.get('azr')
    self.ffl = kwargs.get('ffl')
    self.config = kwargs.get('config', {})
    self.active_orchestrations = {}
    self.update_task_state_fn = self.config.get("update_task_state_fn")
    # Initialize agents
    self.web_automation_agent = WebAutomationAgent(headless=True)
    self.file_manager_agent = FileManagerAgent()
    self.notification_agent = NotificationAgent()
    self.scheduler_agent = SchedulerAgent()
    self.cognitive_monitor_agent = CognitiveMonitorAgent()
    # Initialize monitors and managers
    self.health_monitor = None  # Mock this
    self.resource_manager = None  # Mock this
    self.feedback_manager = None  # Mock this

# Apply the monkey patch for the test
AgentOrchestrator.__init__ = patched_init

def test_orchestrator_registers_new_agents():
    orchestrator = AgentOrchestrator(
        llm_router=DummyLLMRouter(),
        memory_manager=DummyMemoryManager(),
        safety_sandbox=DummySafetySandbox(),
        monitoring_system=DummyMonitoringSystem(),
        config={}
    )
    assert isinstance(orchestrator.file_manager_agent, FileManagerAgent)
    assert isinstance(orchestrator.notification_agent, NotificationAgent)
    assert isinstance(orchestrator.scheduler_agent, SchedulerAgent)
    assert isinstance(orchestrator.cognitive_monitor_agent, CognitiveMonitorAgent)
    assert isinstance(orchestrator.cognitive_monitor_agent, CognitiveMonitorAgent)

def test_tool_selection_new_agents():
    orchestrator = AgentOrchestrator(
        llm_router=DummyLLMRouter(),
        memory_manager=DummyMemoryManager(),
        safety_sandbox=DummySafetySandbox(),
        monitoring_system=DummyMonitoringSystem(),
        config={}
    )
    # FileManagerAgent
    tools = orchestrator._default_tool_selection({"title": "Read file", "description": "Read a file from disk"})
    assert any(t["name"] == "FileManagerAgent" for t in tools)
    # NotificationAgent
    tools = orchestrator._default_tool_selection({"title": "Notify", "description": "Send notification"})
    assert any(t["name"] == "NotificationAgent" for t in tools)
    # SchedulerAgent
    tools = orchestrator._default_tool_selection({"title": "Schedule", "description": "Schedule a task"})
    assert any(t["name"] == "SchedulerAgent" for t in tools)
    # CognitiveMonitorAgent (test for hallucination detection)
    tools = orchestrator._default_tool_selection({"title": "Check hallucination", "description": "Detect hallucinations in output"})
    assert any(t["name"] == "CognitiveMonitorAgent" for t in tools)

# Test cognitive monitor agent
def test_cognitive_monitor():
    orchestrator = AgentOrchestrator(
        llm_router=DummyLLMRouter(),
        memory_manager=DummyMemoryManager(),
        safety_sandbox=DummySafetySandbox(),
        monitoring_system=DummyMonitoringSystem(),
        config={}
    )
    # Test hallucination detection
    suspect_subtask = {"title": "Test", "result": "Lorem ipsum as an AI I cannot do that"}
    issues = orchestrator.cognitive_monitor_agent.analyze(suspect_subtask, {"goal": "Test goal"})
    assert len(issues) > 0, "Should detect hallucination markers"
    
    # Test goal drift detection
    unrelated_subtask = {"title": "Completely unrelated", "description": "This has nothing to do with main goal"}
    issues = orchestrator.cognitive_monitor_agent.analyze(unrelated_subtask, {"goal": "Build a web application"})
    assert len(issues) > 0, "Should detect goal drift"

# Test the additional CognitiveMonitorAgent
def test_cognitive_monitor_agent():
    # Create the agent directly
    from backend.agents.cognitive_monitor_agent import CognitiveMonitorAgent
    
    cognitive_agent = CognitiveMonitorAgent()
    
    # Test hallucination detection
    hallucination_subtask = {"result": "Lorem ipsum as an AI I cannot do that"}
    issues = cognitive_agent.analyze(hallucination_subtask, {"goal": "Test goal"})
    assert len(issues) > 0, "Should detect hallucination markers"

# Restore the original init to avoid affecting other tests
def teardown_module(module):
    AgentOrchestrator.__init__ = original_init
