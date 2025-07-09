import { reactive, ref, computed } from 'vue';

// Define a unified interface for any step in the reasoning process
export interface ReasoningStep {
  id: string;
  type: 'thought' | 'tool_call' | 'tool_output' | 'agent_output';
  title: string;
  content: string | object;
  status: 'running' | 'complete' | 'error';
  agentName?: string;
  timestamp: string;
  progress?: number; // Added progress field for tracking agent progress
}

export interface StreamState {
  thinkingSteps: ReasoningStep[];
  finalAnswer: string | null;
  isStreaming: boolean;
  error: string | null;
  currentAgent?: string;
  streamStarted: boolean;
}

export function useStreamState() {
  const state = reactive<StreamState>({
    thinkingSteps: [],
    finalAnswer: null,
    isStreaming: false,
    error: null,
    currentAgent: undefined,
    streamStarted: false,
  });

  // Computed properties for easier access
  const hasSteps = computed(() => state.thinkingSteps.length > 0);
  const hasError = computed(() => !!state.error);
  const currentStepCount = computed(() => state.thinkingSteps.length);

  // State mutations
  const startStream = () => {
    state.isStreaming = true;
    state.streamStarted = true;
    state.error = null;
    state.thinkingSteps = [];
    state.finalAnswer = null;
  };

  const endStream = () => {
    state.isStreaming = false;
  };

  const setError = (error: string) => {
    state.error = error;
    state.isStreaming = false;
  };

  const setCurrentAgent = (agentName: string) => {
    state.currentAgent = agentName;
  };

  const addThinkingStep = (step: Omit<ReasoningStep, 'id' | 'timestamp'>): string => {
    const id = `step-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const fullStep: ReasoningStep = {
      ...step,
      id,
      timestamp: new Date().toISOString(),
    };
    
    // Create a new array to trigger reactivity
    state.thinkingSteps = [...state.thinkingSteps, fullStep];
    return id;
  };

  const updateThinkingStep = (id: string, updates: Partial<ReasoningStep>) => {
    const index = state.thinkingSteps.findIndex(step => step.id === id);
    if (index !== -1) {
      // Create new array with updated step to trigger reactivity
      const updatedSteps = [...state.thinkingSteps];
      updatedSteps[index] = { ...updatedSteps[index], ...updates };
      state.thinkingSteps = updatedSteps;
    }
  };

  const updateLastThinkingStep = (updates: Partial<ReasoningStep>) => {
    if (state.thinkingSteps.length > 0) {
      const lastIndex = state.thinkingSteps.length - 1;
      const lastStep = state.thinkingSteps[lastIndex];
      updateThinkingStep(lastStep.id, updates);
    }
  };

  const appendToLastStepContent = (content: string) => {
    if (state.thinkingSteps.length > 0) {
      const lastStep = state.thinkingSteps[state.thinkingSteps.length - 1];
      const currentContent = typeof lastStep.content === 'string' ? lastStep.content : JSON.stringify(lastStep.content, null, 2);
      updateThinkingStep(lastStep.id, {
        content: currentContent + content
      });
    }
  };

  const setFinalAnswer = (answer: string) => {
    state.finalAnswer = answer;
  };

  const appendToFinalAnswer = (content: string) => {
    if (state.finalAnswer) {
      state.finalAnswer += content;
    } else {
      state.finalAnswer = content;
    }
  };

  const resetState = () => {
    state.thinkingSteps = [];
    state.finalAnswer = null;
    state.isStreaming = false;
    state.error = null;
    state.currentAgent = undefined;
    state.streamStarted = false;
  };

  // Helper function to find step by criteria
  const findStep = (predicate: (step: ReasoningStep) => boolean): ReasoningStep | undefined => {
    return state.thinkingSteps.find(predicate);
  };

  const findStepsByType = (type: ReasoningStep['type']): ReasoningStep[] => {
    return state.thinkingSteps.filter(step => step.type === type);
  };

  const findStepsByAgent = (agentName: string): ReasoningStep[] => {
    return state.thinkingSteps.filter(step => step.agentName === agentName);
  };

  return {
    // State
    state,
    
    // Computed
    hasSteps,
    hasError,
    currentStepCount,
    
    // Mutations
    startStream,
    endStream,
    setError,
    setCurrentAgent,
    addThinkingStep,
    updateThinkingStep,
    updateLastThinkingStep,
    appendToLastStepContent,
    setFinalAnswer,
    appendToFinalAnswer,
    resetState,
    
    // Queries
    findStep,
    findStepsByType,
    findStepsByAgent,
  };
} 