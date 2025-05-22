#!/usr/bin/env python3

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid

logger = logging.getLogger("ai-architect-backend.planner_agent")

class PlannerAgent:
    """
    Planner Agent: Responsible for breaking down high-level goals into
    specific, actionable tasks. This agent creates detailed implementation
    plans and coordinates the overall execution flow.
    """
    
    def __init__(self, 
                llm_router=None,
                memory_manager=None,
                monitoring_system=None,
                config=None):
        """
        Initialize the planner agent.
        
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
        
        # Load planner agent prompt template from config
        self.prompt_template = self.config.get(
            "planner_agent_prompt_template", 
            "You are an AI Architect's master planning agent. Your task is to receive a high-level user goal and break it into actionable tasks."
        )
        
        logger.info("Planner agent initialized")
    
    async def initialize(self):
        """Initialize the planner agent with CrewAI."""
        if self.agent:
            return self.agent
            
        try:
            # Create the agent - we'll implement CrewAI integration when it's available
            logger.info("Planner agent initialized without CrewAI - using direct LLM calls")
            
            if self.monitoring_system:
                self.monitoring_system.agent_initialization_counter.labels(
                    agent_type="planner").inc()
            
            return self
            
        except Exception as e:
            logger.error(f"Error initializing planner agent: {str(e)}")
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="planner", 
                    operation="initialize"
                ).inc()
            raise
    
    async def create_implementation_plan(self, user_goal: str, user_analysis: Optional[str] = None) -> str:
        """
        Create a detailed implementation plan for achieving a goal.
        
        Args:
            user_goal: The high-level goal to plan for
            user_analysis: Optional client-side analysis or requirements
            
        Returns:
            JSON string with ordered task list
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            prompt = f"""
            You are a project planner specializing in software architecture and implementation.
            Create a detailed implementation plan for the following goal:
            
            GOAL: {user_goal}
            
            {f"ADDITIONAL CONTEXT: {user_analysis}" if user_analysis else ""}
            
            Break down the goal into specific, actionable tasks. For each task, include:
            1. A task ID
            2. A descriptive title
            3. A detailed description of what needs to be done
            4. Any dependencies on other tasks (by ID)
            5. Estimated complexity (Low, Medium, High)
            
            Return your plan as a valid JSON array of task objects with the structure:
            [
              {{
                "id": "task1",
                "title": "Task title",
                "description": "Detailed description",
                "dependencies": ["task_id1", "task_id2"],
                "complexity": "Medium"
              }},
              // More tasks...
            ]
            
            Ensure your response is a valid JSON array.
            """
            
            llm_response = await self.llm_router.generate(
                messages=[
                    {"role": "system", "content": "You are a software architecture planning assistant."},
                    {"role": "user", "content": prompt}
                ],
                model="azure",  # Try to use Azure OpenAI first
                temperature=0.1,
                max_tokens=4000
            )
            
            # Ensure the output is valid JSON by extracting any JSON structure
            import re
            json_match = re.search(r'\[\s*{.*}\s*\]', llm_response, re.DOTALL)
            if json_match:
                try:
                    # Validate by parsing and re-stringifying
                    tasks_json = json.loads(json_match.group(0))
                    llm_response = json.dumps(tasks_json, indent=2)
                except json.JSONDecodeError:
                    # If the extracted JSON is invalid, return the full response
                    pass
            
            # Store in memory
            if self.memory_manager:
                memory_id = await self.memory_manager.store_memory(
                    content=llm_response,
                    namespace="execution_history",
                    metadata={
                        "type": "implementation_plan",
                        "goal": user_goal,
                        "has_user_analysis": bool(user_analysis)
                    }
                )
            
            # Track timing
            if self.monitoring_system:
                duration = asyncio.get_event_loop().time() - start_time
                self.monitoring_system.agent_operation_duration.labels(
                    agent_type="planner",
                    operation="create_implementation_plan"
                ).observe(duration)
                self.monitoring_system.agent_operation_counter.labels(
                    agent_type="planner",
                    operation="create_implementation_plan"
                ).inc()
            
            return llm_response
            
        except Exception as e:
            error_msg = f"Error creating implementation plan: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="planner",
                    operation="create_implementation_plan"
                ).inc()
            return f"Failed to create implementation plan: {str(e)}"
    
    async def task_breakdown(self, task_description: str) -> str:
        """
        Break down a complex task into smaller, more manageable subtasks.
        
        Args:
            task_description: Description of the task to break down
            
        Returns:
            JSON string with subtasks
        """
        try:
            # Similar implementation as create_implementation_plan but for subtask breakdown
            # ...existing code...
            return "Subtask breakdown implementation placeholder"
            
        except Exception as e:
            error_msg = f"Error breaking down task: {str(e)}"
            logger.error(error_msg)
            if self.monitoring_system:
                self.monitoring_system.agent_error_counter.labels(
                    agent_type="planner",
                    operation="task_breakdown"
                ).inc()
            return f"Failed to break down task: {str(e)}"
    
    # Other methods (dependency_analysis, estimate_effort) would have similar implementations
    # ...existing code...