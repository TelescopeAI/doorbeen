import { ref, computed } from 'vue'
import type { 
  AgentCoordinationOutput, 
  StreamResponse 
} from '~/types/streaming'

export const useAgentCoordination = () => {
  // Mock data for testing agent coordination features
  const mockSupervisorDecisions = ref([
    {
      decision_type: 'route',
      target_agent: 'data_analysis_agent',
      reasoning: 'Need to analyze the database schema and understand available tables before generating queries',
      confidence: 0.95,
      iteration: 1,
      timestamp: new Date().toISOString()
    },
    {
      decision_type: 'route',
      target_agent: 'query_generation_agent', 
      reasoning: 'Schema analysis complete, now generating optimized SQL query based on user requirements',
      confidence: 0.88,
      iteration: 2,
      timestamp: new Date().toISOString()
    }
  ])

  const mockAgentHandoffs = ref([
    {
      source_agent: 'data_analysis_agent',
      target_agent: 'query_generation_agent',
      reason: 'Schema analysis complete, handing off to query generation',
      context: {
        tables_found: ['customers', 'orders', 'products'],
        domain: 'e-commerce',
        complexity: 'medium'
      },
      timestamp: new Date().toISOString()
    }
  ])

  const mockAgentFlow = ref([
    {
      name: 'data_analysis_agent',
      status: 'complete' as const,
      context: 'Analyzed database schema, found 12 tables, identified e-commerce domain',
      duration: 2500,
      startTime: new Date().toISOString(),
      endTime: new Date().toISOString()
    },
    {
      name: 'query_generation_agent',
      status: 'active' as const,
      context: 'Generating SQL query for top customers by revenue',
      duration: 1800
    },
    {
      name: 'result_processing_agent',
      status: 'pending' as const,
      context: 'Waiting for query results to process'
    }
  ])

  const mockAgentProgress = ref({
    agent_name: 'query_generation_agent',
    progress_percentage: 65,
    status: 'working' as const,
    familiar_node_name: 'generate_sql_query_node',
    current_task: 'Optimizing JOIN operations for performance'
  })

  const mockObjectiveStatus = ref({
    identified: [
      'Find top 5 customers by revenue',
      'Include customer details',
      'Sort by revenue descending'
    ],
    completed: [
      'Find top 5 customers by revenue',
      'Include customer details'
    ],
    remaining: [
      'Sort by revenue descending'
    ],
    completion_confidence: 0.85,
    overall_status: 'partial' as const
  })

  const mockRetryHistory = ref([
    {
      agent_name: 'query_generation_agent',
      attempt_number: 2,
      max_retries: 3,
      reason: 'Query optimization timeout',
      strategy: 'incremental_backoff',
      error: 'Query execution took longer than 30 seconds',
      timestamp: new Date().toISOString()
    }
  ])

  const mockAgentPerformance = ref([
    {
      name: 'data_analysis_agent',
      avgTime: 2500,
      performance: 95,
      successRate: 98
    },
    {
      name: 'query_generation_agent', 
      avgTime: 3200,
      performance: 88,
      successRate: 92
    },
    {
      name: 'result_processing_agent',
      avgTime: 1800,
      performance: 92,
      successRate: 96
    }
  ])

  // Computed properties
  const totalExecutionTime = computed(() => {
    return mockAgentPerformance.value.reduce((total, agent) => total + agent.avgTime, 0)
  })

  const currentIteration = computed(() => {
    return mockSupervisorDecisions.value.length
  })

  const useSupervisor = ref(true)
  const isExecuting = ref(false)

  // Functions to simulate real-time updates
  const startMockExecution = () => {
    isExecuting.value = true
    // Simulate progress updates
    const interval = setInterval(() => {
      if (mockAgentProgress.value.progress_percentage < 100) {
        mockAgentProgress.value.progress_percentage += 10
      } else {
        isExecuting.value = false
        clearInterval(interval)
      }
    }, 1000)
  }

  const addMockSupervisorDecision = (decision: any) => {
    mockSupervisorDecisions.value.push({
      ...decision,
      timestamp: new Date().toISOString()
    })
  }

  const addMockAgentHandoff = (handoff: any) => {
    mockAgentHandoffs.value.push({
      ...handoff,
      timestamp: new Date().toISOString()
    })
  }

  // Create a mock enhanced stream response
  const createMockStreamResponse = (): StreamResponse => {
    const mockResponse = new StreamResponse({
      nodeOutputs: [
        {
          type: 'assistant:node:output',
          name: 'data_exploration_node',
          data: {
            content: 'Schema analysis complete',
            exploration_complete: true,
            tables_explored: ['customers', 'orders', 'products']
          },
          occurred_at: new Date().toISOString()
        }
      ],
      agentOutputs: [],
      supervisorDecisions: mockSupervisorDecisions.value,
      agentHandoffs: mockAgentHandoffs.value,
      currentAgent: 'query_generation_agent',
      agentProgress: mockAgentProgress.value
    })

    return mockResponse
  }

  return {
    // Mock data
    mockSupervisorDecisions,
    mockAgentHandoffs,
    mockAgentFlow,
    mockAgentProgress,
    mockObjectiveStatus,
    mockRetryHistory,
    mockAgentPerformance,

    // Computed properties
    totalExecutionTime,
    currentIteration,
    useSupervisor,
    isExecuting,

    // Functions
    startMockExecution,
    addMockSupervisorDecision,
    addMockAgentHandoff,
    createMockStreamResponse
  }
} 