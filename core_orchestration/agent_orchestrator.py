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

# Import AZR and FFL here
from azr.core import AbsoluteZeroReasoner
from ffl.core import FractalFeedbackLoop

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
        azr: Optional[AbsoluteZeroReasoner] = None,  # Make AZR optional for backward compatibility
        ffl: Optional[FractalFeedbackLoop] = None,   # Make FFL optional for backward compatibility
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
        
        # Set up CrewAI agents later
        
    async def start_orchestration(self, goal_id: str, goal: str, client_analysis: Optional[str] = None):
        """
        Start the orchestration process for achieving a specific goal.
        Now enhanced with AZR for zero-shot planning and decomposition.
        """
        logger.info(f"Starting orchestration for goal {goal_id}: {goal}")
        
        start_time = time.time()
        
        # Use Absolute Zero Reasoner to create a plan if available
        if self.azr:
            try:
                # Create zero-shot plan using AZR
                plan = await self.azr.decompose_task(goal, client_analysis)
                
                # Update task state with plan
                update_task_fn = self.config.get("update_task_state_fn", None)
                if update_task_fn:
                    await update_task_fn(goal_id, {
                        "status": "planning_completed",
                        "plan": plan,
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
                plan = await self._traditional_planning(goal, client_analysis)
        else:
            # Traditional planning without AZR
            plan = await self._traditional_planning(goal, client_analysis)
        
        # Execute the plan here
        # This would involve dispatching to specific agents based on the plan
        
        # Track orchestration
        self.active_orchestrations[goal_id] = {
            "goal": goal,
            "start_time": start_time,
            "plan": plan,
            "status": "in_progress"
        }
        
        # Placeholder for actual implementation
        # This should dispatch tasks to agents based on the plan
        
        # Mark as complete when done
        execution_time = time.time() - start_time
        self.active_orchestrations[goal_id]["status"] = "completed"
        self.active_orchestrations[goal_id]["execution_time"] = execution_time
        
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
        # Placeholder for traditional planning logic
        # This would use a predefined planning agent or system
        
        # Simulate planning result
        return {
            "goal": goal,
            "subtasks": [
                {"id": "1", "description": "Analyze requirements", "dependencies": []},
                {"id": "2", "description": "Design architecture", "dependencies": ["1"]},
                {"id": "3", "description": "Implement solution", "dependencies": ["2"]},
                {"id": "4", "description": "Test solution", "dependencies": ["3"]},
                {"id": "5", "description": "Deploy solution", "dependencies": ["4"]}
            ]
        }
    
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
        if "code" in task["description"].lower() or "implement" in task["description"].lower():
            return [{"name": "CodeExecutor", "description": "Executes code in a sandbox environment"}]
        elif "deploy" in task["description"].lower() or "cloud" in task["description"].lower():
            return [{"name": "CloudDeployer", "description": "Deploys solutions to cloud services"}]
        elif "database" in task["description"].lower() or "data" in task["description"].lower():
            return [{"name": "DatabaseManager", "description": "Interacts with databases"}]
        elif "test" in task["description"].lower() or "api" in task["description"].lower():
            return [{"name": "APITester", "description": "Tests APIs and endpoints"}]
        elif "document" in task["description"].lower():
            return [{"name": "DocumentationGenerator", "description": "Generates documentation"}]
        else:
            # Default to code executor as a fallback
            return [{"name": "CodeExecutor", "description": "Executes code in a sandbox environment"}]
    
    async def get_orchestration_status(self, goal_id: str) -> Dict[str, Any]:
        """Get the current status of an orchestration process."""
        if goal_id not in self.active_orchestrations:
            return {"status": "not_found", "goal_id": goal_id}
        
        return self.active_orchestrations[goal_id]
