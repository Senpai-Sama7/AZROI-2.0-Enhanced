## Testing

The Autonomous AI Architect includes comprehensive testing capabilities:

### Running Tests

1. Make the test script executable:
   ```bash
   chmod +x run_tests.sh
   ```

2. Run all tests:
   ```bash
   ./run_tests.sh
   ```

3. Run a specific test file:
   ```bash
   ./run_tests.sh backend/tests/test_cloud_agent.py
   ```

### Test Coverage

The testing suite includes:

1. **Unit Tests**: Testing individual components in isolation.
   - Cloud Agent operations (GCS, Cloud Build, Cloud Run, Artifact Registry)
   - Code Execution Agent sandbox operations
   - Planner Agent planning functionality

2. **Integration Tests**: Testing how components work together.
   - Agent orchestration workflow
   - End-to-end processing of user goals

### Autonomous Verification Engine (AVE)

The project includes an Autonomous Verification Engine (AVE) that performs comprehensive testing without human interaction:

1. **Codebase Ingestion**
   - Automatically clones or unpacks the repository into an isolated sandbox
   - Verifies repository integrity

2. **Feature Discovery**
   - Analyzes code semantics, comments, and configurations
   - Enumerates distinct user-facing features and core functionalities with unique IDs

3. **Behavior Inference**
   - Infers correct expected behavior from code logic
   - Identifies preconditions, postconditions, success criteria, and error handling paths

4. **Test Plan Generation**
   - Automatically creates comprehensive test suites for each feature
   - Covers positive cases, negative cases, and boundary conditions

5. **Test Execution**
   - Runs all tests in a sandbox harness against the application logic
   - Logs outputs, state changes, return values, exceptions, and side effects

6. **Validation & Discrepancy Analysis**
   - Compares observed outcomes to inferred expected behavior
   - Classifies each feature as Verified, Discrepancy Identified, or Execution Error

7. **Final Report Generation**
   - Produces a detailed Markdown report with all findings

### AVE Report Format

The AVE generates a comprehensive Markdown report with:

- **Executive Summary**: Overview of total features, verification status percentages
- **Feature Analyses**: Detailed breakdown of each feature, expected behavior, test results
- **Appendices**: Full logs, test definitions, and supplementary data

### Required Files and Directories for AVE Implementation

To fully implement the Autonomous Verification Engine (AVE) as described, the following components need to be added to the project:

1. **AVE Core Components**
   - `/backend/ave/` - Main directory for AVE implementation
   - `/backend/ave/engine.py` - Main entry point for the verification engine
   - `/backend/ave/codebase_ingestion.py` - Module for repository cloning and integrity verification
   - `/backend/ave/feature_discovery.py` - Code analysis and feature identification
   - `/backend/ave/behavior_inference.py` - Logic to determine expected behavior
   - `/backend/ave/test_generator.py` - Automated test plan creation
   - `/backend/ave/test_executor.py` - Test execution in sandbox environment
   - `/backend/ave/discrepancy_analyzer.py` - Validation and issue identification
   - `/backend/ave/report_generator.py` - Markdown report generation

2. **AVE Sandbox Environment**
   - `/backend/ave/sandbox/` - Isolated execution environment
   - `/backend/ave/sandbox/container.py` - Container management for isolated testing
   - `/backend/ave/sandbox/harness.py` - Test harness implementation

3. **AVE Configuration**
   - `/backend/ave/config/` - Configuration files
   - `/backend/ave/config/ave_config.yaml` - Main configuration file
   - `/backend/ave/config/test_templates/` - Templates for generated tests

4. **AVE CLI Tool**
   - `/backend/ave/cli.py` - Command-line interface for AVE
   - `/run_ave.sh` - Shell script to execute the verification engine

5. **AVE Tests**
   - `/backend/tests/ave/` - Tests for AVE components
   - `/backend/tests/ave/test_engine.py` - Tests for the verification engine
   - `/backend/tests/ave/test_feature_discovery.py` - Tests for feature analysis

6. **Additional Dependencies**
   - Update `requirements.txt` to include:
     - Docker SDK for Python (for sandbox isolation)
     - Static code analysis libraries
     - Test generation frameworks
     - Report generation dependencies

### AVE Usage

Once implemented, add the following to the run_tests.sh script:

```bash
# Run the Autonomous Verification Engine
function run_ave() {
  python -m backend.ave.cli --repo-path=$1 --output-dir=$2
}

# Example usage
# ./run_tests.sh ave /path/to/repo /path/to/output
```

### AVE Integration

The AVE should be integrated with the CI/CD pipeline to automatically run on code changes:

1. Add a GitHub Actions workflow file: `.github/workflows/ave.yml`
2. Configure the workflow to run AVE on pull requests and merges to main
3. Archive and publish the verification reports as artifacts

These components will provide the necessary infrastructure to fully implement the Autonomous Verification Engine as described in the documentation.

### Fractal Feedback Loop for UI Improvement

The Autonomous AI Architect UI implements a Fractal Feedback Loop (FFL) system to continuously improve the user interface:

1. **UI Self-Evaluation Layer**
   - The UI continuously collects usage metrics and interaction patterns
   - Heatmaps and session recordings identify friction points
   - Automated accessibility and UX evaluations run periodically

2. **Recursive UI Enhancement**
   - UI improvements are applied at multiple levels (component, page, workflow)
   - Each enhancement is tested against multiple personas and use cases
   - The system visualizes improvement targets as a recursive tree structure

3. **UI Implementation Requirements**
   - `/frontend/src/ffl/` - Main directory for UI FFL implementation
   - `/frontend/src/ffl/UIMonitor.tsx` - Collects UI interaction metrics 
   - `/frontend/src/ffl/UIAnalyzer.tsx` - Identifies patterns and improvement areas
   - `/frontend/src/ffl/UIOptimizer.tsx` - Implements UI component improvements
   - `/frontend/src/ffl/config/ffl_config.json` - Configuration for the UI feedback loop

4. **UI Feedback Visualization**
   - `/frontend/src/components/FeedbackLoopVisualizer.tsx` - Interactive visualization of the feedback loop
   - `/frontend/src/pages/UIMetricsPage.tsx` - Dashboard for viewing UI metrics

### Absolute Zero Reasoner (AZR) for UI

The project includes an Absolute Zero Reasoner (AZR) implementation for the UI, providing advanced interaction capabilities:

1. **Zero-shot UI Planning & Adaptation**
   - Dynamically adjusts UI based on user goals without predefined templates
   - Builds custom UI workflows on-the-fly for novel user requests
   - Implementation path: `/frontend/src/azr/UIPlanner.tsx`

2. **Tool-augmented UI Reasoning**
   - Intelligently integrates appropriate UI tools based on the current task
   - Dynamically builds UI control panels based on available backend tools
   - Implementation path: `/frontend/src/azr/ToolSelector.tsx`

3. **UI Chain-of-Thought Visualization**
   - Visualizes reasoning chains to help users understand system decisions
   - Provides interactive decision trees for complex operations
   - Implementation path: `/frontend/src/azr/ReasoningVisualizer.tsx`

4. **Multi-view Orchestration**
   - Coordinates multiple UI views based on complex reasoning about user needs
   - Intelligently manages screen real estate for multi-step workflows
   - Implementation path: `/frontend/src/azr/ViewOrchestrator.tsx`

5. **AZR UI Testing Integration**
   - Specialized UI test generators for reasoning-based interfaces
   - Automated testing of dynamically generated UI components
   - Implementation paths:
     - `/frontend/src/tests/azr/UIReasoningTests.tsx`
     - `/frontend/cypress/e2e/azr-ui-flows.cy.ts`

6. **Required Implementation Files**
   - `/frontend/src/azr/` - Main directory for UI AZR implementation
   - `/frontend/src/azr/core/` - Core reasoning components for UI
   - `/frontend/src/azr/components/` - Reusable reasoning-based UI components
   - `/frontend/src/azr/hooks/useReasoning.ts` - React hook for reasoning capabilities
   - `/frontend/src/azr/config/reasoning_templates.json` - UI reasoning templates

### Testing AZR and FFL UI Components

To test these advanced UI components:

1. **Unit Testing**
   - Component-level tests for AZR UI elements
   - Hook testing for reasoning functions
   - Redux state testing for feedback loop data

2. **Integration Testing**
   - Testing interactions between reasoning components
   - Testing feedback loop integration with UI components

3. **End-to-End Testing**
   - Cypress tests for complete AZR-powered user journeys
   - Automated accessibility testing for dynamically generated UIs

4. **Usage Example**
   ```bash
   # Test UI reasoning components
   npm test -- --testPathPattern=src/azr
   
   # Run E2E tests for AZR UI flows
   npm run cypress:run -- --spec "cypress/e2e/azr-ui-flows.cy.ts"
   ```

### Adding New Tests

To add new tests:

1. Create a new test file in the `backend/tests/` directory.
2. Follow the pytest conventions for test naming.
3. Use the existing test files as templates.

### Test Dependencies

The test suite requires:
- pytest
- pytest-asyncio

These are included in the `requirements.txt` file and will be installed during setup.
