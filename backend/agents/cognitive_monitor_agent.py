import re
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Pattern, Tuple
from .agent_plugin import AgentPlugin

logger = logging.getLogger(__name__)

class CognitiveMonitorAgent(AgentPlugin):
    """
    Monitors for hallucination, faulty reasoning, and loss of goal/context in agent outputs and orchestration steps.
    - Optimized for performance with compiled regex patterns and efficient detection algorithms.
    - Supports runtime configuration of regex patterns.
    - Thread-safe for cache operations.
    """
    def __init__(self):
        super().__init__(
            name="CognitiveMonitorAgent",
            description="Monitors for hallucination, faulty reasoning, and loss of goal/context in agent outputs and orchestration steps."
        )
        # Default regex patterns (can be updated at runtime)
        self.hallucination_patterns: List[Tuple[Pattern, str]] = self._compile_patterns([
            (r'lorem\s+ipsum', "Lorem ipsum placeholder text"),
            (r'as\s+an\s+ai', "Self-reference as AI"),
            (r'i\s+am\s+an\s+ai', "Self-identification as AI"),
            (r'i\s+cannot\s+(?:access|browse|view|use)', "Capability disclaimer"),
            (r'(?:undefined|null|nan)\s+(?:error|exception|value)', "Programming placeholders"),
            (r'example\.com|test\.com', "Example domains")
        ])
        self.reasoning_patterns: List[Tuple[Pattern, str]] = self._compile_patterns([
            (r'(?:contradiction|paradox|impossible|cannot\s+be\s+both)', "Logical contradiction"),
            (r'logic\s+(?:error|mistake|issue|problem)', "Logic error"),
            (r'circular\s+(?:reasoning|logic|argument)', "Circular reasoning")
        ])
        # Thread-safe cache for goal keywords
        self.goal_keywords_cache: Dict[str, Set[str]] = {}
        self._cache_lock = threading.Lock()

    @staticmethod
    def _compile_patterns(patterns: List[Tuple[str, str]]) -> List[Tuple[Pattern, str]]:
        """Compile regex patterns for efficiency."""
        return [(re.compile(pat, re.IGNORECASE), desc) for pat, desc in patterns]

    def set_regex_patterns(self, hallucination_patterns: List[Tuple[str, str]], reasoning_patterns: List[Tuple[str, str]]):
        """
        Allows runtime configuration of regex patterns.
        Args:
            hallucination_patterns: List of (pattern_str, description) for hallucination detection
            reasoning_patterns: List of (pattern_str, description) for reasoning error detection
        """
        self.hallucination_patterns = self._compile_patterns(hallucination_patterns)
        self.reasoning_patterns = self._compile_patterns(reasoning_patterns)
        logger.info("CognitiveMonitorAgent regex patterns updated at runtime.")

    def health_check(self):
        """Return health status of the agent."""
        return True, "CognitiveMonitorAgent healthy."

    def _extract_goal_keywords(self, goal: str) -> Set[str]:
        """
        Extract meaningful keywords from the goal for more accurate drift detection. Thread-safe.
        Uses a simple stopword filter for English.
        """
        with self._cache_lock:
            if goal in self.goal_keywords_cache:
                return self.goal_keywords_cache[goal]
            common_words = {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'as', 'and', 'or', 'of'}
            keywords = {word.lower() for word in goal.split() if word.lower() not in common_words and len(word) > 3}
            self.goal_keywords_cache[goal] = keywords
            return keywords

    def analyze(self, subtask: Dict[str, Any], orchestration_state: Dict[str, Any], early_exit: bool = False) -> List[str]:
        """
        Analyze a subtask for cognitive issues (hallucination, faulty reasoning, goal drift).
        Args:
            subtask: The subtask to analyze
            orchestration_state: The current state of orchestration
            early_exit: If True, returns after finding the first issue
        Returns:
            List of detected issues
        """
        issues = []
        if not subtask:
            return issues
        # Hallucination Detection
        result = subtask.get("result")
        if isinstance(result, str) and result:
            for pattern, issue_type in self.hallucination_patterns:
                if pattern.search(result):
                    issues.append(f"Possible hallucination detected: {issue_type}")
                    logger.info(f"Detected hallucination: {issue_type} | Subtask: {subtask.get('id', 'unknown')}")
                    if early_exit:
                        return issues
        # Faulty Reasoning Detection
        error = subtask.get("error", "")
        description = subtask.get("description", "")
        reasoning_text = f"{error} {description}"
        if reasoning_text.strip():
            for pattern, issue_type in self.reasoning_patterns:
                if pattern.search(reasoning_text):
                    issues.append(f"Possible faulty reasoning detected: {issue_type}")
                    logger.info(f"Detected faulty reasoning: {issue_type} | Subtask: {subtask.get('id', 'unknown')}")
                    if early_exit:
                        return issues
        # Goal Drift Detection
        goal = orchestration_state.get("goal", "")
        if goal and subtask.get("title"):
            goal_keywords = self._extract_goal_keywords(goal)
            title = subtask.get("title", "")
            subtask_text = f"{title} {subtask.get('description', '')}"
            subtask_keywords = {word.lower() for word in subtask_text.split() if len(word) > 3}
            if goal_keywords and subtask_keywords and not goal_keywords.intersection(subtask_keywords):
                issues.append("Subtask may be drifting from main goal (no keyword overlap).")
                logger.info(f"Detected goal drift: {title} | Subtask: {subtask.get('id', 'unknown')}")
                if early_exit:
                    return issues
        return issues

    def analyze_batch(self, subtasks: List[Dict[str, Any]], orchestration_state: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Efficiently analyzes multiple subtasks in a batch.
        Args:
            subtasks: List of subtasks to analyze
            orchestration_state: The current state of orchestration
        Returns:
            Dictionary mapping subtask IDs to lists of issues
        """
        results = {}
        goal = orchestration_state.get("goal", "")
        if goal:
            self._extract_goal_keywords(goal)
        for subtask in subtasks:
            task_id = subtask.get("id", "unknown")
            issues = self.analyze(subtask, orchestration_state)
            if issues:
                results[task_id] = issues
        return results
