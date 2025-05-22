"""
Absolute Zero Reasoner (AZR) - Core Implementation
Provides zero-shot planning and decomposition capabilities to the Autonomous AI Architect
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio

from ..core_orchestration.llm_router import LLMRouter

logger = logging.getLogger("azr")

# Reflection keywords to detect when the system is engaging in self-correction
REFLECTION_KEYWORDS = [
    "wait", "recheck", "retry", "rethink", "re-verify", "re-evaluate", 
    "check again", "try again", "think again", "verify again",
    "evaluate again", "let's correct", "however", "alternatively",
    "reconsider", "review", "revisit", "double-check", "cross-check", 
    "second look", "reassess", "inspect", "examine again", "re-examine", 
    "revise", "adjust", "modify", "recalibrate", "pause", "reflect", 
    "clarify", "confirm", "validate again", "on second thought", 
    "in retrospect", "upon reflection", "alternately", "perhaps", 
    "maybe", "on the other hand"
]

class AbsoluteZeroReasoner:
    """
    Absolute Zero Reasoner can take a high-level user request and break it into executable subtasks 
    without prior examples through first-principles reasoning.
    """
    
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
        
    async def decompose_task(self, goal: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Decompose a high-level goal into executable subtasks using zero-shot planning.
        
        Args:
            goal: The high-level user goal to decompose
            context: Optional additional context or constraints
            
        Returns:
            Dict containing the plan with subtasks
        """
        decomposition_prompt = self._create_decomposition_prompt(goal, context)
        
        # Use ReAct prompting to get better reasoning
        response = await self.llm_router.generate(
            messages=[
                {"role": "system", "content": "You are the Absolute Zero Reasoner, an advanced AI system that decomposes complex tasks into executable subtasks through first-principles reasoning."},
                {"role": "user", "content": decomposition_prompt}
            ],
            model="gpt-4-turbo", # Use a capable model for reasoning
            temperature=0.2,      # Keep temperature low for logical planning
            max_tokens=2000,
        )
        
        # Extract the plan from the response
        plan = self._extract_plan(response)
        return plan
    
    async def select_tool(self, task: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine the right tool to use based on a task description.
        
        Args:
            task: Description of the task to be performed
            available_tools: List of tool descriptions and capabilities
            
        Returns:
            Dict containing the selected tool and reasoning
        """
        tools_context = "\n".join([f"Tool {i+1}: {tool['name']} - {tool['description']}" 
                                  for i, tool in enumerate(available_tools)])
        
        tool_selection_prompt = f"""
        # Task
        {task}
        
        # Available Tools
        {tools_context}
        
        Think step by step about which tool would be most appropriate for this task.
        For each tool, analyze:
        1. Whether it has the capabilities required for the task
        2. How efficiently it can complete the task
        3. Any limitations or constraints that might make it unsuitable
        
        After your analysis, select the most appropriate tool and explain your reasoning.
        Format your response as:
        
        Reasoning: [Your step-by-step reasoning process]
        Selected Tool: [Name of the selected tool]
        """
        
        response = await self.llm_router.generate(
            messages=[
                {"role": "system", "content": "You are a tool-augmented reasoning system that selects the optimal tool for a given task."},
                {"role": "user", "content": tool_selection_prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.1,
            max_tokens=1000,
        )
        
        # Extract the selected tool
        return self._extract_tool_selection(response, available_tools)
    
    async def chain_of_thought_reasoning(self, problem: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate structured, logical reasoning chains for complex problems.
        
        Args:
            problem: The problem to reason about
            context: Optional additional context
            
        Returns:
            Dict containing reasoning steps and conclusion
        """
        cot_prompt = f"""
        # Problem
        {problem}
        
        {f"# Context\n{context}" if context else ""}
        
        Solve this problem by thinking step by step. Break down your reasoning process clearly.
        For each step:
        1. Identify what you know
        2. Determine what you need to know next
        3. Apply logical reasoning to move forward
        
        Format your response as:
        Step 1: [First reasoning step]
        Step 2: [Second reasoning step]
        ...
        Conclusion: [Final answer]
        """
        
        response = await self.llm_router.generate(
            messages=[
                {"role": "system", "content": "You are a logical reasoning system that solves problems through clear, step-by-step thinking."},
                {"role": "user", "content": cot_prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.2,
            max_tokens=1500,
        )
        
        # Extract the reasoning steps
        return self._extract_reasoning_chain(response)
    
    async def orchestrate_agents(self, 
                               goal: str, 
                               agents: List[Dict[str, Any]], 
                               context: Optional[str] = None) -> Dict[str, Any]:
        """
        Act as a master reasoner to coordinate multiple specialized agents.
        
        Args:
            goal: The overall goal to achieve
            agents: List of available agents with their capabilities
            context: Optional additional context
            
        Returns:
            Dict containing the orchestration plan with agent assignments
        """
        agents_context = "\n".join([f"Agent {i+1}: {agent['name']} - {agent['expertise']}" 
                                  for i, agent in enumerate(agents)])
        
        orchestration_prompt = f"""
        # Goal
        {goal}
        
        {f"# Context\n{context}" if context else ""}
        
        # Available Agents
        {agents_context}
        
        You are the orchestration system responsible for coordinating these specialized agents to achieve the goal.
        Think step by step about:
        1. How to break down the goal into subtasks
        2. Which agent is best suited for each subtask
        3. The optimal sequence of operations
        4. How information should flow between agents
        
        Create a detailed orchestration plan that assigns tasks to specific agents and establishes the workflow.
        Format your response as:
        
        ## Task Breakdown
        [List of subtasks]
        
        ## Agent Assignments
        [Mapping of subtasks to agents]
        
        ## Workflow Sequence
        [Step-by-step execution plan]
        
        ## Communication Plan
        [How agents will share information]
        """
        
        response = await self.llm_router.generate(
            messages=[
                {"role": "system", "content": "You are a multi-agent orchestration system that optimally coordinates specialized agents."},
                {"role": "user", "content": orchestration_prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.2,
            max_tokens=2000,
        )
        
        # Extract the orchestration plan
        return self._extract_orchestration_plan(response, agents)
        
    def _create_decomposition_prompt(self, goal: str, context: Optional[str] = None) -> str:
        """Create the prompt for task decomposition using ReAct format."""
        return f"""
        # Goal
        {goal}
        
        {f"# Context\n{context}" if context else ""}
        
        Break down this goal into executable subtasks through first-principles reasoning.
        For each subtask:
        1. Provide a clear description
        2. List any dependencies on other subtasks
        3. Specify the expected output
        4. Estimate the complexity (Low, Medium, High)
        
        Follow this format:
        
        Thought: [Analyze the goal and think about how to break it down logically]
        
        Action: Decompose the goal into subtasks
        
        Action Input: {goal}
        
        Observation: [The subtasks that result from your decomposition]
        
        Thought: [Analyze whether the subtasks cover the entire goal and are properly sequenced]
        
        Action: Finalize the plan
        
        Action Input: [The complete plan with all subtasks]
        
        Observation: [The finalized plan]
        
        # Final Plan
        [Structured representation of all subtasks with their descriptions, dependencies, outputs, and complexity]
        """
    
    def _extract_plan(self, response: str) -> Dict[str, Any]:
        """Extract structured plan from the LLM response."""
        try:
            # Extract the "Final Plan" section
            if "# Final Plan" in response:
                final_plan = response.split("# Final Plan")[-1].strip()
            else:
                final_plan = response
                
            # Parse the plan into a structured format
            subtasks = []
            current_subtask = {}
            
            for line in final_plan.split("\n"):
                line = line.strip()
                if line.startswith("Subtask"):
                    if current_subtask and "description" in current_subtask:
                        subtasks.append(current_subtask)
                    current_subtask = {"id": line.split(":")[0].strip()}
                elif line.startswith("Description:"):
                    current_subtask["description"] = line.replace("Description:", "").strip()
                elif line.startswith("Dependencies:"):
                    current_subtask["dependencies"] = [dep.strip() for dep in line.replace("Dependencies:", "").split(",") if dep.strip()]
                elif line.startswith("Expected Output:"):
                    current_subtask["expected_output"] = line.replace("Expected Output:", "").strip()
                elif line.startswith("Complexity:"):
                    current_subtask["complexity"] = line.replace("Complexity:", "").strip()
            
            # Don't forget the last subtask
            if current_subtask and "description" in current_subtask:
                subtasks.append(current_subtask)
                
            return {
                "goal": response.split("# Goal")[1].split("\n")[0].strip() if "# Goal" in response else "",
                "subtasks": subtasks
            }
        except Exception as e:
            logger.error(f"Error extracting plan: {e}")
            return {"subtasks": [], "error": str(e), "raw_response": response}
    
    def _extract_tool_selection(self, response: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract selected tool and reasoning from response."""
        try:
            reasoning = ""
            selected_tool = None
            
            if "Reasoning:" in response:
                reasoning_part = response.split("Reasoning:")[1].split("Selected Tool:")[0].strip()
                reasoning = reasoning_part
                
            if "Selected Tool:" in response:
                tool_name = response.split("Selected Tool:")[1].strip().split("\n")[0].strip()
                # Find the tool in available_tools
                for tool in available_tools:
                    if tool["name"].lower() == tool_name.lower():
                        selected_tool = tool
                        break
            
            return {
                "reasoning": reasoning,
                "selected_tool": selected_tool if selected_tool else {"name": "None", "description": "No suitable tool found"},
                "raw_response": response
            }
        except Exception as e:
            logger.error(f"Error extracting tool selection: {e}")
            return {"reasoning": "", "selected_tool": None, "error": str(e), "raw_response": response}
    
    def _extract_reasoning_chain(self, response: str) -> Dict[str, Any]:
        """Extract structured reasoning chain from the LLM response."""
        try:
            steps = []
            conclusion = ""
            
            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("Step "):
                    step_number = line.split(":")[0].replace("Step ", "").strip()
                    step_content = line.split(":", 1)[1].strip() if ":" in line else ""
                    steps.append({"number": step_number, "content": step_content})
                elif line.startswith("Conclusion:"):
                    conclusion = line.replace("Conclusion:", "").strip()
            
            return {
                "steps": steps,
                "conclusion": conclusion,
                "raw_response": response
            }
        except Exception as e:
            logger.error(f"Error extracting reasoning chain: {e}")
            return {"steps": [], "conclusion": "", "error": str(e), "raw_response": response}
    
    def _extract_orchestration_plan(self, response: str, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structured orchestration plan from the LLM response."""
        try:
            task_breakdown = []
            agent_assignments = {}
            workflow_sequence = []
            communication_plan = ""
            
            if "## Task Breakdown" in response:
                task_section = response.split("## Task Breakdown")[1].split("##")[0].strip()
                task_breakdown = [task.strip() for task in task_section.split("\n") if task.strip()]
                
            if "## Agent Assignments" in response:
                assignment_section = response.split("## Agent Assignments")[1].split("##")[0].strip()
                for line in assignment_section.split("\n"):
                    if ":" in line:
                        task, agent = line.split(":", 1)
                        agent_assignments[task.strip()] = agent.strip()
                        
            if "## Workflow Sequence" in response:
                workflow_section = response.split("## Workflow Sequence")[1].split("##")[0].strip()
                workflow_sequence = [step.strip() for step in workflow_section.split("\n") if step.strip()]
                
            if "## Communication Plan" in response:
                communication_section = response.split("## Communication Plan")[1].strip()
                communication_plan = communication_section
            
            return {
                "task_breakdown": task_breakdown,
                "agent_assignments": agent_assignments,
                "workflow_sequence": workflow_sequence,
                "communication_plan": communication_plan,
                "raw_response": response
            }
        except Exception as e:
            logger.error(f"Error extracting orchestration plan: {e}")
            return {
                "task_breakdown": [], 
                "agent_assignments": {}, 
                "workflow_sequence": [], 
                "communication_plan": "",
                "error": str(e), 
                "raw_response": response
            }
