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

logger = logging.getLogger("ai-architect-backend.architect_agent")

class ArchitectAgent:
    """
    Architect Agent: Responsible for high-level architecture decisions
    and system design. This agent determines the overall structure of
    the application, technology choices, and best practices.
    """
    
    def __init__(self, 
                llm_router=None,
                memory_manager=None,
                monitoring_system=None,
                safety_sandbox=None,
                config=None):
        """
        Initialize the architect agent.
        
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
        
        logger.info("Architect agent initialized")
    
    async def initialize(self):
        """Initialize the architect agent with CrewAI."""
        if self.agent:
            return self.agent
            
        try:
            # Create tools for the agent
            tools = [
                self.research_tech_stack,
                self.evaluate_architecture,
                self.generate_system_diagram,
                self.check_best_practices
            ]
            
            # Use Gemini Pro by default for architecture tasks
            llm = await self.llm_router.get_llm("gemini-2.5-pro-preview-04-11")
            
            # Create the agent
            self.agent = Agent(
                role="Senior Software Architect",
                goal="Design robust, scalable and maintainable software architectures",
                backstory=(
                    "You are an expert software architect with decades of experience "
                    "designing complex systems. You excel at choosing the right technologies, "
                    "considering scalability, maintenance, and best practices. You are "
                    "especially skilled at cloud-native architectures and microservices."
                ),
                verbose=True,
                llm=llm,
                tools=tools,
                allow_delegation=True
            )
            
            logger.info("Architect agent fully initialized with CrewAI")
            
            if self.monitoring_system:
                self.monitoring_system.agent_initialization_counter.labels(
                    agent_type="architect").inc()
            
            return self.agent
            
        except Exception as e:
            logger.error(f"Error initializing architect agent: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="architect", 
                    operation="initialize"
                ).inc()
            raise
    
    @tool("Research technology stack")
    def research_tech_stack(self, query: str) -> str:
        """
        Research and recommend appropriate technology stack for a given project.
        
        Args:
            query: Details about the project requirements
            
        Returns:
            Recommended technology stack with rationale
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # This would normally be an async call, but CrewAI tools are synchronous
            # We'll use asyncio.run_until_complete to handle this
            llm_response = asyncio.get_event_loop().run_until_complete(
                self.llm_router.generate_text(
                    prompt=f"""
                    You are a technology expert specializing in software architecture.
                    Research and recommend the most appropriate technology stack for the following project:
                    
                    {query}
                    
                    Consider:
                    1. Scalability requirements
                    2. Performance considerations
                    3. Development speed and team expertise
                    4. Maintenance and long-term support
                    5. Industry best practices and trends
                    
                    Provide a detailed recommendation with:
                    - Frontend technologies
                    - Backend technologies
                    - Database solutions
                    - Infrastructure and deployment options
                    - Rationale for each choice
                    """,
                    model="gemini-2.5-pro-preview-04-11",
                    max_tokens=2000
                )
            )
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=llm_response,
                        namespace="code_snippets",
                        metadata={
                            "type": "tech_stack_research",
                            "query": query
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="architect",
                    operation="research_tech_stack"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="architect",
                    operation="research_tech_stack"
                ).inc()
            
            return llm_response
            
        except Exception as e:
            error_msg = f"Error researching tech stack: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="architect",
                    operation="research_tech_stack"
                ).inc()
            return f"Failed to research technology stack: {str(e)}"
    
    @tool("Evaluate architecture")
    def evaluate_architecture(self, architecture_description: str) -> str:
        """
        Evaluate a proposed architecture for a software system.
        
        Args:
            architecture_description: Description of the architecture to evaluate
            
        Returns:
            Evaluation with strengths, weaknesses, and recommendations
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            llm_response = asyncio.get_event_loop().run_until_complete(
                self.llm_router.generate_text(
                    prompt=f"""
                    You are an expert software architect tasked with evaluating the following system architecture:
                    
                    {architecture_description}
                    
                    Provide a comprehensive evaluation including:
                    1. Strengths of the architecture
                    2. Potential weaknesses or risks
                    3. Scalability assessment
                    4. Security considerations
                    5. Maintainability and extensibility
                    6. Specific recommendations for improvement
                    7. Alternative approaches to consider
                    
                    Format your response with clear sections and bullet points.
                    """,
                    model="gemini-2.5-pro-preview-04-11",
                    max_tokens=2000
                )
            )
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=llm_response,
                        namespace="code_snippets",
                        metadata={
                            "type": "architecture_evaluation",
                            "architecture": architecture_description[:200]  # Store truncated version
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="architect",
                    operation="evaluate_architecture"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="architect",
                    operation="evaluate_architecture"
                ).inc()
            
            return llm_response
            
        except Exception as e:
            error_msg = f"Error evaluating architecture: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="architect",
                    operation="evaluate_architecture"
                ).inc()
            return f"Failed to evaluate architecture: {str(e)}"
    
    @tool("Generate system diagram")
    def generate_system_diagram(self, system_description: str) -> str:
        """
        Generate a system diagram representation in Mermaid or PlantUML format.
        
        Args:
            system_description: Description of the system to diagram
            
        Returns:
            System diagram in Mermaid format
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            llm_response = asyncio.get_event_loop().run_until_complete(
                self.llm_router.generate_text(
                    prompt=f"""
                    You are a software architect experienced in creating system diagrams.
                    Based on the following system description, create a detailed system diagram 
                    using Mermaid markdown syntax.
                    
                    System Description:
                    {system_description}
                    
                    Create a Mermaid diagram showing the components, their relationships, and data flows.
                    Use flowchart or sequence diagram syntax as appropriate.
                    Include all major components, interfaces, data stores, and external systems.
                    
                    Return ONLY the Mermaid diagram code in the format:
                    ```mermaid
                    [your diagram code here]
                    ```
                    """,
                    model="gemini-2.5-pro-preview-04-11",
                    max_tokens=1500
                )
            )
            
            # Extract just the Mermaid diagram code
            import re
            mermaid_match = re.search(r'```mermaid\s+(.*?)\s+```', llm_response, re.DOTALL)
            if mermaid_match:
                diagram_code = mermaid_match.group(1)
                # Wrap it again in mermaid code block
                llm_response = f"```mermaid\n{diagram_code.strip()}\n```"
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=llm_response,
                        namespace="code_snippets",
                        metadata={
                            "type": "system_diagram",
                            "description": system_description[:200]  # Store truncated version
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="architect",
                    operation="generate_system_diagram"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="architect",
                    operation="generate_system_diagram"
                ).inc()
            
            return llm_response
            
        except Exception as e:
            error_msg = f"Error generating system diagram: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="architect",
                    operation="generate_system_diagram"
                ).inc()
            return f"Failed to generate system diagram: {str(e)}"
    
    @tool("Check architecture best practices")
    def check_best_practices(self, technology: str) -> str:
        """
        Provide best practices for a specific technology or architectural pattern.
        
        Args:
            technology: Technology or architectural pattern to check
            
        Returns:
            Best practices for the specified technology
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            llm_response = asyncio.get_event_loop().run_until_complete(
                self.llm_router.generate_text(
                    prompt=f"""
                    You are an expert software architect specializing in best practices.
                    Provide a comprehensive guide to best practices for implementing and working with:
                    
                    {technology}
                    
                    Include:
                    1. Architecture and design principles
                    2. Common pitfalls and how to avoid them
                    3. Scalability considerations
                    4. Security best practices
                    5. Performance optimization techniques
                    6. Testing approaches
                    7. Deployment and operational recommendations
                    8. Maintenance strategies
                    
                    Format your response with clear sections, bullet points, and code examples where appropriate.
                    """,
                    model="gemini-2.5-pro-preview-04-11",
                    max_tokens=2000
                )
            )
            
            # Store in memory
            if self.memory_manager:
                memory_id = asyncio.get_event_loop().run_until_complete(
                    self.memory_manager.store_memory(
                        content=llm_response,
                        namespace="code_snippets",
                        metadata={
                            "type": "best_practices",
                            "technology": technology
                        }
                    )
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="architect",
                    operation="check_best_practices"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="architect",
                    operation="check_best_practices"
                ).inc()
            
            return llm_response
            
        except Exception as e:
            error_msg = f"Error checking best practices: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="architect",
                    operation="check_best_practices"
                ).inc()
            return f"Failed to check best practices: {str(e)}"