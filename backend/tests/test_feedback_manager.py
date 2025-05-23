from backend.agents.feedback_manager import FeedbackManager

def test_feedback_manager():
    fm = FeedbackManager()
    fm.add_user_feedback("Great job!")
    fm.add_agent_feedback("Agent completed task.")
    feedback = fm.get_all_feedback()
    assert "Great job!" in feedback["user_feedback"]
    assert "Agent completed task." in feedback["agent_feedback"]
