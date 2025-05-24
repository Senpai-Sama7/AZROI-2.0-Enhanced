"""
Test configuration for AZROI testing suite
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, AsyncMock, patch

# Test fixtures and configurations
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    from backend.config.settings import AppConfig, LLMConfig, CrewAIConfig
    
    config = AppConfig()
    config.llm = LLMConfig(
        default_model="test-model",
        openai_api_key="test-key",
        max_tokens=1000,
        temperature=0.7
    )
    config.crewai = CrewAIConfig(
        max_concurrent_crews=2,
        max_agents_per_crew=5,
        task_timeout=60
    )
    
    return config


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    logger.context = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))
    logger.bind = Mock(return_value=logger)
    return logger


# Test data factories
class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_test_user(user_id="test_user", username="testuser", role="user"):
        """Create a test user"""
        from backend.security.auth import User, UserRole, Permission
        
        return User(
            id=user_id,
            username=username,
            email=f"{username}@test.com",
            role=UserRole(role),
            permissions=[Permission.READ, Permission.WRITE]
        )
    
    @staticmethod
    def create_test_task(task_id="test_task", task_type="code_generation"):
        """Create a test task"""
        return {
            "task_id": task_id,
            "type": task_type,
            "description": f"Test {task_type} task",
            "inputs": {"test_input": "test_value"},
            "status": "pending",
            "priority": "medium"
        }
    
    @staticmethod
    def create_test_agent(agent_id="test_agent", agent_type="ARCHITECT"):
        """Create a test agent"""
        from backend.core_orchestration.agent_orchestrator_enhanced import AgentType
        
        return {
            "agent_id": agent_id,
            "agent_type": AgentType(agent_type),
            "status": "idle",
            "capabilities": ["analysis", "planning"],
            "tools": ["architecture_tool"]
        }
    
    @staticmethod
    def create_test_crew(crew_id="test_crew", crew_name="Test Crew"):
        """Create a test crew"""
        return {
            "crew_id": crew_id,
            "crew_name": crew_name,
            "status": "idle",
            "agents": [],
            "tasks": []
        }


# Test utilities
class TestUtils:
    """Utility functions for tests"""
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """Wait for a condition to become true"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    def assert_dict_contains(actual_dict, expected_subset):
        """Assert that a dictionary contains expected key-value pairs"""
        for key, expected_value in expected_subset.items():
            assert key in actual_dict, f"Key '{key}' not found in {actual_dict}"
            assert actual_dict[key] == expected_value, f"Expected {key}={expected_value}, got {actual_dict[key]}"
    
    @staticmethod
    def create_mock_response(status_code=200, json_data=None, text=""):
        """Create a mock HTTP response"""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        mock_response.text = text
        mock_response.raise_for_status = Mock()
        
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        
        return mock_response


# Performance test helpers
class PerformanceTestHelper:
    """Helper for performance testing"""
    
    @staticmethod
    async def measure_execution_time(func, *args, **kwargs):
        """Measure execution time of a function"""
        import time
        start_time = time.time()
        
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        execution_time = time.time() - start_time
        return result, execution_time
    
    @staticmethod
    async def run_concurrent_tasks(tasks, max_concurrent=10):
        """Run tasks concurrently with limit"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await task
        
        return await asyncio.gather(*[run_with_semaphore(task) for task in tasks])


# Mock external services
class MockServices:
    """Mock external services for testing"""
    
    @staticmethod
    def mock_openai_client():
        """Mock OpenAI client"""
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = "Test response"
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        return mock_client
    
    @staticmethod
    def mock_redis_client():
        """Mock Redis client"""
        mock_redis = Mock()
        mock_redis.ping = Mock(return_value=True)
        mock_redis.set = Mock(return_value=True)
        mock_redis.get = Mock(return_value="test_value")
        mock_redis.delete = Mock(return_value=1)
        mock_redis.hset = Mock(return_value=1)
        mock_redis.hgetall = Mock(return_value={"test": "value"})
        mock_redis.expire = Mock(return_value=True)
        return mock_redis
    
    @staticmethod
    def mock_crewai_crew():
        """Mock CrewAI crew"""
        mock_crew = Mock()
        mock_crew.kickoff = AsyncMock(return_value="Test crew result")
        mock_crew.agents = []
        mock_crew.tasks = []
        return mock_crew


# Test markers for pytest
pytest_plugins = ["pytest_asyncio"]

# Custom pytest markers
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external: mark test as requiring external services")
