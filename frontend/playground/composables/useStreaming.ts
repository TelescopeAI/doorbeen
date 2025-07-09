import { ref, onMounted, onUnmounted } from 'vue'
import { SSEService } from '~/core/streaming/sse'
import { useEventRouter } from './useEventRouter'
import { useStreamState } from './useStreamState'
import { getAPIServerURL } from '~/composables/server'

export function useStreaming() {
  const streamState = useStreamState()
  const eventRouter = useEventRouter(streamState)
  
  const sseService = ref<SSEService | null>(null)
  const isConnected = ref(false)
  
  const initializeSSE = (url: string, options: any) => {
    // No authentication required for assistants endpoint
    sseService.value = new SSEService(url, '', options) // Pass empty token since no auth needed
    
    // Set up message handling with the event router
    sseService.value.onMessage((event) => {
      console.log('📡 SSE message received:', event)
      eventRouter.routeEvent(event)
    })
    
    return sseService.value
  }
  
  const startStream = async (params: { 
    threadId: string, 
    message: string,
    modelParams?: any,
    connectionDetails?: any,
    useSupervisor?: boolean,
    agentConfig?: any 
  }) => {
    try {
      streamState.resetState()
      streamState.startStream()
      
      const url = `${getAPIServerURL()}/api/v1/assistants`
      const requestBody = {
        question: params.message,
        model: params.modelParams || {},
        connection: params.connectionDetails || {},
        stream: true,
        ...(params.threadId && { thread_id: params.threadId }),
        ...(params.useSupervisor !== undefined && { use_supervisor: params.useSupervisor }),
        ...(params.agentConfig && { agent_config: params.agentConfig }),
      }
      
      const service = initializeSSE(url, { body: requestBody })
      if (!service) {
        throw new Error('Failed to initialize SSE service')
      }
      
      await service.connect()
      isConnected.value = true
      
      console.log('🚀 Stream started for thread:', params.threadId)
      
    } catch (error) {
      console.error('Failed to start stream:', error)
      streamState.setError(`Failed to start stream: ${error}`)
      isConnected.value = false
    }
  }
  
  const stopStream = () => {
    if (sseService.value) {
      sseService.value.disconnect()
      sseService.value = null
      isConnected.value = false
      streamState.endStream()
      console.log('🛑 Stream stopped')
    }
  }
  
  // Auto-cleanup on unmount
  if (process.client) {
    onUnmounted(() => {
      stopStream()
    })
  }
  
  return {
    // State from streamState
    state: streamState.state,
    hasSteps: streamState.hasSteps,
    hasError: streamState.hasError,
    currentStepCount: streamState.currentStepCount,
    
    // Actions
    startStream,
    stopStream,
    
    // SSE connection state
    isConnected,
    
    // Direct access to state manager for advanced usage
    stateManager: streamState,
    
    // Direct access to event router for custom handlers
    eventRouter,
  }
} 