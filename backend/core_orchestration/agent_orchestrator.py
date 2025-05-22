#!/usr/bin/env python3
# filepath: /home/donovan/Downloads/autonomous-ai-architect-ui (3)/backend/core_orchestration/agent_orchestrator.py

import logging
import asyncio
import json
import time
from typing import Dict, List, Any, Optional

from .llm_router import LLMRouter
from .monitoring_system import MonitoringSystem
from .safety_sandbox import SafetySandbox

# Import the memory manager for context
from tools.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates the interactions between various autonomous agents.
    Now enhanced with AZR for zero-shot planning and FFL for system improvement.
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        memory_manager: MemoryManager,
        safety_sandbox: SafetySandbox,
        monitoring_system: MonitoringSystem,
        azr=None,  # Make AZR optional for backward compatibility
        ffl=None,   # Make FFL optional for backward compatibility
        config: Dict[str, Any] = None
    ):
        self.llm_router = llm_router
        self.memory_manager = memory_manager
        self.safety_sandbox = safety_sandbox
        self.monitoring_system = monitoring_system
        self.azr = azr
        self.ffl = ffl
        self.config = config or {}
        
        # Map to track active orchestrations
        self.active_orchestrations = {}
        
        # Set the update_task_state function if provided in config
        self.update_task_state_fn = self.config.get("update_task_state_fn")
        
        logger.info("Agent Orchestrator initialized")
        if self.azr:
            logger.info("AZR integration enabled")
        if self.ffl:
            logger.info("FFL integration enabled")
        
    async def start_orchestration(self, goal_id: str, goal: str, client_analysis: Optional[str] = None):
        """
        Start the orchestration process for achieving a specific goal.
        Now enhanced with AZR for zero-shot planning and decomposition.
        """
        logger.info(f"Starting orchestration for goal {goal_id}: {goal}")
        
        start_time = time.time()
        plan = None
        
        # Track orchestration
        self.active_orchestrations[goal_id] = {
            "goal_id": goal_id,
            "goal": goal,
            "client_analysis": client_analysis,
            "start_time": start_time,
            "status": "planning",
            "plan": None,
        }
        
        # Update task state to indicate planning has started
        if self.update_task_state_fn:
            await self.update_task_state_fn(goal_id, {
                "status": "planning",
                "logs": ["Starting planning phase..."]
            })
        
        # Use Absolute Zero Reasoner to create a plan if available
        if self.azr:
            try:
                logger.info(f"Using AZR to decompose goal: {goal}")
                # Create zero-shot plan using AZR
                plan = await self.azr.decompose_task(goal, client_analysis)
                
                logger.info(f"AZR plan created with {len(plan.get('subtasks', []))} subtasks")
                
                # Update task state with plan
                if self.update_task_state_fn:
                    await self.update_task_state_fn(goal_id, {
                        "status": "planning_completed",
                        "plan": plan,
                        "logs": [f"Planning completed with {len(plan.get('subtasks', []))} subtasks"]
                    })
                
                # Record plan creation in monitoring
                self.monitoring_system.record_event(
                    event_type="plan_created",
                    event_data={"goal_id": goal_id, "subtasks_count": len(plan.get("subtasks", []))}
                )
                
                # Record metrics for Fractal Feedback Loop
                if self.ffl:
                    await self.ffl.record_metric(
                        category="planning_quality",
                        component="azr_planner",
                        value=1.0,  # Placeholder for actual quality assessment
                        metadata={"goal_id": goal_id, "subtasks_count": len(plan.get("subtasks", []))}
                    )
            except Exception as e:
                logger.error(f"Error creating plan with AZR: {e}")
                # Fallback to traditional planning if AZR fails
                if self.update_task_state_fn:
                    await self.update_task_state_fn(goal_id, {
                        "logs": [f"Error in AZR planning: {str(e)}. Falling back to traditional planning."]
                    })
                plan = await self._traditional_planning(goal, client_analysis)
        else:
            # Traditional planning without AZR
            logger.info("Using traditional planning (no AZR available)")
            plan = await self._traditional_planning(goal, client_analysis)
        
        # Update orchestration with plan
        self.active_orchestrations[goal_id]["plan"] = plan
        self.active_orchestrations[goal_id]["status"] = "executing"
        
        if self.update_task_state_fn:
            await self.update_task_state_fn(goal_id, {
                "status": "executing",
                "logs": ["Starting execution phase..."]
            })
        
        # Execute the plan here
        try:
            await self._execute_plan(goal_id, plan)
        except Exception as e:
            logger.error(f"Error executing plan: {e}")
            if self.update_task_state_fn:
                await self.update_task_state_fn(goal_id, {
                    "status": "failed",
                    "logs": [f"Execution failed: {str(e)}"]
                })
            return
        
        # Mark as complete when done
        execution_time = time.time() - start_time
        self.active_orchestrations[goal_id]["status"] = "completed"
        self.active_orchestrations[goal_id]["execution_time"] = execution_time
        
        if self.update_task_state_fn:
            await self.update_task_state_fn(goal_id, {
                "status": "completed",
                "execution_time": execution_time,
                "logs": [f"Goal completed in {execution_time:.2f} seconds"]
            })
        
        # Record completion metrics
        self.monitoring_system.record_event(
            event_type="orchestration_completed",
            event_data={"goal_id": goal_id, "execution_time": execution_time}
        )
        
        # Record quality metrics for Fractal Feedback Loop
        if self.ffl:
            await self.ffl.record_metric(
                category="orchestration_efficiency",
                component="orchestrator",
                value=60.0 / max(1, execution_time/60),  # Higher is better, normalize to tasks per minute
                metadata={"goal_id": goal_id}
            )
        
        logger.info(f"Completed orchestration for goal {goal_id} in {execution_time:.2f} seconds")
    
    async def _traditional_planning(self, goal: str, client_analysis: Optional[str] = None) -> Dict[str, Any]:
        """Legacy planning method without AZR."""
        logger.info("Using traditional planning approach")
        
        try:
            # Create a prompt for the LLM to generate a plan
            planning_prompt = f"""
            You are a software architect and project planner. Given the following goal, create a detailed plan 
            with specific, actionable tasks.
            
            GOAL: {goal}
            
            {f"ADDITIONAL CONTEXT: {client_analysis}" if client_analysis else ""}
            
            Break down the goal into tasks with the following structure:
            1. Task ID
            2. Task title
            3. Detailed description
            4. Dependencies (IDs of tasks that must be completed first)
            5. Estimated complexity (Low, Medium, High)
            
            Format your response as a JSON array of task objects.
            """
            
            # Call the LLM to generate a plan
            response = await self.llm_router.generate(
                messages=[
                    {"role": "system", "content": "You are a software architecture and planning assistant."},
                    {"role": "user", "content": planning_prompt}
                ],
                model="azure",  # Try to use Azure OpenAI
                temperature=0.1,
                max_tokens=3000
            )
            
            # Extract JSON content from the response
            import re
            json_match = re.search(r'\[\s*{.*}\s*\]', response, re.DOTALL)
            if json_match:
                try:
                    tasks = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    # Fallback to a simpler structure if JSON extraction fails
                    logger.warning("Failed to extract valid JSON from LLM response, using default plan")
                    tasks = [
                        {"id": "1", "title": "Analyze requirements", "description": "Analyze and clarify the project requirements", "dependencies": [], "complexity": "Medium"},
                        {"id": "2", "title": "Design architecture", "description": "Design the system architecture", "dependencies": ["1"], "complexity": "High"},
                        {"id": "3", "title": "Implement solution", "description": "Implement the designed solution", "dependencies": ["2"], "complexity": "High"},
                        {"id": "4", "title": "Test solution", "description": "Test the implemented solution", "dependencies": ["3"], "complexity": "Medium"},
                        {"id": "5", "title": "Deploy solution", "description": "Deploy the solution to production", "dependencies": ["4"], "complexity": "Medium"}
                    ]
            else:
                # If no JSON found, use default structure
                logger.warning("No JSON found in LLM response, using default plan")
                tasks = [
                    {"id": "1", "title": "Analyze requirements", "description": "Analyze and clarify the project requirements", "dependencies": [], "complexity": "Medium"},
                    {"id": "2", "title": "Design architecture", "description": "Design the system architecture", "dependencies": ["1"], "complexity": "High"},
                    {"id": "3", "title": "Implement solution", "description": "Implement the designed solution", "dependencies": ["2"], "complexity": "High"},
                    {"id": "4", "title": "Test solution", "description": "Test the implemented solution", "dependencies": ["3"], "complexity": "Medium"},
                    {"id": "5", "title": "Deploy solution", "description": "Deploy the solution to production", "dependencies": ["4"], "complexity": "Medium"}
                ]
            
            return {
                "goal": goal,
                "subtasks": tasks
            }
            
        except Exception as e:
            logger.error(f"Error in traditional planning: {str(e)}")
            # Return a basic plan as fallback
            return {
                "goal": goal,
                "subtasks": [
                    {"id": "1", "title": "Analyze requirements", "description": "Analyze and clarify the project requirements", "dependencies": [], "complexity": "Medium"},
                    {"id": "2", "title": "Design architecture", "description": "Design the system architecture", "dependencies": ["1"], "complexity": "High"},
                    {"id": "3", "title": "Implement solution", "description": "Implement the designed solution", "dependencies": ["2"], "complexity": "High"},
                    {"id": "4", "title": "Test solution", "description": "Test the implemented solution", "dependencies": ["3"], "complexity": "Medium"},
                    {"id": "5", "title": "Deploy solution", "description": "Deploy the solution to production", "dependencies": ["4"], "complexity": "Medium"}
                ]
            }
    
    async def _execute_plan(self, goal_id: str, plan: Dict[str, Any]):
        """
        Execute a plan by dispatching subtasks to appropriate agents.
        
        Args:
            goal_id: The ID of the goal being executed
            plan: The plan to execute
        """
        logger.info(f"Executing plan for goal {goal_id}")
        
        # Get subtasks from the plan
        subtasks = plan.get("subtasks", [])
        
        if not subtasks:
            logger.warning(f"No subtasks found in plan for goal {goal_id}")
            if self.update_task_state_fn:
                await self.update_task_state_fn(goal_id, {
                    "logs": ["No subtasks found in plan, nothing to execute"]
                })
            return
        
        # Create a dependency graph to determine execution order
        dependency_graph = self._create_dependency_graph(subtasks)
        execution_order = self._topological_sort(dependency_graph)
        
        if self.update_task_state_fn:
            await self.update_task_state_fn(goal_id, {
                "logs": [f"Created execution order for {len(subtasks)} subtasks"]
            })
        
        # Execute subtasks in order
        completed_subtasks = set()
        for task_id in execution_order:
            subtask = next((t for t in subtasks if t["id"] == task_id), None)
            if not subtask:
                continue
            
            # Log start of subtask
            if self.update_task_state_fn:
                await self.update_task_state_fn(goal_id, {
                    "logs": [f"Starting subtask: {subtask['title']}"]
                })
            
            try:
                # Select appropriate tools for this task
                tools = await self.select_tools_for_task(subtask)
                
                # Execute the subtask (placeholder)
                # In a real implementation, this would dispatch to the relevant agent
                # For now, just simulate execution with a delay
                await asyncio.sleep(0.5)  # Simulate execution time
                
                # Mark task as completed
                completed_subtasks.add(task_id)
                
                if self.update_task_state_fn:
                    await self.update_task_state_fn(goal_id, {
                        "logs": [f"Completed subtask: {subtask['title']}"],
                        "completed_subtasks": list(completed_subtasks)
                    })
            except Exception as e:
                logger.error(f"Error executing subtask {task_id}: {e}")
                if self.update_task_state_fn:
                    await self.update_task_state_fn(goal_id, {
                        "logs": [f"Error in subtask {task_id}: {str(e)}"]
                    })
                # Continue with next task despite errors
        
        logger.info(f"Plan execution completed for goal {goal_id}")
    
    def _create_dependency_graph(self, subtasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Create a dependency graph from subtasks.
        
        Args:
            subtasks: List of subtask dictionaries
            
        Returns:
            Dictionary mapping task ID to list of dependent tasks
        """
        # Create a graph where each key is a task ID and the value is a list of tasks that depend on it
        graph = {task["id"]: [] for task in subtasks}
        
        # Add dependencies
        for task in subtasks:
            for dep_id in task.get("dependencies", []):
                if dep_id in graph:
                    graph[dep_id].append(task["id"])
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Perform topological sort on a dependency graph.
        
        Args:
            graph: Dependency graph
            
        Returns:
            List of task IDs in order of execution
        """
        # Find all tasks with no dependencies
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for dependent in graph[node]:
                in_degree[dependent] = in_degree.get(dependent, 0) + 1
        
        # Start with nodes that have no dependencies
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree of dependent nodes
            for dependent in graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for cycles
        if len(result) != len(graph):
            logger.warning("Dependency cycle detected in plan")
        
        return result
    
    async def select_tools_for_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Select appropriate tools for a given task using AZR's tool-augmented reasoning.
        """
        if not self.azr:
            # Fallback to predetermined tool selection
            return self._default_tool_selection(task)
        
        try:
            # Define available tools
            available_tools = [
                {"name": "CodeExecutor", "description": "Executes code in a sandbox environment"},
                {"name": "CloudDeployer", "description": "Deploys solutions to cloud services"},
                {"name": "DatabaseManager", "description": "Interacts with databases"},
                {"name": "APITester", "description": "Tests APIs and endpoints"},
                {"name": "DocumentationGenerator", "description": "Generates documentation"}
            ]
            
            # Use AZR to select tools
            tool_selection = await self.azr.select_tool(task["description"], available_tools)
            
            # Extract the selected tool
            selected_tool = tool_selection.get("selected_tool")
            
            if selected_tool:
                return [selected_tool]
            else:
                return self._default_tool_selection(task)
                
        except Exception as e:
            logger.error(f"Error selecting tools with AZR: {e}")
            return self._default_tool_selection(task)
    
    def _default_tool_selection(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback method for tool selection."""
        # Simple keyword-based tool selection as a fallback
        description = task.get("description", "").lower()
        title = task.get("title", "").lower()
        
        if any(word in description or word in title for word in ["code", "implement", "develop", "programming"]):
            return [{"name": "CodeExecutor", "description": "Executes code in a sandbox environment"}]
        elif any(word in description or word in title for word in ["deploy", "cloud", "infrastructure", "aws", "azure", "gcp"]):
            return [{"name": "CloudDeployer", "description": "Deploys solutions to cloud services"}]
        elif any(word in description or word in title for word in ["database", "data", "storage", "sql", "nosql"]):
            return [{"name": "DatabaseManager", "description": "Interacts with databases"}]
        elif any(word in description or word in title for word in ["test", "api", "endpoint", "request"]):
            return [{"name": "APITester", "description": "Tests APIs and endpoints"}]
        elif any(word in description or word in title for word in ["document", "documentation", "readme", "manual"]):
            return [{"name": "DocumentationGenerator", "description": "Generates documentation"}]
        else:
            # Default to code executor as a fallback
            return [{"name": "CodeExecutor", "description": "Executes code in a sandbox environment"}]
    
    async def get_orchestration_status(self, goal_id: str) -> Dict[str, Any]:
        """Get the current status of an orchestration process."""
        if goal_id not in self.active_orchestrations:
            return {"status": "not_found", "goal_id": goal_id}
        
        return self.active_orchestrations[goal_id]
