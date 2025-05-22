"""
Fractal Feedback Loop (FFL) for AI Improvement
Implements a self-improving AI system that continuously analyzes its own performance
and applies optimizations at multiple levels of abstraction.
"""

import logging
import time
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
import numpy as np
from collections import defaultdict

from ..core_orchestration.llm_router import LLMRouter
from ..core_orchestration.monitoring_system import MonitoringSystem

logger = logging.getLogger("ffl")

class FractalFeedbackLoop:
    """
    Implements a Fractal Feedback Loop system that continuously monitors, analyzes,
    and improves AI system performance across multiple levels of abstraction.
    """
    
    def __init__(
        self, 
        llm_router: LLMRouter,
        monitoring_system: MonitoringSystem,
        feedback_interval: int = 3600,  # 1 hour default
        initial_feedback_delay: int = 86400,  # 24 hours default
        min_samples_required: int = 10,
        config: Optional[Dict[str, Any]] = None
    ):
        self.llm_router = llm_router
        self.monitoring_system = monitoring_system
        self.feedback_interval = feedback_interval
        self.initial_feedback_delay = initial_feedback_delay
        self.min_samples_required = min_samples_required
        self.config = config or {}
        
        # Performance metrics storage
        self.performance_metrics = {
            "response_quality": defaultdict(list),
            "response_time": defaultdict(list),
            "success_rate": defaultdict(list),
            "reflection_rate": defaultdict(list),
            "user_feedback": defaultdict(list),
        }
        
        # Improvement records
        self.improvement_history = []
        
        # Dictionary of improvement functions that can be called
        self.improvement_functions = {
            "prompt_optimization": self._optimize_prompts,
            "agent_coordination": self._optimize_agent_coordination,
            "error_handling": self._optimize_error_handling,
            "tool_usage": self._optimize_tool_usage,
        }
        
        # Initialize the feedback loop timestamp
        self.last_feedback_time = time.time()
        self.system_start_time = time.time()
        
        # Running flag
        self.running = False
        self.feedback_task = None
    
    async def start(self):
        """Start the feedback loop."""
        if self.running:
            return
            
        self.running = True
        self.feedback_task = asyncio.create_task(self._feedback_loop())
        logger.info("Fractal Feedback Loop started")
        
    async def stop(self):
        """Stop the feedback loop."""
        if not self.running:
            return
            
        self.running = False
        if self.feedback_task:
            self.feedback_task.cancel()
            try:
                await self.feedback_task
            except asyncio.CancelledError:
                pass
        logger.info("Fractal Feedback Loop stopped")
    
    async def _feedback_loop(self):
        """Main feedback loop that runs periodically."""
        # Wait for initial delay before starting
        initial_delay = max(0, self.initial_feedback_delay - (time.time() - self.system_start_time))
        if initial_delay > 0:
            logger.info(f"Waiting {initial_delay} seconds before starting feedback loop")
            await asyncio.sleep(initial_delay)
        
        while self.running:
            try:
                # Check if we have enough data
                if self._has_sufficient_data():
                    logger.info("Running feedback loop analysis")
                    await self._perform_analysis_cycle()
                else:
                    logger.info("Insufficient data for feedback loop analysis")
                
                # Wait for next feedback interval
                await asyncio.sleep(self.feedback_interval)
            except Exception as e:
                logger.error(f"Error in feedback loop: {e}")
                await asyncio.sleep(self.feedback_interval)
    
    def _has_sufficient_data(self) -> bool:
        """Check if we have enough data to perform meaningful analysis."""
        # Need at least min_samples_required samples in at least one category
        for metric_category, values_by_component in self.performance_metrics.items():
            for component, values in values_by_component.items():
                if len(values) >= self.min_samples_required:
                    return True
        return False
    
    async def record_metric(self, 
                          category: str, 
                          component: str, 
                          value: Union[float, int, str, bool],
                          metadata: Optional[Dict[str, Any]] = None):
        """
        Record a performance metric.
        
        Args:
            category: The metric category (e.g., "response_quality")
            component: The system component being measured
            value: The metric value
            metadata: Optional additional context about this measurement
        """
        if category not in self.performance_metrics:
            self.performance_metrics[category] = defaultdict(list)
        
        # Store the metric with timestamp and metadata
        self.performance_metrics[category][component].append({
            "value": value,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })
        
        # Also record in monitoring system for visualization
        self.monitoring_system.record_metric(
            metric_name=f"ffl_{category}_{component}",
            value=float(value) if isinstance(value, (int, float)) else 1.0,
            labels={"source": "fractal_feedback_loop"}
        )
    
    async def _perform_analysis_cycle(self):
        """
        Perform a complete analysis cycle:
        1. Analyze performance metrics
        2. Identify improvement opportunities
        3. Generate improvement plans
        4. Apply improvements
        5. Record the improvement cycle
        """
        # Analyze current performance
        performance_analysis = await self._analyze_performance()
        
        # Identify areas for improvement
        improvement_opportunities = await self._identify_improvement_opportunities(performance_analysis)
        
        # If no opportunities found, just log and return
        if not improvement_opportunities:
            logger.info("No improvement opportunities identified")
            return
        
        # Generate improvement plans for each opportunity
        improvement_plans = []
        for opportunity in improvement_opportunities:
            plan = await self._generate_improvement_plan(opportunity)
            if plan:
                improvement_plans.append(plan)
        
        # Apply the improvements
        applied_improvements = []
        for plan in improvement_plans:
            success = await self._apply_improvement(plan)
            if success:
                applied_improvements.append(plan)
        
        # Record the improvement cycle
        cycle_record = {
            "timestamp": time.time(),
            "performance_analysis": performance_analysis,
            "improvement_opportunities": improvement_opportunities,
            "improvement_plans": improvement_plans,
            "applied_improvements": applied_improvements
        }
        
        self.improvement_history.append(cycle_record)
        logger.info(f"Completed feedback cycle with {len(applied_improvements)} improvements applied")
        
        # Reset performance metrics older than the feedback interval to prevent re-analyzing old data
        self._prune_old_metrics()
    
    async def _analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze current performance metrics to identify patterns and issues.
        Returns a structured analysis of system performance.
        """
        analysis = {}
        
        for category, values_by_component in self.performance_metrics.items():
            category_analysis = {}
            
            for component, metrics in values_by_component.items():
                # Skip if we don't have enough data points
                if len(metrics) < self.min_samples_required:
                    continue
                    
                # Extract values for numerical analysis
                values = [m["value"] for m in metrics if isinstance(m["value"], (int, float))]
                
                # Skip if we can't do numerical analysis
                if not values:
                    continue
                    
                # Calculate statistics
                component_analysis = {
                    "mean": np.mean(values),
                    "median": np.median(values),
                    "std_dev": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "sample_count": len(values),
                    "trend": self._calculate_trend(values)
                }
                
                category_analysis[component] = component_analysis
            
            analysis[category] = category_analysis
        
        return analysis
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate the trend direction of a series of values."""
        if len(values) < 2:
            return "stable"
            
        # Simple linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        slope = (np.mean(x * y) - np.mean(x) * np.mean(y)) / (np.mean(x * x) - np.mean(x) ** 2)
        
        if slope > 0.05:  # Threshold for positive trend
            return "improving"
        elif slope < -0.05:  # Threshold for negative trend
            return "declining"
        else:
            return "stable"
    
    async def _identify_improvement_opportunities(self, performance_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify specific opportunities for improvement based on performance analysis.
        Returns a list of improvement opportunities.
        """
        opportunities = []
        
        # Check for declining performance
        for category, components in performance_analysis.items():
            for component, analysis in components.items():
                # Look for declining trends
                if analysis.get("trend") == "declining":
                    opportunities.append({
                        "category": category,
                        "component": component,
                        "issue": "declining_performance",
                        "severity": "high",
                        "details": f"Performance is declining with mean {analysis['mean']:.2f} and trend {analysis['trend']}"
                    })
                
                # Look for high variation
                if analysis.get("std_dev", 0) > 0.2 * analysis.get("mean", 1):  # High relative standard deviation
                    opportunities.append({
                        "category": category,
                        "component": component,
                        "issue": "high_variability",
                        "severity": "medium",
                        "details": f"High performance variability with std_dev {analysis['std_dev']:.2f} relative to mean {analysis['mean']:.2f}"
                    })
                    
                # Look for low absolute performance
                if category == "response_quality" and analysis.get("mean", 0) < 0.7:  # Threshold for good quality
                    opportunities.append({
                        "category": category,
                        "component": component,
                        "issue": "low_quality",
                        "severity": "high",
                        "details": f"Low response quality with mean {analysis['mean']:.2f}"
                    })
                
                if category == "success_rate" and analysis.get("mean", 0) < 0.8:  # Threshold for good success rate
                    opportunities.append({
                        "category": category,
                        "component": component,
                        "issue": "low_success_rate",
                        "severity": "high",
                        "details": f"Low success rate with mean {analysis['mean']:.2f}"
                    })
        
        return opportunities
    
    async def _generate_improvement_plan(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a specific improvement plan for a given opportunity.
        Uses LLM-based reasoning to create actionable improvement steps.
        """
        # Map the opportunity to an improvement type
        improvement_type = self._map_opportunity_to_improvement_type(opportunity)
        
        if not improvement_type:
            logger.warning(f"No suitable improvement type for opportunity: {opportunity}")
            return None
        
        # Create the prompt for the LLM
        improvement_prompt = f"""
        # Performance Issue Analysis
        Category: {opportunity['category']}
        Component: {opportunity['component']}
        Issue: {opportunity['issue']}
        Severity: {opportunity['severity']}
        Details: {opportunity['details']}
        
        Based on this performance issue, create a detailed improvement plan that addresses:
        1. Root causes - What might be causing this issue?
        2. Improvement approach - What specific changes could address these causes?
        3. Implementation steps - What concrete actions should be taken?
        4. Success metrics - How should we measure if the improvement is working?
        
        Your improvement plan should be specific, measurable, achievable, relevant, and time-bound.
        """
        
        # Generate the improvement plan
        response = await self.llm_router.generate(
            messages=[
                {"role": "system", "content": "You are an AI system optimization expert. Your goal is to analyze performance issues and create specific, actionable improvement plans."},
                {"role": "user", "content": improvement_prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.3,
            max_tokens=1000,
        )
        
        # Extract the structured plan
        improvement_plan = {
            "opportunity": opportunity,
            "improvement_type": improvement_type,
            "plan": response,
            "raw_response": response
        }
        
        return improvement_plan
    
    def _map_opportunity_to_improvement_type(self, opportunity: Dict[str, Any]) -> Optional[str]:
        """Map an improvement opportunity to a specific improvement type."""
        category = opportunity.get("category", "")
        issue = opportunity.get("issue", "")
        component = opportunity.get("component", "")
        
        # Mapping logic
        if category == "response_quality" and issue in ["declining_performance", "low_quality"]:
            return "prompt_optimization"
        elif category == "success_rate" and issue in ["declining_performance", "low_success_rate"]:
            return "error_handling"
        elif category == "response_time" and issue == "high_variability":
            return "agent_coordination"
        elif "tool" in component.lower():
            return "tool_usage"
        
        # Default fallback
        return None
    
    async def _apply_improvement(self, plan: Dict[str, Any]) -> bool:
        """
        Apply an improvement plan to the system.
        Returns True if improvement was applied successfully.
        """
        improvement_type = plan.get("improvement_type")
        
        # Check if we have an implementation for this improvement type
        if improvement_type not in self.improvement_functions:
            logger.warning(f"No implementation for improvement type: {improvement_type}")
            return False
        
        try:
            # Call the appropriate improvement function
            improvement_function = self.improvement_functions[improvement_type]
            success = await improvement_function(plan)
            
            if success:
                logger.info(f"Successfully applied {improvement_type} improvement")
                
                # Record the applied improvement
                self.monitoring_system.record_event(
                    event_type="system_improvement",
                    event_data={
                        "improvement_type": improvement_type,
                        "success": True,
                        "details": plan.get("opportunity", {}).get("details", "")
                    }
                )
            else:
                logger.warning(f"Failed to apply {improvement_type} improvement")
            
            return success
        except Exception as e:
            logger.error(f"Error applying improvement plan: {e}")
            return False
    
    async def _optimize_prompts(self, plan: Dict[str, Any]) -> bool:
        """
        Optimize system prompts based on the improvement plan.
        This is a placeholder for actual prompt optimization logic.
        """
        # In a real implementation, this would update prompt templates
        # stored in a database or configuration system
        
        logger.info(f"Optimizing prompts based on plan: {plan['opportunity']['component']}")
        
        # Simulate successful optimization
        return True
    
    async def _optimize_agent_coordination(self, plan: Dict[str, Any]) -> bool:
        """
        Optimize agent coordination based on the improvement plan.
        This is a placeholder for actual agent coordination optimization.
        """
        logger.info(f"Optimizing agent coordination based on plan: {plan['opportunity']['component']}")
        
        # Simulate successful optimization
        return True
    
    async def _optimize_error_handling(self, plan: Dict[str, Any]) -> bool:
        """
        Optimize error handling based on the improvement plan.
        This is a placeholder for actual error handling optimization.
        """
        logger.info(f"Optimizing error handling based on plan: {plan['opportunity']['component']}")
        
        # Simulate successful optimization
        return True
    
    async def _optimize_tool_usage(self, plan: Dict[str, Any]) -> bool:
        """
        Optimize tool usage based on the improvement plan.
        This is a placeholder for actual tool usage optimization.
        """
        logger.info(f"Optimizing tool usage based on plan: {plan['opportunity']['component']}")
        
        # Simulate successful optimization
        return True
    
    def _prune_old_metrics(self):
        """Remove metrics older than the feedback interval to prevent re-analyzing old data."""
        cutoff_time = time.time() - self.feedback_interval
        
        for category in self.performance_metrics.keys():
            for component in list(self.performance_metrics[category].keys()):
                self.performance_metrics[category][component] = [
                    metric for metric in self.performance_metrics[category][component]
                    if metric["timestamp"] >= cutoff_time
                ]
