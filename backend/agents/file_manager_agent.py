from .agent_plugin import AgentPlugin
import os

class FileManagerAgent(AgentPlugin):
    """Agent for file system operations (read, write, list, delete)."""
    def __init__(self):
        super().__init__(
            name="FileManagerAgent",
            description="Performs file system operations such as reading, writing, listing, and deleting files."
        )

    def health_check(self):
        # Simple check: can we list the current directory?
        try:
            os.listdir('.')
            return True, "FileManagerAgent healthy."
        except Exception as e:
            return False, f"FileManagerAgent error: {e}"

    def handle_task(self, task):
        action = task.get('action')
        path = task.get('path')
        if action == 'list':
            return os.listdir(path)
        elif action == 'read':
            with open(path, 'r') as f:
                return f.read()
        elif action == 'write':
            with open(path, 'w') as f:
                f.write(task.get('content', ''))
            return f"Wrote to {path}"
        elif action == 'delete':
            os.remove(path)
            return f"Deleted {path}"
        else:
            return f"Unknown action: {action}"
