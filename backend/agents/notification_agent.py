from .agent_plugin import AgentPlugin

class NotificationAgent(AgentPlugin):
    """Agent for sending notifications (mock implementation)."""
    def __init__(self):
        super().__init__(
            name="NotificationAgent",
            description="Sends notifications to users or external systems."
        )

    def health_check(self):
        # Always healthy in mock
        return True, "NotificationAgent healthy."

    def handle_task(self, task):
        # Simulate sending a notification
        recipient = task.get('recipient')
        message = task.get('message')
        if recipient and message:
            return f"Notification sent to {recipient}: {message}"
        return "Missing recipient or message."
