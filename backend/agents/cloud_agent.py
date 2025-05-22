#!/usr/bin/env python3

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid

from crewai import Agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger("ai-architect-backend.cloud_agent")

class CloudAgent:
    """
    Cloud Agent: Responsible for deploying applications to cloud environments,
    managing cloud storage, building Docker images, and setting up cloud resources.
    This agent primarily works with Google Cloud Platform services like Cloud Storage,
    Artifact Registry, Cloud Build, and Cloud Run.
    """
    
    def __init__(self, 
                llm_router=None,
                memory_manager=None,
                monitoring_system=None,
                config=None):
        """
        Initialize the cloud agent.
        
        Args:
            llm_router: LLM router for model access
            memory_manager: Memory manager for storing results
            monitoring_system: Monitoring system for metrics
            config: Configuration dictionary
        """
        self.llm_router = llm_router
        self.memory_manager = memory_manager
        self.monitoring_system = monitoring_system
        self.config = config or {}
        self.agent = None
        
        # Load cloud agent prompt template from config
        self.prompt_template = self.config.get(
            "cloud_agent_prompt_template", 
            "You are a Cloud Deployment Specialist with expertise in GCP services. Your task is to deploy applications to cloud environments securely and efficiently."
        )
        
        logger.info("Cloud agent initialized")
    
    async def initialize(self):
        """Initialize the cloud agent with CrewAI."""
        if self.agent:
            return self.agent
            
        try:
            # Create tools for the agent
            tools = [
                self.deploy_to_cloud_run,
                self.upload_to_cloud_storage,
                self.build_docker_image,
                self.manage_artifact_registry,
                self.list_cloud_resources
            ]
            
            # Use Gemini Pro by default for cloud operations
            llm = await self.llm_router.get_llm("gemini-2.5-pro-preview-04-11")
            
            # Create the agent
            self.agent = Agent(
                role="Cloud Deployment Specialist",
                goal="Deploy applications to cloud environments efficiently and securely",
                backstory=(
                    "You are a Cloud Deployment Specialist with expertise in containerization, "
                    "cloud services, and infrastructure automation. You know how to package applications, "
                    "deploy them to cloud providers like GCP, and ensure they are scalable and secure. "
                    "You understand networking, security best practices, and infrastructure as code."
                ),
                verbose=True,
                llm=llm,
                tools=tools,
                allow_delegation=True
            )
            
            logger.info("Cloud agent fully initialized with CrewAI")
            
            if self.monitoring_system:
                self.monitoring_system.agent_initialization_counter.labels(
                    agent_type="cloud").inc()
            
            return self.agent
            
        except Exception as e:
            logger.error(f"Error initializing cloud agent: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="cloud", 
                    operation="initialize"
                ).inc()
            raise
    
    @tool("Deploy application to Cloud Run")
    def deploy_to_cloud_run(self, image_uri: str, service_name: Optional[str] = None, goal_id: str = None) -> str:
        """
        Deploy a container image to Google Cloud Run.
        
        Args:
            image_uri: The URI of the container image to deploy
            service_name: Optional name for the Cloud Run service (will be generated if not provided)
            goal_id: The ID of the current goal for tracking purposes
            
        Returns:
            JSON string with deployment results
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            from google.cloud import run_v2
            
            # Initialize client
            client = run_v2.ServicesClient()
            
            # Get project ID and region
            project_id = self.config.get("gcp_config_defaults", {}).get("project_id")
            location = self.config.get("gcp_config_defaults", {}).get("region", "us-central1")
            
            # Generate service name if not provided
            if not service_name:
                prefix = self.config.get("gcp_config_defaults", {}).get("cloud_run_service_prefix", "ai-arch-svc")
                service_name = f"{prefix}-{goal_id.split('-')[0]}"
            
            # Create service
            service = run_v2.Service()
            service.template = run_v2.RevisionTemplate()
            service.template.containers = [run_v2.Container(image=image_uri)]
            
            # Set environment variables
            service.template.containers[0].env = [
                run_v2.EnvVar(name="GOAL_ID", value=goal_id)
            ]
            
            # Set resource limits
            service.template.containers[0].resources = run_v2.ResourceRequirements(
                limits={"cpu": "1", "memory": "512Mi"}
            )
            
            # Set scaling
            service.template.max_instance_request_concurrency = 80
            service.template.max_instance_count = 10
            
            # Allow unauthenticated access if configured
            allow_unauthenticated = self.config.get("gcp_config_defaults", {}).get("cloud_run_allow_unauthenticated", True)
            
            # Deploy service
            parent = f"projects/{project_id}/locations/{location}"
            operation = client.create_service(
                parent=parent,
                service_id=service_name,
                service=service
            )
            
            # Wait for deployment to complete
            response = operation.result()
            
            # Set IAM policy for unauthenticated access if needed
            if allow_unauthenticated:
                from google.cloud import run_v2
                from google.iam.v1 import policy_pb2, binding_pb2
                
                iam_client = run_v2.ServicesClient()
                policy = policy_pb2.Policy()
                binding = binding_pb2.Binding()
                binding.role = "roles/run.invoker"
                binding.members.append("allUsers")
                policy.bindings.append(binding)
                
                iam_policy = iam_client.set_iam_policy(
                    request={
                        "resource": response.name,
                        "policy": policy
                    }
                )
            
            # Store deployment record in memory
            if self.memory_manager:
                asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=json.dumps({
                            "service_name": service_name,
                            "image_uri": image_uri,
                            "region": location,
                            "service_url": response.uri
                        }),
                        namespace="deployment_history",
                        metadata={
                            "type": "cloud_run_deployment",
                            "goal_id": goal_id,
                            "service_name": service_name
                        }
                    )
                )
            
            # Track timing and success metrics
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="cloud",
                    operation="deploy_to_cloud_run"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="cloud",
                    operation="deploy_to_cloud_run"
                ).inc()
            
            return json.dumps({
                "success": True,
                "service_name": service_name,
                "service_url": response.uri,
                "region": location,
                "revision": response.template.revision
            })
            
        except Exception as e:
            error_msg = f"Error deploying to Cloud Run: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="cloud",
                    operation="deploy_to_cloud_run"
                ).inc()
            return json.dumps({
                "success": False,
                "error": error_msg
            })
    
    @tool("Upload files to Cloud Storage")
    def upload_to_cloud_storage(self, local_path: str, goal_id: str, destination_folder: Optional[str] = None) -> str:
        """
        Upload files or directories to Google Cloud Storage.
        
        Args:
            local_path: Path to local file or directory to upload
            goal_id: The ID of the current goal
            destination_folder: Optional folder name within the bucket
            
        Returns:
            JSON string with upload results and GCS URI
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            from google.cloud import storage
            import os
            
            # Initialize client
            client = storage.Client()
            
            # Get or create bucket
            bucket_name = self.config.get("gcp_config_defaults", {}).get("gcs_bucket_name", "ai_architect_storage")
            
            try:
                bucket = client.get_bucket(bucket_name)
            except Exception:
                # Create bucket if it doesn't exist
                project_id = self.config.get("gcp_config_defaults", {}).get("project_id")
                location = self.config.get("gcp_config_defaults", {}).get("region", "us-central1")
                
                bucket = client.create_bucket(
                    bucket_name,
                    project=project_id,
                    location=location
                )
                logger.info(f"Created new GCS bucket: {bucket_name}")
            
            # Define destination path
            if not destination_folder:
                destination_folder = f"goals/{goal_id}"
            
            uploaded_files = []
            gcs_uris = []
            
            # Upload file or directory
            if os.path.isfile(local_path):
                # Single file upload
                filename = os.path.basename(local_path)
                blob_name = f"{destination_folder}/{filename}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_path)
                
                uploaded_files.append(filename)
                gcs_uris.append(f"gs://{bucket_name}/{blob_name}")
            
            elif os.path.isdir(local_path):
                # Directory upload
                for root, _, files in os.walk(local_path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        rel_path = os.path.relpath(filepath, local_path)
                        blob_name = f"{destination_folder}/{rel_path}"
                        
                        blob = bucket.blob(blob_name)
                        blob.upload_from_filename(filepath)
                        
                        uploaded_files.append(rel_path)
                        gcs_uris.append(f"gs://{bucket_name}/{blob_name}")
            
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Path not found: {local_path}"
                })
                
            # Store upload record in memory
            if self.memory_manager:
                asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=json.dumps({
                            "bucket": bucket_name,
                            "destination_folder": destination_folder,
                            "uploaded_files": uploaded_files,
                            "gcs_uris": gcs_uris
                        }),
                        namespace="deployment_history",
                        metadata={
                            "type": "gcs_upload",
                            "goal_id": goal_id,
                            "file_count": len(uploaded_files)
                        }
                    )
                )
            
            # Track timing and success metrics
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="cloud",
                    operation="upload_to_cloud_storage"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="cloud",
                    operation="upload_to_cloud_storage"
                ).inc()
            
            primary_uri = f"gs://{bucket_name}/{destination_folder}"
            
            return json.dumps({
                "success": True,
                "bucket": bucket_name,
                "destination_folder": destination_folder,
                "uploaded_files": uploaded_files,
                "gcs_uri": primary_uri,
                "file_count": len(uploaded_files)
            })
            
        except Exception as e:
            error_msg = f"Error uploading to Cloud Storage: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="cloud",
                    operation="upload_to_cloud_storage"
                ).inc()
            return json.dumps({
                "success": False,
                "error": error_msg
            })
    
    @tool("Build Docker image with Cloud Build")
    def build_docker_image(self, source_uri: str, goal_id: str, dockerfile_path: Optional[str] = None, image_name: Optional[str] = None) -> str:
        """
        Build a Docker image using Google Cloud Build.
        
        Args:
            source_uri: GCS URI pointing to the source code directory
            goal_id: The ID of the current goal 
            dockerfile_path: Optional path to the Dockerfile within the source directory
            image_name: Optional custom name for the resulting image
            
        Returns:
            JSON string with build results
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            from google.cloud import build_v1
            from google.cloud.devtools import cloudbuild_v1
            
            # Initialize client
            client = build_v1.CloudBuildClient()
            
            # Get project ID
            project_id = self.config.get("gcp_config_defaults", {}).get("project_id")
            
            # Get defaults from config
            if not image_name:
                repo_name = self.config.get("gcp_config_defaults", {}).get("artifact_registry_repository")
                location = self.config.get("gcp_config_defaults", {}).get("region", "us-central1")
                image_name = f"{location}-docker.pkg.dev/{project_id}/{repo_name}/app-{goal_id}"
            
            # Create build config
            build = cloudbuild_v1.Build()
            build.source.storage_source.bucket = source_uri.split("//")[1].split("/")[0]
            build.source.storage_source.object = "/".join(source_uri.split("//")[1].split("/")[1:])
            
            # Add build step
            build_step = cloudbuild_v1.BuildStep()
            build_step.name = "gcr.io/cloud-builders/docker"
            
            dockerfile_arg = f"-f {dockerfile_path}" if dockerfile_path else ""
            build_step.args = [
                "build",
                dockerfile_arg,
                "-t", image_name,
                "."
            ]
            
            build.steps.append(build_step)
            
            # Add image push step
            push_step = cloudbuild_v1.BuildStep()
            push_step.name = "gcr.io/cloud-builders/docker"
            push_step.args = ["push", image_name]
            
            build.steps.append(push_step)
            
            # Set timeout
            build.timeout.seconds = int(self.config.get("cloud_build_timeout_seconds", 1800))
            
            # Start build
            operation = client.create_build(project_id=project_id, build=build)
            
            # Get operation ID
            operation_id = operation.metadata.build.id
            
            # Store build record in memory
            if self.memory_manager:
                asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=json.dumps({
                            "build_id": operation_id,
                            "source_uri": source_uri,
                            "image_name": image_name,
                            "build_log_url": f"https://console.cloud.google.com/cloud-build/builds/{operation_id}?project={project_id}"
                        }),
                        namespace="deployment_history",
                        metadata={
                            "type": "cloud_build",
                            "goal_id": goal_id,
                            "image_name": image_name
                        }
                    )
                )
            
            # Track timing and success metrics
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="cloud",
                    operation="build_docker_image"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="cloud",
                    operation="build_docker_image"
                ).inc()
            
            return json.dumps({
                "success": True,
                "message": f"Build started with ID: {operation_id}",
                "build_id": operation_id,
                "build_log_url": f"https://console.cloud.google.com/cloud-build/builds/{operation_id}?project={project_id}",
                "image_name": image_name
            })
            
        except Exception as e:
            error_msg = f"Error building Docker image: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="cloud",
                    operation="build_docker_image"
                ).inc()
            return json.dumps({
                "success": False,
                "error": error_msg
            })
    
    @tool("Manage Artifact Registry repository")
    def manage_artifact_registry(self, operation: str, repository_name: Optional[str] = None, repository_format: str = "DOCKER") -> str:
        """
        Manage Google Artifact Registry repositories.
        
        Args:
            operation: Operation to perform (create, list)
            repository_name: Name of the repository to create or manage
            repository_format: Format of the repository (DOCKER, NPM, etc.)
            
        Returns:
            JSON string with operation results
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            from google.cloud import artifactregistry_v1
            
            # Get defaults from config
            if not repository_name:
                repository_name = self.config.get("gcp_config_defaults", {}).get("artifact_registry_repository")
            
            location = self.config.get("gcp_config_defaults", {}).get("region", "us-central1")
            
            # Initialize client
            client = artifactregistry_v1.ArtifactRegistryClient()
            
            # Get project ID
            project_id = self.config.get("gcp_config_defaults", {}).get("project_id")
            
            # Perform the requested operation
            if operation == "create":
                # Check if repository exists
                parent = f"projects/{project_id}/locations/{location}"
                repositories = client.list_repositories(parent=parent)
                
                repository_exists = False
                for repo in repositories:
                    if repo.name.split("/")[-1] == repository_name:
                        repository_exists = True
                        break
                
                if repository_exists:
                    return json.dumps({
                        "success": True,
                        "message": f"Repository {repository_name} already exists",
                        "repository_path": f"{location}-docker.pkg.dev/{project_id}/{repository_name}"
                    })
                
                # Create repository if it doesn't exist
                repository = artifactregistry_v1.Repository(
                    description="Artifact repository for the Autonomous AI Architect system",
                    format_=getattr(artifactregistry_v1.Repository.Format, repository_format)
                )
                
                request = artifactregistry_v1.CreateRepositoryRequest(
                    parent=parent,
                    repository_id=repository_name,
                    repository=repository
                )
                
                operation = client.create_repository(request=request)
                response = operation.result()
                
                # Grant Cloud Build service account access to the repo
                from google.iam.v1 import policy_pb2, binding_pb2
                iam_policy = client.get_iam_policy(request={"resource": response.name})
                
                cloud_build_sa = f"serviceAccount:{project_id}@cloudbuild.gserviceaccount.com"
                binding_exists = False
                
                for binding in iam_policy.bindings:
                    if binding.role == "roles/artifactregistry.writer":
                        if cloud_build_sa in binding.members:
                            binding_exists = True
                            break
                
                if not binding_exists:
                    binding = binding_pb2.Binding()
                    binding.role = "roles/artifactregistry.writer"
                    binding.members.append(cloud_build_sa)
                    iam_policy.bindings.append(binding)
                    
                    client.set_iam_policy(
                        request={
                            "resource": response.name,
                            "policy": iam_policy
                        }
                    )
                
                return json.dumps({
                    "success": True,
                    "message": f"Repository {repository_name} created successfully",
                    "repository_path": f"{location}-docker.pkg.dev/{project_id}/{repository_name}"
                })
                
            elif operation == "list":
                # List repositories
                parent = f"projects/{project_id}/locations/{location}"
                repositories = client.list_repositories(parent=parent)
                
                repos = []
                for repo in repositories:
                    repos.append({
                        "name": repo.name.split("/")[-1],
                        "format": repo.format_.name,
                        "description": repo.description,
                        "create_time": repo.create_time.isoformat() if hasattr(repo, 'create_time') and repo.create_time else None,
                        "update_time": repo.update_time.isoformat() if hasattr(repo, 'update_time') and repo.update_time else None
                    })
                
                return json.dumps({
                    "success": True,
                    "repositories": repos
                })
                
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                })
                
            # Track timing and success metrics
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="cloud",
                    operation="manage_artifact_registry"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="cloud",
                    operation="manage_artifact_registry"
                ).inc()
            
        except Exception as e:
            error_msg = f"Error managing Artifact Registry: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="cloud",
                    operation="manage_artifact_registry"
                ).inc()
            return json.dumps({
                "success": False,
                "error": error_msg
            })
    
    @tool("List cloud resources")
    def list_cloud_resources(self, resource_type: str, goal_id: Optional[str] = None) -> str:
        """
        List cloud resources of a specific type.
        
        Args:
            resource_type: Type of resource to list (cloud_run, cloud_storage, cloud_build)
            goal_id: Optional goal ID to filter resources
            
        Returns:
            JSON string with list of resources
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Get project ID and region
            project_id = self.config.get("gcp_config_defaults", {}).get("project_id")
            location = self.config.get("gcp_config_defaults", {}).get("region", "us-central1")
            
            result = {
                "success": True,
                "resource_type": resource_type,
                "resources": []
            }
            
            if resource_type == "cloud_run":
                from google.cloud import run_v2
                
                # Initialize client
                client = run_v2.ServicesClient()
                
                # List services
                parent = f"projects/{project_id}/locations/{location}"
                services = client.list_services(parent=parent)
                
                for service in services:
                    # Filter by goal_id if provided
                    if goal_id and goal_id not in service.name:
                        continue
                        
                    result["resources"].append({
                        "name": service.name.split("/")[-1],
                        "url": service.uri,
                        "created_at": service.create_time.isoformat() if service.create_time else None,
                        "updated_at": service.update_time.isoformat() if service.update_time else None
                    })
            
            elif resource_type == "cloud_storage":
                from google.cloud import storage
                
                # Initialize client
                client = storage.Client()
                
                # List buckets
                buckets = client.list_buckets()
                
                for bucket in buckets:
                    result["resources"].append({
                        "name": bucket.name,
                        "location": bucket.location,
                        "storage_class": bucket.storage_class,
                        "created_at": bucket.time_created.isoformat() if bucket.time_created else None
                    })
            
            elif resource_type == "cloud_build":
                from google.cloud import build_v1
                
                # Initialize client
                client = build_v1.CloudBuildClient()
                
                # List builds
                parent = f"projects/{project_id}"
                builds = client.list_builds(parent=parent)
                
                for build in builds:
                    # Filter by goal_id if provided
                    if goal_id and goal_id not in build.id:
                        continue
                        
                    result["resources"].append({
                        "id": build.id,
                        "status": build.status.name,
                        "create_time": build.create_time.isoformat() if build.create_time else None,
                        "finish_time": build.finish_time.isoformat() if build.finish_time else None,
                        "log_url": f"https://console.cloud.google.com/cloud-build/builds/{build.id}?project={project_id}"
                    })
            
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown resource type: {resource_type}"
                })
            
            # Track timing and success metrics
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="cloud",
                    operation="list_cloud_resources"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="cloud",
                    operation="list_cloud_resources"
                ).inc()
            
            return json.dumps(result)
            
        except Exception as e:
            error_msg = f"Error listing cloud resources: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="cloud",
                    operation="list_cloud_resources"
                ).inc()
            return json.dumps({
                "success": False,
                "error": error_msg
            })
