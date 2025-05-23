class AgentPlugin:
    """
    Base class for agent plugins. Extend this to add new agent/tool capabilities.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def execute(self, *args, **kwargs):
        raise NotImplementedError("Plugins must implement the execute method.")
