#!/usr/bin/env python3
"""
Agent Orchestrator for coordinating multiple AI agents
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Agent:
    """Agent data structure"""
    id: str
    name: str
    type: str
    status: str
    task: Optional[str] = None
    progress: float = 0.0
    created_at: str = ""
    updated_at: str = ""

class AgentOrchestrator:
    """Orchestrates multiple AI agents for goal processing"""
    
    def __init__(self, config_loader=None, llm_router=None):
        self.config_loader = config_loader
        self.llm_router = llm_router
        self.active_agents: Dict[str, Agent] = {}
        self.max_concurrent_agents = 5
        
        logger.info("AgentOrchestrator initialized")
    
    async def reload_config(self):
        """Reload configuration from config loader"""
        try:
            if self.config_loader:
                config = await self.config_loader.get_config()
                self.max_concurrent_agents = config.get('max_concurrent_agents', 5)
                logger.info(f"Configuration reloaded: max_concurrent_agents={self.max_concurrent_agents}")
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
    
    async def process_goal(self, goal_text: str, goal_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a goal using coordinated agents"""
        try:
            logger.info(f"Starting goal processing: {goal_id}")
            
            # Initial status update
            yield {
                "type": "goal_update",
                "goal_id": goal_id,
                "status": "analyzing"
            }
            
            # Create planning agent
            planner_agent = Agent(
                id=str(uuid.uuid4()),
                name="Planner Agent",
                type="planner",
                status="active",
                task=f"Analyzing goal: {goal_text}",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            self.active_agents[planner_agent.id] = planner_agent
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": planner_agent.id,
                        "name": planner_agent.name,
                        "type": planner_agent.type,
                        "status": planner_agent.status,
                        "task": planner_agent.task,
                        "progress": planner_agent.progress,
                        "created_at": planner_agent.created_at,
                        "updated_at": planner_agent.updated_at
                    }
                }
            }
            
            # Simulate planning phase
            await asyncio.sleep(1)
            planner_agent.progress = 0.5
            planner_agent.updated_at = datetime.utcnow().isoformat()
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": planner_agent.id,
                        "name": planner_agent.name,
                        "type": planner_agent.type,
                        "status": planner_agent.status,
                        "task": planner_agent.task,
                        "progress": planner_agent.progress,
                        "created_at": planner_agent.created_at,
                        "updated_at": planner_agent.updated_at
                    }
                }
            }
            
            # Generate output
            yield {
                "type": "output_update",
                "data": {
                    "output": {
                        "id": str(uuid.uuid4()),
                        "goalId": goal_id,
                        "type": "analysis",
                        "title": "Goal Analysis Complete",
                        "content": f"Successfully analyzed goal: {goal_text}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_id": planner_agent.id
                    }
                }
            }
            
            # Complete planning
            planner_agent.progress = 1.0
            planner_agent.status = "completed"
            planner_agent.updated_at = datetime.utcnow().isoformat()
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": {
                        "id": planner_agent.id,
                        "name": planner_agent.name,
                        "type": planner_agent.type,
                        "status": planner_agent.status,
                        "task": planner_agent.task,
                        "progress": planner_agent.progress,
                        "created_at": planner_agent.created_at,
                        "updated_at": planner_agent.updated_at
                    }
                }
            }
            
            # Final status update
            yield {
                "type": "goal_update",
                "goal_id": goal_id,
                "status": "completed"
            }
            
            logger.info(f"Goal processing completed: {goal_id}")
            
        except Exception as e:
            logger.error(f"Goal processing failed for {goal_id}: {e}")
            yield {
                "type": "goal_update",
                "goal_id": goal_id,
                "status": "error",
                "error": str(e)
            }
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of active agents"""
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type,
                "status": agent.status,
                "task": agent.task,
                "progress": agent.progress,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            }
            for agent in self.active_agents.values()
        ]
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent"""
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            agent.status = "stopped"
            agent.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Agent stopped: {agent_id}")
            return True
        return False
    
    async def cleanup_completed_agents(self):
        """Remove completed agents from active list"""
        completed_agents = [
            agent_id for agent_id, agent in self.active_agents.items()
            if agent.status in ["completed", "stopped", "error"]
        ]
        
        for agent_id in completed_agents:
            del self.active_agents[agent_id]
            logger.debug(f"Cleaned up completed agent: {agent_id}")