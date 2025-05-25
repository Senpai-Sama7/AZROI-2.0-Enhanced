# Project AZROI: Implementation Dependency Map

## Understanding the Critical Path

This dependency map helps you understand why certain components must be built before others. Think of it like constructing a building - you need a solid foundation before you can add the walls, and you need walls before you can install the windows.

## Phase 1: Foundation Dependencies (Must Complete First)

### Core CrewAI Infrastructure
**Why This Comes First**: Everything else depends on having functional multi-agent orchestration. Without this foundation, the UI has nothing meaningful to display, and the cloud agents have no framework to operate within.

#### Critical Sequence:
1. **LLMRouter.py Enhancement** → *Enables all agent LLM communication*
2. **Pydantic Models for Tool I/O** → *Establishes data contracts for all agent interactions*
3. **Basic CrewAI Tool Framework** → *Provides the mechanism for agents to perform actions*
4. **Individual Agent Implementation** → *Creates the specialized workers*
5. **AgentOrchestrator.py Complete Refactor** → *Ties everything together into working crews*

### Why This Order Matters:
- **LLMRouter First**: Every agent needs to communicate with language models, so this routing system must be stable before agents can be properly tested
- **Pydantic Models Early**: These data contracts prevent integration headaches later - it's much easier to define clean interfaces upfront than to refactor messy data passing later
- **Tools Before Orchestration**: The orchestrator needs functional tools to assign to agents, so tools must be implemented and tested independently first

## Phase 2: Integration Dependencies

### Backend-Frontend Communication Bridge
**Dependency**: Requires Phase 1 AgentOrchestrator to be functional

#### Sequential Requirements:
1. **WebSocket Message Schema Definition** → *Based on CrewAI events from Phase 1*
2. **Backend WebSocket Abstraction Layer** → *Translates CrewAI events to UI-friendly messages*
3. **Frontend WebSocket Handler Updates** → *Processes the new message types*
4. **UI Component Updates** → *Displays the processed information*

### Why This Sequence is Critical:
The WebSocket schema can't be properly designed until you understand what events CrewAI actually generates. Trying to design the UI components before knowing what data they'll receive leads to constant rework.

## Phase 3: Platform-Specific Dependencies

### Multi-Cloud Implementation Strategy
**Dependency**: Requires functional CrewAI framework and basic cloud agent structure

#### Parallel Development Possible:
- **GCP Agent Tools** ← Can develop simultaneously → **Azure Agent Tools**
- **GCP UI Components** ← Can develop simultaneously → **Azure UI Components**

#### Sequential Dependencies Within Each Platform:
1. **Cloud SDK Integration** → *Basic connectivity and authentication*
2. **Individual Service Tools** → *Granular operations like storage, compute, deployment*
3. **Composite Workflow Tools** → *Higher-level operations that combine multiple services*
4. **UI Integration** → *Platform-specific display and selection components*

## Phase 4: Quality and Documentation Dependencies

### Testing Implementation Order
**Dependency**: Requires functional components from previous phases

#### Testing Sequence:
1. **Unit Tests for Tools** → *Test individual CrewAI tools in isolation*
2. **Agent Integration Tests** → *Test agents using their tools*
3. **Orchestrator Integration Tests** → *Test full crew workflows*
4. **UI Component Tests** → *Test frontend components with mocked backend*
5. **End-to-End Tests** → *Test complete user journeys*

### Documentation Dependencies
**Dependency**: Requires implemented features to document

#### Documentation Order:
1. **Code Documentation** → *As you implement each component*
2. **API Documentation** → *After backend APIs are stable*
3. **User Documentation** → *After UI is functional*
4. **Architectural Documentation** → *After all major components are integrated*

## Critical Bottlenecks to Watch

### Bottleneck 1: CrewAI Tool Definition
**Risk**: If tools are poorly designed, every agent will struggle
**Mitigation**: Invest extra time in tool design and testing before moving to orchestration

### Bottleneck 2: WebSocket Message Schema
**Risk**: Changes to backend events require frontend rework
**Mitigation**: Design message schema to be extensible and version-compatible

### Bottleneck 3: Memory/State Management
**Risk**: Inconsistent state across agents can cause cascade failures
**Mitigation**: Implement and test state management early, before complex workflows

## Parallel Development Opportunities

### What Can Be Done Simultaneously:
- **Frontend UI Components** (with mocked data) while **Backend Tools** are being implemented
- **GCP Agent Development** while **Azure Agent Development** proceeds
- **Documentation Writing** while **Testing Implementation** happens
- **Security Hardening** while **Performance Optimization** occurs

### What Must Be Sequential:
- **Tool Implementation** before **Agent Implementation**
- **Agent Implementation** before **Orchestrator Implementation**
- **Backend WebSocket Events** before **Frontend WebSocket Handling**
- **Component Implementation** before **Integration Testing**

## Risk Mitigation Strategies

### High-Risk Dependencies:
1. **CrewAI Framework Integration**: New framework with potential undocumented behaviors
   - **Mitigation**: Build simple test cases early, maintain fallback plans
2. **Multi-Agent State Synchronization**: Complex distributed state management
   - **Mitigation**: Implement comprehensive logging and state validation
3. **Real-Time UI Updates**: Complex WebSocket state management
   - **Mitigation**: Design for graceful degradation when real-time updates fail

This dependency map serves as your implementation compass. When you're unsure what to work on next, refer back to this map to understand which components are blocking others and which can proceed in parallel.