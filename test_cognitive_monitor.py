#!/usr/bin/env python3
# A test script for the CognitiveMonitorAgent

import sys
import os
import time
import threading

# Add the project root to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.agents.cognitive_monitor_agent import CognitiveMonitorAgent

def main():
    # Create an instance of the agent
    cognitive_agent = CognitiveMonitorAgent()
    print('Created CognitiveMonitorAgent instance')

    # Test 1: Default hallucination pattern detection
    print('\n--- Test 1: Default Hallucination Pattern Detection ---')
    subtask_hallucination = {'id': 'test-1', 'result': 'As an AI, I cannot access external systems.'}
    issues = cognitive_agent.analyze(subtask_hallucination, {'goal': 'Test goal'})
    print(f'Issues found: {issues}')

    # Test 2: Default reasoning error pattern detection
    print('\n--- Test 2: Default Reasoning Error Pattern Detection ---')
    subtask_reasoning = {'id': 'test-2', 'error': 'This contains a logical contradiction.', 'description': 'Testing reasoning detection'}
    issues = cognitive_agent.analyze(subtask_reasoning, {'goal': 'Test goal'})
    print(f'Issues found: {issues}')

    # Test 3: Goal drift detection
    print('\n--- Test 3: Goal Drift Detection ---')
    subtask_drift = {'id': 'test-3', 'title': 'Completely unrelated task', 'description': 'This has nothing to do with the main goal'}
    issues = cognitive_agent.analyze(subtask_drift, {'goal': 'Build a web application with authentication'})
    print(f'Issues found: {issues}')

    # Test 4: No issues case
    print('\n--- Test 4: No Issues Case ---')
    good_subtask = {'id': 'test-4', 'title': 'Build authentication module', 'result': 'Authentication module successfully built'}
    issues = cognitive_agent.analyze(good_subtask, {'goal': 'Build a web application with authentication'})
    print(f'Issues found: {issues}')

    # Test 5: Early exit option
    print('\n--- Test 5: Early Exit Option ---')
    multi_issue_subtask = {
        'id': 'test-5',
        'title': 'Unrelated task', 
        'result': 'Lorem ipsum dolor sit amet',
        'error': 'This contains a logical contradiction.'
    }
    start = time.time()
    all_issues = cognitive_agent.analyze(multi_issue_subtask, {'goal': 'Build a web application'})
    full_time = time.time() - start

    start = time.time()
    early_exit_issues = cognitive_agent.analyze(multi_issue_subtask, {'goal': 'Build a web application'}, early_exit=True)
    early_time = time.time() - start

    print(f'All issues: {all_issues}')
    print(f'Early exit issues: {early_exit_issues}')
    print(f'Full analysis time: {full_time:.6f}s, Early exit time: {early_time:.6f}s')

    # Test 6: Runtime pattern configuration
    print('\n--- Test 6: Runtime Pattern Configuration ---')
    new_hallucination_patterns = [
        (r'cannot\s+assist', 'Custom cannot assist pattern'),
        (r'custom\s+pattern', 'Custom pattern')
    ]
    new_reasoning_patterns = [
        (r'illogical', 'Custom illogical pattern')
    ]

    cognitive_agent.set_regex_patterns(new_hallucination_patterns, new_reasoning_patterns)
    print('Updated regex patterns at runtime')

    # Test with old pattern - should no longer detect
    old_pattern_subtask = {'id': 'test-6a', 'result': 'As an AI, I cannot access external systems.'}
    issues = cognitive_agent.analyze(old_pattern_subtask, {'goal': 'Test goal'})
    print(f'Old pattern detection (should be empty): {issues}')

    # Test with new pattern - should detect
    new_pattern_subtask = {'id': 'test-6b', 'result': 'I cannot assist with that request.'}
    issues = cognitive_agent.analyze(new_pattern_subtask, {'goal': 'Test goal'})
    print(f'New pattern detection: {issues}')

    # Test 7: Performance and caching
    print('\n--- Test 7: Performance and Caching ---')
    large_result = 'This is a large result ' * 1000
    large_subtask = {'result': large_result, 'title': 'Performance test'}

    start_time = time.time()
    cognitive_agent.analyze(large_subtask, {'goal': 'Test performance'})
    single_execution_time = time.time() - start_time
    print(f'Large analysis execution time: {single_execution_time:.6f} seconds')

    # Test caching effectiveness
    start_time = time.time()
    for _ in range(10):
        cognitive_agent.analyze({'title': f'Task {_}'}, {'goal': 'Same goal repeatedly'})
    cached_time = time.time() - start_time

    # Reset cache
    cognitive_agent.goal_keywords_cache = {}

    # Run again with different goals
    start_time = time.time()
    for i in range(10):
        cognitive_agent.analyze({'title': f'Task {i}'}, {'goal': f'Different goal {i}'})
    uncached_time = time.time() - start_time

    print(f'Cached execution time (10 runs): {cached_time:.6f}s, Uncached (10 runs): {uncached_time:.6f}s')
    if cached_time > 0:
        print(f'Cache speedup factor: {uncached_time/cached_time:.2f}x')

    # Test 8: Thread safety
    print('\n--- Test 8: Thread Safety Test ---')

    # Function to run in threads
    def analyze_in_thread(thread_id):
        goal = f'Thread goal {thread_id}'
        subtask = {'title': f'Thread task {thread_id}', 'result': f'Thread result {thread_id}'}
        results = cognitive_agent.analyze(subtask, {'goal': goal})
        # Just to ensure we're accessing the cache
        cognitive_agent._extract_goal_keywords(goal)

    # Create and start 5 threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=analyze_in_thread, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print('Multithreaded test completed without errors')

    # Test 9: Batch analysis
    print('\n--- Test 9: Batch Analysis ---')
    subtasks = [
        {'id': '1', 'title': 'Build components', 'result': 'Components successfully built'},
        {'id': '2', 'title': 'Unrelated task', 'result': 'I cannot assist with that request.'},
        {'id': '3', 'title': 'Debug errors', 'error': 'Completely illogical solution.'}
    ]

    batch_results = cognitive_agent.analyze_batch(subtasks, {'goal': 'Build a web application with authentication'})
    print(f'Batch analysis results:')
    for task_id, issues in batch_results.items():
        print(f'  Task {task_id}: {issues}')

if __name__ == "__main__":
    main()
