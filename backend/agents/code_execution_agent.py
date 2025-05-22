#!/usr/bin/env python3

import os
import json
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid
import shutil
import re

from crewai import Agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger("ai-architect-backend.code_execution_agent")

class CodeExecutionAgent:
    """
    Code Execution Agent: Responsible for generating code, executing it 
    in a secure sandbox, and validating results. This agent implements
    secure code execution with various isolation levels.
    """
    
    def __init__(self, 
                llm_router=None,
                memory_manager=None,
                monitoring_system=None,
                safety_sandbox=None,
                config=None):
        """
        Initialize the code execution agent.
        
        Args:
            llm_router: LLM router for model access
            memory_manager: Memory manager for storing results
            monitoring_system: Monitoring system for metrics
            safety_sandbox: Safety sandbox for code execution
            config: Configuration dictionary
        """
        self.llm_router = llm_router
        self.memory_manager = memory_manager
        self.monitoring_system = monitoring_system
        self.safety_sandbox = safety_sandbox
        self.config = config or {}
        self.agent = None
        
        # Output base path for code executions
        self.output_base_path = self.config.get(
            "output_base_path_code_executions", 
            "./backend/outputs/code_executions"
        )
        
        # Timeout for code execution in seconds
        self.execution_timeout = self.config.get(
            "code_execution_timeout_seconds", 
            600
        )
        
        # Default port for generated applications
        self.default_app_port = self.config.get(
            "default_generated_app_port", 
            8080
        )
        
        logger.info("Code execution agent initialized")
    
    async def initialize(self):
        """Initialize the code execution agent with CrewAI."""
        if self.agent:
            return self.agent
            
        try:
            # Create tools for the agent
            tools = [
                self.generate_code,
                self.execute_code,
                self.generate_dockerfile,
                self.validate_code
            ]
            
            # Use Gemini Pro by default for code tasks
            llm = await self.llm_router.get_llm("gemini-2.5-pro-preview-04-11")
            
            # Create the agent
            self.agent = Agent(
                role="Senior Software Developer",
                goal="Generate and execute high-quality code securely",
                backstory=(
                    "You are an expert developer with extensive experience across "
                    "multiple programming languages. You excel at writing clean, "
                    "efficient, and maintainable code. You also know how to properly "
                    "test and validate code. Security and best practices are your priority."
                ),
                verbose=True,
                llm=llm,
                tools=tools,
                allow_delegation=True
            )
            
            logger.info("Code execution agent fully initialized with CrewAI")
            
            if self.monitoring_system:
                self.monitoring_system.agent_initialization_counter.labels(
                    agent_type="code_execution").inc()
            
            return self.agent
            
        except Exception as e:
            logger.error(f"Error initializing code execution agent: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="code_execution", 
                    operation="initialize"
                ).inc()
            raise
    
    @tool("Generate code")
    def generate_code(self, code_request: Dict[str, Any]) -> str:
        """
        Generate code based on specifications.
        
        Args:
            code_request: Dictionary with code generation parameters
                - language: Programming language (e.g., "Python", "JavaScript")
                - framework: Framework to use (e.g., "FastAPI", "React")
                - details: Detailed requirements for the code
                - output_dir: Optional directory to save the generated code
            
        Returns:
            Path to the generated code and summary
        """
        if isinstance(code_request, str):
            try:
                code_request = json.loads(code_request)
            except json.JSONDecodeError:
                code_request = {
                    "language": "Python",
                    "details": code_request
                }
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Extract parameters
            language = code_request.get("language", "Python")
            framework = code_request.get("framework", "")
            details = code_request.get("details", "")
            output_dir = code_request.get("output_dir")
            
            # Create unique output directory if not specified
            if not output_dir:
                execution_id = str(uuid.uuid4())[:8]
                timestamp = int(time.time())
                output_dir = os.path.join(
                    self.output_base_path,
                    f"{timestamp}_{execution_id}"
                )
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate code using sandbox to isolate the execution
            sandbox_result = asyncio.get_event_loop().run_until_complete(
                self.safety_sandbox.execute_code_generation(
                    language=language,
                    framework=framework,
                    details=details,
                    working_dir=output_dir,
                    timeout_seconds=self.execution_timeout
                )
            )
            
            # Create summary of generated files
            files_list = []
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, output_dir)
                    files_list.append(rel_path)
            
            # Identify main entry point and dependencies file
            entrypoint_file = None
            dependencies_file = None
            
            # Common patterns for entry points and dependencies
            entry_patterns = {
                "Python": ["main.py", "app.py", "index.py"],
                "JavaScript": ["index.js", "app.js", "server.js"],
                "TypeScript": ["index.ts", "app.ts", "server.ts"]
            }
            
            dep_patterns = {
                "Python": ["requirements.txt"],
                "JavaScript": ["package.json"],
                "TypeScript": ["package.json"]
            }
            
            lang_patterns = entry_patterns.get(language, entry_patterns["Python"])
            for pattern in lang_patterns:
                for file in files_list:
                    if file.endswith(pattern) or file == pattern:
                        entrypoint_file = file
                        break
                if entrypoint_file:
                    break
            
            dep_lang_patterns = dep_patterns.get(language, dep_patterns["Python"])
            for pattern in dep_lang_patterns:
                for file in files_list:
                    if file.endswith(pattern) or file == pattern:
                        dependencies_file = file
                        break
                if dependencies_file:
                    break
            
            # Create result
            result = {
                "generated_code_path": output_dir,
                "entrypoint_file": entrypoint_file,
                "dependencies_file": dependencies_file,
                "files": files_list,
                "summary": sandbox_result.get("summary", "Code generated successfully"),
                "language": language,
                "framework": framework
            }
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=json.dumps(result, indent=2),
                        namespace="code_snippets",
                        metadata={
                            "type": "generated_code",
                            "language": language,
                            "framework": framework,
                            "path": output_dir
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="code_execution",
                    operation="generate_code"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="code_execution",
                    operation="generate_code"
                ).inc()
                # Track code generation size
                self.monitoring_system.code_generation_files_count.observe(len(files_list))
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error generating code: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="code_execution",
                    operation="generate_code"
                ).inc()
            return json.dumps({
                "error": error_msg,
                "generated_code_path": output_dir if 'output_dir' in locals() else None
            })
    
    @tool("Execute code")
    def execute_code(self, execution_request: Dict[str, Any]) -> str:
        """
        Execute generated code in a secure sandbox.
        
        Args:
            execution_request: Dictionary with execution parameters
                - code_path: Path to the code to execute
                - entrypoint_file: Main file to execute 
                - command: Optional specific command to run
                - timeout_seconds: Optional timeout override
            
        Returns:
            Execution results including output and any errors
        """
        if isinstance(execution_request, str):
            try:
                execution_request = json.loads(execution_request)
            except json.JSONDecodeError:
                return json.dumps({
                    "error": "Invalid execution request format. Expected JSON."
                })
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Extract parameters
            code_path = execution_request.get("code_path")
            entrypoint_file = execution_request.get("entrypoint_file")
            command = execution_request.get("command")
            timeout_seconds = execution_request.get("timeout_seconds", self.execution_timeout)
            
            if not code_path:
                return json.dumps({
                    "error": "Missing required parameter: code_path"
                })
            
            # Ensure the code path exists
            if not os.path.exists(code_path):
                return json.dumps({
                    "error": f"Code path does not exist: {code_path}"
                })
            
            # If no explicit command is provided, try to infer one based on the entrypoint
            if not command and entrypoint_file:
                file_ext = os.path.splitext(entrypoint_file)[1]
                if file_ext == '.py':
                    command = f"cd {code_path} && python {entrypoint_file}"
                elif file_ext == '.js':
                    command = f"cd {code_path} && node {entrypoint_file}"
                elif file_ext == '.ts':
                    command = f"cd {code_path} && npx ts-node {entrypoint_file}"
                else:
                    return json.dumps({
                        "error": f"Unsupported file type for automatic execution: {file_ext}"
                    })
            
            # Execute the code in the sandbox
            sandbox_result = asyncio.get_event_loop().run_until_complete(
                self.safety_sandbox.execute_command(
                    command=command,
                    working_dir=code_path,
                    timeout_seconds=timeout_seconds,
                    allow_network=True,  # Allow network for most code executions
                    capture_stdout=True,
                    capture_stderr=True
                )
            )
            
            # Create result
            result = {
                "code_path": code_path,
                "command": command,
                "success": sandbox_result.get("success", False),
                "stdout": sandbox_result.get("stdout", ""),
                "stderr": sandbox_result.get("stderr", ""),
                "execution_time": sandbox_result.get("execution_time", 0)
            }
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=json.dumps(result, indent=2),
                        namespace="execution_history",
                        metadata={
                            "type": "code_execution",
                            "path": code_path,
                            "command": command,
                            "success": result["success"]
                        }
                    )
                )
            
            # Track timing and metrics
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="code_execution",
                    operation="execute_code"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="code_execution",
                    operation="execute_code"
                ).inc()
                
                # Track execution success/failure
                if result["success"]:
                    self.monitoring_system.code_execution_success_counter.inc()
                else:
                    self.monitoring_system.code_execution_failure_counter.inc()
                
                # Track execution time
                self.monitoring_system.code_execution_time.observe(result["execution_time"])
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error executing code: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="code_execution",
                    operation="execute_code"
                ).inc()
            return json.dumps({
                "error": error_msg,
                "success": False
            })
    
    @tool("Generate Dockerfile")
    def generate_dockerfile(self, dockerfile_request: Dict[str, Any]) -> str:
        """
        Generate a Dockerfile for the application.
        
        Args:
            dockerfile_request: Dictionary with Dockerfile parameters
                - code_path: Path to the code
                - language: Programming language
                - entrypoint_file: Main file to execute
                - port: Port to expose (default: 8080)
            
        Returns:
            Path to the generated Dockerfile
        """
        if isinstance(dockerfile_request, str):
            try:
                dockerfile_request = json.loads(dockerfile_request)
            except json.JSONDecodeError:
                return json.dumps({
                    "error": "Invalid Dockerfile request format. Expected JSON."
                })
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Extract parameters
            code_path = dockerfile_request.get("code_path")
            language = dockerfile_request.get("language", "Python")
            entrypoint_file = dockerfile_request.get("entrypoint_file")
            dependencies_file = dockerfile_request.get("dependencies_file")
            port = dockerfile_request.get("port", self.default_app_port)
            
            if not code_path:
                return json.dumps({
                    "error": "Missing required parameter: code_path"
                })
            
            # Ensure the code path exists
            if not os.path.exists(code_path):
                return json.dumps({
                    "error": f"Code path does not exist: {code_path}"
                })
            
            # Generate Dockerfile prompt based on language
            dockerfile_prompt = f"""
            Generate a production-ready Dockerfile for the following application:
            
            Language: {language}
            Entrypoint File: {entrypoint_file or 'Not specified'}
            Dependencies File: {dependencies_file or 'Not specified'}
            Port to Expose: {port}
            
            Requirements:
            1. Use official base images with specific version tags (not 'latest')
            2. Include proper security practices (run as non-root if possible)
            3. Optimize for build speed and image size (multi-stage if appropriate)
            4. Set appropriate environment variables (e.g., PYTHONUNBUFFERED=1 for Python)
            5. Include proper health checks
            6. Include proper handling of signals
            7. Expose the specified port: {port}
            
            Return ONLY the Dockerfile content, nothing else.
            """
            
            # Generate Dockerfile content
            dockerfile_content = asyncio.get_event_loop().run_until_complete(
                self.llm_router.generate_text(
                    prompt=dockerfile_prompt,
                    model="gemini-2.5-pro-preview-04-11",
                    max_tokens=1500
                )
            )
            
            # Clean up the Dockerfile content (remove markdown formatting if present)
            dockerfile_content = re.sub(r'```dockerfile\s+', '', dockerfile_content)
            dockerfile_content = re.sub(r'```\s*$', '', dockerfile_content)
            dockerfile_content = dockerfile_content.strip()
            
            # Write Dockerfile to the code directory
            dockerfile_path = os.path.join(code_path, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            # Create result
            result = {
                "dockerfile_path": dockerfile_path,
                "code_path": code_path,
                "language": language,
                "port": port
            }
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=dockerfile_content,
                        namespace="code_snippets",
                        metadata={
                            "type": "dockerfile",
                            "language": language,
                            "path": dockerfile_path
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="code_execution",
                    operation="generate_dockerfile"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="code_execution",
                    operation="generate_dockerfile"
                ).inc()
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error generating Dockerfile: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="code_execution",
                    operation="generate_dockerfile"
                ).inc()
            return json.dumps({
                "error": error_msg
            })
    
    @tool("Validate code")
    def validate_code(self, validation_request: Dict[str, Any]) -> str:
        """
        Validate generated code for quality and correctness.
        
        Args:
            validation_request: Dictionary with validation parameters
                - code_path: Path to the code to validate
                - language: Programming language
                - framework: Framework used
            
        Returns:
            Validation results including issues found
        """
        if isinstance(validation_request, str):
            try:
                validation_request = json.loads(validation_request)
            except json.JSONDecodeError:
                return json.dumps({
                    "error": "Invalid validation request format. Expected JSON."
                })
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Extract parameters
            code_path = validation_request.get("code_path")
            language = validation_request.get("language", "Python")
            framework = validation_request.get("framework", "")
            
            if not code_path:
                return json.dumps({
                    "error": "Missing required parameter: code_path"
                })
            
            # Ensure the code path exists
            if not os.path.exists(code_path):
                return json.dumps({
                    "error": f"Code path does not exist: {code_path}"
                })
            
            # Determine validation command based on language
            validation_command = None
            if language.lower() == "python":
                validation_command = f"cd {code_path} && python -m pylint --disable=C0111,C0103 **/*.py || true"
            elif language.lower() in ["javascript", "typescript"]:
                validation_command = f"cd {code_path} && npx eslint . || true"
            
            if not validation_command:
                return json.dumps({
                    "error": f"Unsupported language for validation: {language}"
                })
            
            # Execute validation command in sandbox
            validation_result = asyncio.get_event_loop().run_until_complete(
                self.safety_sandbox.execute_command(
                    command=validation_command,
                    working_dir=code_path,
                    timeout_seconds=120,  # Shorter timeout for validation
                    allow_network=True,  # May need to download validation tools
                    capture_stdout=True,
                    capture_stderr=True
                )
            )
            
            # Get file list for manual validation if linting fails
            files_to_analyze = []
            for root, _, files in os.walk(code_path):
                for file in files:
                    if (language.lower() == "python" and file.endswith(".py")) or \
                       (language.lower() == "javascript" and file.endswith(".js")) or \
                       (language.lower() == "typescript" and file.endswith(".ts")):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, code_path)
                        with open(file_path, 'r') as f:
                            content = f.read()
                        files_to_analyze.append({"path": rel_path, "content": content})
            
            # If files are too many, just get the first 5 most important ones
            if len(files_to_analyze) > 5:
                important_patterns = ["main", "app", "index", "server"]
                important_files = []
                other_files = []
                
                for file_info in files_to_analyze:
                    file_path = file_info["path"]
                    if any(pattern in file_path.lower() for pattern in important_patterns):
                        important_files.append(file_info)
                    else:
                        other_files.append(file_info)
                
                files_to_analyze = important_files + other_files
                files_to_analyze = files_to_analyze[:5]
            
            # Manual code analysis using LLM
            file_contents = "\n\n".join([
                f"File: {file_info['path']}\n```\n{file_info['content']}\n```"
                for file_info in files_to_analyze
            ])
            
            analysis_prompt = f"""
            You are an expert code reviewer. Analyze the following code for quality issues, bugs, and best practices:
            
            Language: {language}
            Framework: {framework}
            
            {file_contents}
            
            Focus on:
            1. Logic errors and bugs
            2. Security vulnerabilities
            3. Performance issues
            4. Architecture problems
            5. Best practices violations
            6. Documentation and readability
            
            For each issue found, provide:
            - File path
            - Issue description
            - Severity (High, Medium, Low)
            - Recommended fix
            
            Return your analysis as a structured list of issues.
            """
            
            manual_analysis = asyncio.get_event_loop().run_until_complete(
                self.llm_router.generate_text(
                    prompt=analysis_prompt,
                    model="gemini-2.5-pro-preview-04-11",
                    max_tokens=2500
                )
            )
            
            # Create result
            result = {
                "code_path": code_path,
                "language": language,
                "framework": framework,
                "linter_output": validation_result.get("stdout", ""),
                "linter_errors": validation_result.get("stderr", ""),
                "manual_analysis": manual_analysis,
                "files_analyzed": [file_info["path"] for file_info in files_to_analyze]
            }
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=json.dumps(result, indent=2),
                        namespace="execution_history",
                        metadata={
                            "type": "code_validation",
                            "language": language,
                            "framework": framework,
                            "path": code_path
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="code_execution",
                    operation="validate_code"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="code_execution",
                    operation="validate_code"
                ).inc()
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error validating code: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="code_execution",
                    operation="validate_code"
                ).inc()
            return json.dumps({
                "error": error_msg
            })
