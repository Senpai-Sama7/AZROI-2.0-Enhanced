#!/usr/bin/env python3

"""
Quick test script for the CloudAgent.
This script will test the basic functionality of the cloud agent without running a full system test.
"""

import asyncio
import json
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cloud_agent_test")

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the required components
from core_orchestration.config_loader import ConfigLoader
from core_orchestration.llm_router import LLMRouter
from core_orchestration.monitoring_system import MonitoringSystem
from tools.memory_manager import MemoryManager
from tools.vector_storage import VectorStorage
from agents.cloud_agent import CloudAgent

async def run_cloud_agent_test():
    """Run a simple test of the cloud agent."""
    logger.info("Starting Cloud Agent test")
    
    # Initialize configuration
    config_loader = ConfigLoader()
    config = config_loader.load_config()
    
    # Initialize components
    monitoring_system = MonitoringSystem()
    
    # Initialize vector storage and memory manager
    vector_storage = VectorStorage(
        collection_name="cloud_agent_test",
        path="./test_vectorstore_data",
    )
    
    memory_manager = MemoryManager(
        vector_storage=vector_storage,
        collection_name="cloud_agent_test",
    )
    
    # Initialize LLM router
    llm_router = LLMRouter(
        redis_url=None,  # No caching for test
        default_model="gemini-2.5-flash-preview-04-17",
    )
    
    # Initialize the cloud agent
    cloud_agent = CloudAgent(
        llm_router=llm_router,
        memory_manager=memory_manager,
        monitoring_system=monitoring_system,
        config=config
    )
    
    # Test list_cloud_resources (this should be safe to run)
    try:
        logger.info("Testing list_cloud_resources")
        result = cloud_agent.list_cloud_resources("cloud_storage")
        result_data = json.loads(result)
        
        if result_data.get("success", False):
            logger.info(f"Successfully listed {len(result_data.get('resources', []))} cloud storage resources")
            for resource in result_data.get("resources", []):
                logger.info(f"Resource: {resource.get('name')}")
        else:
            logger.error(f"Failed to list cloud resources: {result_data.get('error')}")
            
    except Exception as e:
        logger.error(f"Error testing cloud agent: {str(e)}")
    
    logger.info("Cloud Agent test completed")

if __name__ == "__main__":
    asyncio.run(run_cloud_agent_test())
