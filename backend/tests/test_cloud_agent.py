#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import pytest
import unittest
from unittest.mock import MagicMock, patch

from backend.agents.cloud_agent import CloudAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCloudAgent(unittest.TestCase):
    """Test cases for the Cloud Agent implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_llm_router = MagicMock()
        self.mock_memory_manager = MagicMock()
        self.mock_monitoring_system = MagicMock()
        
        # Configure mocks
        async def mock_get_llm(model_name):
            return MagicMock()
        
        async def mock_store_memory(content, namespace, metadata):
            return "test-memory-id"
        
        self.mock_llm_router.get_llm = mock_get_llm
        self.mock_memory_manager.store_memory = mock_store_memory
        
        # Create test config
        self.test_config = {
            "gcp_config_defaults": {
                "project_id": "test-project",
                "region": "us-central1",
                "gcs_bucket_name": "test-bucket",
                "artifact_registry_repository": "test-repo",
                "cloud_run_service_prefix": "test-svc"
            }
        }
        
        # Initialize the agent
        self.cloud_agent = CloudAgent(
            llm_router=self.mock_llm_router,
            memory_manager=self.mock_memory_manager,
            monitoring_system=self.mock_monitoring_system,
            config=self.test_config
        )
    
    async def async_setup(self):
        """Async setup for tests that need it."""
        # Initialize the agent (normally this happens when needed)
        await self.cloud_agent.initialize()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        # Run the async setup
        await self.async_setup()
        
        # Check that the agent was created
        self.assertIsNotNone(self.cloud_agent.agent)
        self.assertEqual(self.cloud_agent.agent.role, "Cloud Deployment Specialist")
    
    @patch("backend.agents.cloud_agent.storage")
    @pytest.mark.asyncio
    async def test_upload_to_cloud_storage(self, mock_storage):
        """Test the upload_to_cloud_storage tool."""
        # Mock the storage client
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        mock_storage_client = MagicMock()
        mock_storage_client.get_bucket.return_value = mock_bucket
        mock_storage.Client.return_value = mock_storage_client
        
        # Create a test directory and file
        test_dir = "/tmp/test_cloud_agent"
        os.makedirs(test_dir, exist_ok=True)
        with open(f"{test_dir}/test_file.txt", "w") as f:
            f.write("Test content")
        
        # Call the upload method
        result = self.cloud_agent.upload_to_cloud_storage(
            local_path=test_dir,
            goal_id="test-goal-123",
            destination_folder="test-folder"
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check the result
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["bucket"], "test-bucket")
        self.assertEqual(result_data["destination_folder"], "test-folder")
        
        # Clean up
        import shutil
        shutil.rmtree(test_dir)
    
    @patch("backend.agents.cloud_agent.build_v1")
    @patch("backend.agents.cloud_agent.cloudbuild_v1")
    @pytest.mark.asyncio
    async def test_build_docker_image(self, mock_cloudbuild, mock_build):
        """Test the build_docker_image tool."""
        # Mock the build client
        mock_build_client = MagicMock()
        mock_operation = MagicMock()
        mock_metadata = MagicMock()
        mock_build_instance = MagicMock()
        mock_build_instance.id = "test-build-123"
        mock_metadata.build = mock_build_instance
        mock_operation.metadata = mock_metadata
        
        mock_build_client.create_build.return_value = mock_operation
        mock_build.CloudBuildClient.return_value = mock_build_client
        
        # Call the build method
        result = self.cloud_agent.build_docker_image(
            source_uri="gs://test-bucket/test-folder",
            goal_id="test-goal-123",
            dockerfile_path="Dockerfile"
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check the result
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["build_id"], "test-build-123")
        self.assertIn("test-goal-123", result_data["image_name"])
    
    @patch("backend.agents.cloud_agent.run_v2")
    @pytest.mark.asyncio
    async def test_deploy_to_cloud_run(self, mock_run):
        """Test the deploy_to_cloud_run tool."""
        # Mock the run client
        mock_service_client = MagicMock()
        mock_operation = MagicMock()
        mock_response = MagicMock()
        mock_response.uri = "https://test-svc-123.run.app"
        mock_response.name = "projects/test-project/locations/us-central1/services/test-svc-123"
        mock_template = MagicMock()
        mock_template.revision = "test-revision-123"
        mock_response.template = mock_template
        
        mock_operation.result.return_value = mock_response
        mock_service_client.create_service.return_value = mock_operation
        mock_run.ServicesClient.return_value = mock_service_client
        
        # Call the deploy method
        result = self.cloud_agent.deploy_to_cloud_run(
            image_uri="us-central1-docker.pkg.dev/test-project/test-repo/app-test-goal-123",
            goal_id="test-goal-123"
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        # Check the result
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["service_url"], "https://test-svc-123.run.app")
        self.assertIn("test-goal-123", result_data["service_name"])

if __name__ == "__main__":
    unittest.main()
