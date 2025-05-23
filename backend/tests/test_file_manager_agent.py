import pytest
from backend.agents.file_manager_agent import FileManagerAgent

def test_file_manager_health():
    agent = FileManagerAgent()
    healthy, msg = agent.health_check()
    assert healthy
    assert "healthy" in msg.lower()

def test_file_manager_list(tmp_path):
    agent = FileManagerAgent()
    # Create files
    (tmp_path / "a.txt").write_text("A")
    (tmp_path / "b.txt").write_text("B")
    files = agent.handle_task({"action": "list", "path": str(tmp_path)})
    assert set(files) == {"a.txt", "b.txt"}

def test_file_manager_read_write(tmp_path):
    agent = FileManagerAgent()
    file_path = tmp_path / "test.txt"
    agent.handle_task({"action": "write", "path": str(file_path), "content": "hello"})
    content = agent.handle_task({"action": "read", "path": str(file_path)})
    assert content == "hello"

def test_file_manager_delete(tmp_path):
    agent = FileManagerAgent()
    file_path = tmp_path / "test.txt"
    file_path.write_text("bye")
    agent.handle_task({"action": "delete", "path": str(file_path)})
    assert not file_path.exists()
