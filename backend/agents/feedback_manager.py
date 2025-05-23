import logging

class FeedbackManager:
    """
    Collects and manages user and agent feedback for continuous improvement.
    """
    def __init__(self):
        self.logger = logging.getLogger("FeedbackManager")
        self.user_feedback = []
        self.agent_feedback = []

    def add_user_feedback(self, feedback: str):
        self.logger.info(f"User feedback received: {feedback}")
        self.user_feedback.append(feedback)

    def add_agent_feedback(self, feedback: str):
        self.logger.info(f"Agent feedback received: {feedback}")
        self.agent_feedback.append(feedback)

    def get_all_feedback(self):
        return {
            "user_feedback": self.user_feedback,
            "agent_feedback": self.agent_feedback
        }
