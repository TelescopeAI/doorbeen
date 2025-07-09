# Enhanced Event Streaming System

## Overview

The enhanced event streaming system provides rich context information for better frontend UI handling. Each event now includes:

- **Category**: Type of event (progress, error, tool_call, etc.)
- **Source**: Which agent/component generated the event
- **Stage**: Which workflow stage the event belongs to
- **Metadata**: Additional context for UI customization

## Event Structure

```typescript
interface AgentEvent {
  type: string;           // Event type (e.g., "agent:progress", "agent:error")
  name: string;           // Event name (e.g., "QueryGeneration", "DataAnalyst")
  data: any;              // Event-specific data
  occurred_at: string;    // ISO timestamp
  category: string;       // Event category for UI handling
  source: string;         // Source agent/component
  stage: string;          // Workflow stage
  metadata: object;       // Additional context
}
```

## Categories

- **`progress`**: Progress updates and status information
- **`error`**: Error events that need user attention
- **`warning`**: Warning events for potential issues
- **`tool_call`**: Tool invocation events
- **`agent_output`**: Agent responses and outputs
- **`handoff`**: Agent handoff and coordination events
- **`supervisor`**: Supervisor routing and coordination
- **`lifecycle`**: Agent start/end events

## Sources

- **`supervisor`**: Main supervisor agent
- **`data_analyst`**: Data analysis agent
- **`query_generator`**: Query generation agent
- **`result_processor`**: Result processing agent
- **`finalizer`**: Finalization agent
- **`objective_evaluator`**: Objective evaluation agent
- **`system`**: System-level events

## Stages

- **`initialization`**: Initial setup and preparation
- **`planning`**: Query planning and strategy
- **`schema_analysis`**: Database schema analysis
- **`query_generation`**: SQL query generation
- **`query_validation`**: Query validation and correction
- **`query_execution`**: Query execution
- **`result_processing`**: Result analysis and processing
- **`finalization`**: Final answer generation
- **`handoff`**: Agent handoffs
- **`error_handling`**: Error handling and recovery

## Frontend Usage Examples

### Progress Tracking

```typescript
// Group events by stage for progress visualization
const progressByStage = events
  .filter(e => e.category === 'progress')
  .reduce((acc, event) => {
    acc[event.stage] = event.metadata.progress || 0;
    return acc;
  }, {});
```

### Error Handling

```typescript
// Display errors with context
const errorEvents = events
  .filter(e => e.category === 'error')
  .map(event => ({
    source: event.source,
    stage: event.stage,
    message: event.metadata.description,
    details: event.data
  }));
```

### Agent Activity Tracking

```typescript
// Track which agents are active
const activeAgents = events
  .filter(e => e.category === 'lifecycle' && e.type === 'agent:start')
  .map(e => e.source);
```

### Tool Call Visualization

```typescript
// Show tool calls with context
const toolCalls = events
  .filter(e => e.category === 'tool_call')
  .map(event => ({
    tool: event.name,
    agent: event.source,
    stage: event.stage,
    status: 'running' // or 'completed' based on follow-up events
  }));
```

### Stage-based UI Updates

```typescript
// Update UI based on current stage
const currentStage = events
  .filter(e => e.category === 'progress')
  .sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at))[0]?.stage;

switch (currentStage) {
  case 'schema_analysis':
    // Show schema analysis UI
    break;
  case 'query_generation':
    // Show query generation UI
    break;
  case 'query_execution':
    // Show query execution UI
    break;
  // ... etc
}
```

## Metadata Fields

Common metadata fields include:

- **`node_name`**: LangGraph node name
- **`scope`**: Event scope (e.g., "QueryGeneration")
- **`progress`**: Progress percentage (0-100)
- **`description`**: Human-readable description
- **`content`**: Event content/message
- **`workflow_stage`**: Internal workflow stage
- **`attempt`**: Attempt number for retries
- **`tool_call_id`**: Tool call identifier
- **`content_length`**: Content length for sizing

## Benefits for Frontend

1. **Better UX**: Rich context allows for more informative UI
2. **Progress Tracking**: Stage-based progress visualization
3. **Error Handling**: Contextual error messages with source information
4. **Agent Visualization**: Track agent activity and handoffs
5. **Filtering**: Easy filtering by category, source, or stage
6. **Customization**: Metadata allows for custom UI behaviors 