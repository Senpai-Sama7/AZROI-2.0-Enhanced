#!/usr/bin/env python3
"""
Test script for production configuration manager
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from config.production_config import (
    ConfigurationManager, 
    ProductionConfig, 
    Environment, 
    CloudProvider,
    initialize_config,
    get_config,
    config_manager
)

async def test_config_manager():
    """Test the configuration manager"""
    print("Testing Configuration Manager...")

    # Initialize configuration manager
    config_path = "config/test_config.yaml"
    await initialize_config(config_path)

    # Get the global configuration
    config = await get_config()
    print("Loaded Configuration:", config)

    # Test feature flags
    feature_name = "test_feature"
    await config_manager.set_feature_flag(feature_name, True)
    assert await config_manager.get_feature_flag(feature_name) == True
    print(f"Feature flag '{feature_name}' set and retrieved successfully.")

    # Test health check
    health_status = await config_manager.health_check()
    assert health_status == True
    print("Health check passed.")

async def test_global_config():
    """Test global configuration functions"""
    print("Testing Global Configuration Functions...")

    # Initialize configuration
    await initialize_config()

    # Get configuration
    config = await get_config()
    assert isinstance(config, ProductionConfig)
    print("Global configuration loaded successfully.")

async def main():
    """Run all tests"""
    await test_config_manager()
    await test_global_config()

if __name__ == "__main__":
    asyncio.run(main())
