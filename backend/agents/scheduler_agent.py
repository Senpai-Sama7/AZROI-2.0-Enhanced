from .agent_plugin import AgentPlugin
import time

class SchedulerAgent(AgentPlugin):
    """Agent for scheduling tasks (mock implementation)."""
    def __init__(self):
        super().__init__(
            name="SchedulerAgent",
            description="Schedules tasks for future execution."
        )
        self.scheduled_tasks = []

    def health_check(self):
        # Always healthy in mock
        return True, "SchedulerAgent healthy."

    def handle_task(self, task):
        # Simulate scheduling a task
        run_at = task.get('run_at')
        action = task.get('action')
        if run_at and action:
            self.scheduled_tasks.append((run_at, action))
            return f"Task scheduled at {run_at}: {action}"
        return "Missing run_at or action."
