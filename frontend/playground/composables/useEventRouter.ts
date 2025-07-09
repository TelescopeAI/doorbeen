import type { SSEEvent } from '~/types/streaming';
import type { useStreamState } from './useStreamState';

// Type for event handler functions
type EventHandler = (event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) => void;

// Map of event types to their handlers
const createEventHandlers = (): Record<string, EventHandler> => ({
  'agent:stream:start': handleStreamStart,
  'agent:tool:invoke': handleToolInvoke,
  'agent:stream:output': handleStreamOutput,
  'agent:stream:end': handleStreamEnd,
  'agent:start': handleAgentStart,
  'agent:progress': handleAgentProgress,
  'agent:error': handleAgentError,
  'agent:warning': handleAgentWarning,
  'agent:end': handleAgentEnd,
  'assistant:node:output': handleNodeOutput,
  'assistant:agent:output': handleAgentOutput,
  'supervisor:decision': handleSupervisorDecision,
  'agent:handoff': handleAgentHandoff,
  'thread_info': handleThreadInfo,
  'stream:termination': handleStreamTermination,
  'error': handleError,
});

// Event handler implementations
function handleStreamStart(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('🚀 Stream started:', event);
  stateManager.startStream();
  
  if (event.data?.agent_name) {
    stateManager.setCurrentAgent(event.data.agent_name);
  }
}

function handleToolInvoke(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('🔧 Tool invoked:', event);
  
  const toolName = event.name || event.data?.name || 'Unknown Tool';
  const stepId = stateManager.addThinkingStep({
    type: 'tool_call',
    title: `Invoking ${toolName}`,
    content: event.data,
    status: 'running',
    agentName: stateManager.state.currentAgent,
  });
  
  // Store the step ID for potential updates
  (event as any)._stepId = stepId;
}

function handleStreamOutput(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('💬 Stream output:', event);
  
  const agentName = event.name || stateManager.state.currentAgent || 'Unknown Agent';
  const content = event.data?.content || '';
  
  // Check if we have a running step for this agent
  const runningStep = stateManager.findStep(step => 
    step.agentName === agentName && 
    step.status === 'running' && 
    step.type === 'agent_output'
  );
  
  if (runningStep) {
    // Append to existing step
    stateManager.appendToLastStepContent(content);
  } else {
    // Create new step
    stateManager.addThinkingStep({
      type: 'agent_output',
      title: `${getDisplayName(agentName)} Analysis`,
      content: content,
      status: 'running',
      agentName,
    });
  }
  
  // Also append to final answer
  stateManager.appendToFinalAnswer(content);
}

function handleStreamEnd(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('🏁 Stream ended:', event);
  
  // Mark the last step as complete
  stateManager.updateLastThinkingStep({ status: 'complete' });
  stateManager.endStream();
}

function handleAgentStart(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('👋 Agent started:', event);
  
  const agentName = event.name || event.data?.agent_name || 'Unknown Agent';
  stateManager.setCurrentAgent(agentName);
  
  stateManager.addThinkingStep({
    type: 'thought',
    title: `${getDisplayName(agentName)} Started`,
    content: event.data?.description || `${agentName} is starting analysis`,
    status: 'complete',
    agentName,
  });
}

function handleAgentEnd(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('👋 Agent ended:', event);
  
  const agentName = event.name || event.data?.agent_name || stateManager.state.currentAgent;
  
  // Mark any running steps for this agent as complete
  const runningSteps = stateManager.findStepsByAgent(agentName || '').filter(step => step.status === 'running');
  runningSteps.forEach(step => {
    stateManager.updateThinkingStep(step.id, { status: 'complete' });
  });
}

function handleAgentProgress(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('📊 Agent progress:', event);
  
  const agentName = event.name || event.data?.agent_name || stateManager.state.currentAgent || 'Unknown Agent';
  const progress = event.data?.progress || 0;
  const description = event.data?.description || 'Processing...';
  const content = event.data?.content || '';
  const scope = event.data?.scope || agentName;
  
  console.log(`📊 Progress for ${agentName}: ${progress}% - ${description}`);
  
  // Create or update a progress step for this agent
  stateManager.addThinkingStep({
    type: 'agent_output',
    title: description,
    content: content || `${description} (${progress}%)`,
    status: progress >= 100 ? 'complete' : 'running',
    agentName: agentName,
    progress: progress,
  });
  
  // Update current agent if not set
  if (!stateManager.state.currentAgent && agentName !== 'Unknown Agent') {
    stateManager.setCurrentAgent(agentName);
  }
}

function handleNodeOutput(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('📤 Node output:', event);
  
  const nodeName = event.name || 'Unknown Node';
  const content = event.data?.content || event.data;
  
  // Handle stream termination
  if (nodeName === 'stream_termination' || nodeName === 'conversation_complete') {
    stateManager.endStream();
    return;
  }
  
  stateManager.addThinkingStep({
    type: 'tool_output',
    title: `${getDisplayName(nodeName)} Output`,
    content: content,
    status: 'complete',
    agentName: stateManager.state.currentAgent,
  });
}

function handleAgentOutput(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('🤖 Agent output:', event);
  
  // This is similar to handleStreamOutput but for structured agent outputs
  handleStreamOutput(event, stateManager);
}

function handleSupervisorDecision(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('👨‍💼 Supervisor decision:', event);
  
  stateManager.addThinkingStep({
    type: 'thought',
    title: 'Supervisor Decision',
    content: event.data,
    status: 'complete',
  });
}

function handleAgentHandoff(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('🔄 Agent handoff:', event);
  
  const handoffInfo = event.data;
  stateManager.addThinkingStep({
    type: 'thought',
    title: 'Agent Handoff',
    content: `Transitioning from ${handoffInfo?.source_agent} to ${handoffInfo?.target_agent}: ${handoffInfo?.reason}`,
    status: 'complete',
  });
  
  if (handoffInfo?.target_agent) {
    stateManager.setCurrentAgent(handoffInfo.target_agent);
  }
}

function handleThreadInfo(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('📄 Thread info:', event);
  // Just log these, no UI updates needed
}

function handleError(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.error('❌ Stream error:', event);
  
  const errorMessage = event.data?.error || event.data?.message || 'An unknown error occurred';
  stateManager.setError(errorMessage);
}

function handleAgentError(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.error('❌ Agent error:', event);
  
  const agentName = event.name || event.data?.agent_name || stateManager.state.currentAgent || 'Unknown Agent';
  const errorMessage = event.data?.description || event.data?.error || 'An agent error occurred';
  const content = event.data?.content || errorMessage;
  
  stateManager.addThinkingStep({
    type: 'agent_output',
    title: `❌ ${errorMessage}`,
    content: content,
    status: 'error',
    agentName: agentName,
  });
}

function handleAgentWarning(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.warn('⚠️ Agent warning:', event);
  
  const agentName = event.name || event.data?.agent_name || stateManager.state.currentAgent || 'Unknown Agent';
  const warningMessage = event.data?.description || event.data?.warning || 'An agent warning occurred';
  const content = event.data?.content || warningMessage;
  
  stateManager.addThinkingStep({
    type: 'agent_output',
    title: `⚠️ ${warningMessage}`,
    content: content,
    status: 'complete', // Warnings don't stop the process
    agentName: agentName,
  });
}

function handleStreamTermination(event: SSEEvent, stateManager: ReturnType<typeof useStreamState>) {
  console.log('🛑 Stream termination:', event);
  
  // Log termination details for debugging
  if (event.data) {
    console.log('📊 Termination details:', event.data);
  }
  
  // End the stream and mark all running steps as complete
  stateManager.endStream();
  
  // Mark any remaining running steps as complete
  const runningSteps = stateManager.state.thinkingSteps.filter(step => step.status === 'running');
  runningSteps.forEach(step => {
    stateManager.updateThinkingStep(step.id, { status: 'complete' });
  });
}

// Helper function to get display-friendly names
function getDisplayName(agentName: string): string {
  const nameMap: Record<string, string> = {
    'QueryGenerator': 'Query Generator',
    'QueryGeneration': 'Query Generator',
    'DataAnalyst': 'Data Analyst',
    'DataAnalysis': 'Data Analyst',
    'ResultProcessor': 'Result Processor',
    'ResultProcessing': 'Result Processor',
    'Finalizer': 'Finalizer',
    'Finalization': 'Finalizer',
    'ObjectiveEvaluator': 'Objective Evaluator',
    'ObjectiveEvaluation': 'Objective Evaluator',
    'ExplorationAgent': 'Data Explorer',
    'QueryExecutor': 'Query Executor',
    'ResultsAnalyzer': 'Results Analyzer',
    'supervisor': 'Supervisor',
    'Supervisor': 'Supervisor',
  };
  
  return nameMap[agentName] || agentName;
}

export function useEventRouter(stateManager: ReturnType<typeof useStreamState>) {
  const eventHandlers = createEventHandlers();
  
  const routeEvent = (event: SSEEvent) => {
    console.log('🔀 Routing event:', event.type || event.event, event);
    
    const eventType = event.type || event.event;
    
    if (!eventType) {
      console.warn('Event received without type or event field:', event);
      return;
    }
    
    const handler = eventHandlers[eventType];
    
    if (handler) {
      try {
        handler(event, stateManager);
      } catch (error) {
        console.error(`Error handling event ${eventType}:`, error);
        stateManager.setError(`Error processing ${eventType}: ${error}`);
      }
    } else {
      console.warn(`No handler for event type: ${eventType}`, event);
    }
  };
  
  const registerHandler = (eventType: string, handler: EventHandler) => {
    eventHandlers[eventType] = handler;
  };
  
  const unregisterHandler = (eventType: string) => {
    delete eventHandlers[eventType];
  };
  
  return {
    routeEvent,
    registerHandler,
    unregisterHandler,
    eventHandlers,
  };
} 