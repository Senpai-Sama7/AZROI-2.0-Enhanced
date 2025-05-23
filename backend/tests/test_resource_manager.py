from backend.agents.resource_manager import ResourceManager

def test_resource_manager_check():
    rm = ResourceManager(cpu_threshold=100, mem_threshold=100)  # Set high to avoid warnings
    cpu, mem = rm.check_resources()
    assert isinstance(cpu, float)
    assert isinstance(mem, float)
    assert 0 <= cpu <= 100
    assert 0 <= mem <= 100

def test_resource_manager_enforce_limits():
    rm = ResourceManager(cpu_threshold=100, mem_threshold=100)
    assert rm.enforce_limits() is True
