<template>
  <div class="supervisor-container border-2 border-dashed border-gray-300 rounded-lg p-4 mb-4 bg-gray-50">
    <!-- Supervisor Header -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center space-x-3">
        <div class="supervisor-icon">
          <Settings class="h-6 w-6 text-gray-600" />
        </div>
        <div>
          <h3 class="font-semibold text-lg text-gray-700">Analysis Workflow</h3>
          <p class="text-sm text-gray-500">{{ currentActivity }}</p>
        </div>
      </div>
      
      <!-- Supervisor Status -->
      <div class="flex items-center space-x-2">
        <Loader2 v-if="isActive" class="h-5 w-5 animate-spin text-blue-500" />
        <CheckCircle v-else class="h-5 w-5 text-green-500" />
        <Badge variant="outline">{{ isActive ? 'Processing' : 'Ready' }}</Badge>
      </div>
    </div>

    <!-- Business View (Non-Debug Mode) -->
    <div v-if="!debugMode" class="business-view space-y-3">
      <div 
        v-for="(state, agentName) in agentStates" 
        :key="agentName"
        class="agent-status-card border rounded-lg bg-white"
      >
        <div class="p-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <!-- Status Icon -->
              <div class="status-icon">
                <div v-if="state.status === 'idle'" class="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
                  <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
                </div>
                <Loader2 v-else-if="state.status === 'running'" class="w-6 h-6 animate-spin text-blue-500" />
                <CheckCircle v-else-if="state.status === 'completed'" class="w-6 h-6 text-green-500" />
              </div>
              
              <!-- Agent Info -->
              <div>
                <h4 class="font-medium text-gray-900">{{ getAgentDisplayName(agentName) }}</h4>
                <p class="text-sm text-gray-500">{{ getAgentDescription(agentName) }}</p>
              </div>
            </div>
            
            <!-- Status Badge -->
            <Badge 
              :variant="state.status === 'completed' ? 'default' : state.status === 'running' ? 'secondary' : 'outline'"
              class="text-xs"
            >
              {{ state.status === 'idle' ? 'Pending' : state.status === 'running' ? 'Processing' : 'Complete' }}
            </Badge>
          </div>
        </div>
        
        <!-- Collapsible Details for Completed Agents -->
        <div v-if="state.status === 'completed' && getAgentCompletionDetails(agentName)" class="border-t">
          <Collapsible>
            <CollapsibleTrigger class="flex items-center justify-between w-full p-3 hover:bg-gray-50 text-left">
              <span class="text-sm font-medium text-gray-700">View Details</span>
              <ChevronDown class="h-4 w-4 text-gray-500 transition-transform data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent class="p-3 pt-0">
              <div class="bg-gray-50 rounded-lg p-3">
                <div class="text-xs text-gray-500 mb-2">
                  Completed at {{ formatTime(getAgentCompletionDetails(agentName)?.timestamp || '') }}
                </div>
                <div class="text-sm text-gray-700 whitespace-pre-wrap">
                  {{ getAgentCompletionDetails(agentName)?.content || 'No details available' }}
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      </div>
    </div>

    <!-- Debug View (Developer Mode) -->
    <div v-else class="debug-view">
      <!-- Agent Containers -->
      <div class="space-y-4">
        <AgentContainer
          v-for="(agentEvents, agentSource) in groupedAgentEvents"
          :key="agentSource"
          :agent-source="agentSource"
          :events="agentEvents"
          @start-new-question="$emit('start-new-question', $event)"
        />
      </div>

      <!-- Supervisor-specific Events -->
      <div v-if="supervisorSpecificEvents.length > 0" class="mt-4 space-y-2">
        <Collapsible v-model:open="showSupervisorEvents">
          <CollapsibleTrigger class="flex items-center justify-between w-full p-2 hover:bg-gray-100 rounded">
            <span class="text-sm font-medium">Supervisor Decisions ({{ supervisorSpecificEvents.length }} events)</span>
            <ChevronDown :class="{ 'rotate-180': showSupervisorEvents }" class="h-4 w-4 transition-transform" />
          </CollapsibleTrigger>
          <CollapsibleContent class="space-y-1 mt-2">
            <div v-for="event in sortedSupervisorEvents" :key="event.id" class="supervisor-event">
              <div class="flex items-start space-x-3 p-2 rounded bg-white border border-gray-200">
                <!-- Event Icon -->
                <div class="event-icon mt-0.5">
                  <ArrowRight v-if="event.title.includes('Handoff')" class="h-4 w-4 text-blue-500" />
                  <Brain v-else-if="event.type === 'tool_call'" class="h-4 w-4 text-purple-500" />
                  <CheckCircle v-else-if="event.type === 'tool_output'" class="h-4 w-4 text-green-500" />
                  <AlertCircle v-else-if="event.type === 'agent_output'" class="h-4 w-4 text-red-500" />
                  <MessageSquare v-else class="h-4 w-4 text-gray-400" />
                </div>
                
                <!-- Event Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between">
                    <p class="text-xs font-medium text-gray-700">{{ event.title }}</p>
                    <time class="text-xs text-gray-400">{{ formatTime(event.timestamp) }}</time>
                  </div>
                  <pre v-if="event.content" class="text-xs text-gray-500 mt-1 whitespace-pre-wrap">{{ formatContent(event.content) }}</pre>
                </div>
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>

      <!-- Agent Routing Visualization -->
      <div v-if="routingEvents.length > 0" class="mt-4">
        <h4 class="text-sm font-medium text-gray-700 mb-2">Agent Coordination Flow</h4>
        <div class="flex flex-wrap gap-2">
          <div 
            v-for="routing in routingEvents" 
            :key="routing.id"
            class="routing-item flex items-center space-x-2 px-3 py-1 bg-blue-100 rounded-full text-xs"
          >
            <ArrowRight class="h-3 w-3 text-blue-600" />
            <span class="text-blue-800">{{ routing.target_agent }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { 
  Settings, Loader2, CheckCircle, AlertCircle, ChevronDown,
  ArrowRight, Brain, MessageSquare
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import AgentContainer from './AgentContainer.vue'

interface ReasoningStep {
  id: string
  type: 'thought' | 'tool_call' | 'tool_output' | 'agent_output'
  title: string
  content: string | object
  status: 'running' | 'complete' | 'error'
  agentName?: string
  timestamp: string
  progress?: number
}

interface Props {
  events: ReasoningStep[]
  debugMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  debugMode: false
})

const showSupervisorEvents = ref(false)

// Business view: Track agent states (start/end only)
const agentStates = computed(() => {
  const states: Record<string, { status: 'idle' | 'running' | 'completed', startTime?: string, endTime?: string }> = {}
  const agentNames = ['DataAnalyst', 'QueryGenerator', 'ResultProcessor', 'Finalizer', 'ObjectiveEvaluator']
  
  // Initialize all agents as idle
  agentNames.forEach(name => {
    states[name] = { status: 'idle' }
  })
  
  // Process events to determine current states
  const events = props.events || []
  
  for (const event of events) {
    // Look for agent:start and agent:end events
    const eventType = event.type
    const agentName = event.agentName
    const eventTitle = event.title || ''
    const eventContent = typeof event.content === 'string' ? event.content : JSON.stringify(event.content)
    
    if (!agentName || !agentNames.includes(agentName)) continue
    
    if (eventTitle.includes('Started') || eventContent.includes('agent:start')) {
      states[agentName] = { 
        status: 'running', 
        startTime: event.timestamp 
      }
    } else if (eventTitle.includes('Completed') || eventContent.includes('agent:end')) {
      states[agentName] = { 
        ...states[agentName],
        status: 'completed', 
        endTime: event.timestamp 
      }
    }
  }
  
  return states
})

// Business view: Get display name for agents
const getAgentDisplayName = (agentName: string): string => {
  const nameMapping: Record<string, string> = {
    'DataAnalyst': 'Data Analysis',
    'QueryGenerator': 'Query Generation', 
    'ResultProcessor': 'Result Processing',
    'Finalizer': 'Final Report',
    'ObjectiveEvaluator': 'Quality Check'
  }
  return nameMapping[agentName] || agentName
}

// Business view: Get agent description
const getAgentDescription = (agentName: string): string => {
  const descriptions: Record<string, string> = {
    'DataAnalyst': 'Analyzing database structure and requirements',
    'QueryGenerator': 'Generating optimized SQL queries', 
    'ResultProcessor': 'Processing and analyzing results',
    'Finalizer': 'Creating comprehensive report',
    'ObjectiveEvaluator': 'Ensuring quality and completeness'
  }
  return descriptions[agentName] || 'Processing...'
}

// Business view: Get agent completion details from agent:end events
const getAgentCompletionDetails = (agentName: string) => {
  const events = props.events || []
  
  // Find the agent:end event for this agent
  const endEvent = events.find(event => {
    const eventTitle = event.title || ''
    const eventContent = typeof event.content === 'string' ? event.content : JSON.stringify(event.content)
    const matchesAgent = event.agentName === agentName
    const isEndEvent = eventTitle.includes('Completed') || eventContent.includes('agent:end')
    
    return matchesAgent && isEndEvent
  })
  
  if (!endEvent) return null
  
  // Extract meaningful content from the event
  let content = ''
  if (typeof endEvent.content === 'string') {
    content = endEvent.content
  } else if (typeof endEvent.content === 'object' && endEvent.content) {
    // Try to extract meaningful fields from the content object
    const contentObj = endEvent.content as any
    content = contentObj.content || 
              contentObj.description || 
              contentObj.summary ||
              JSON.stringify(contentObj, null, 2)
  }
  
  return {
    timestamp: endEvent.timestamp,
    content: content,
    title: endEvent.title
  }
}

// Group events by agent
const groupedAgentEvents = computed(() => {
  const agentSources = [
    'DataAnalyst', 'DataAnalysis', 'data_analyst', 
    'QueryGenerator', 'QueryGeneration', 'query_generator', 
    'ResultProcessor', 'ResultProcessing', 'result_processor', 
    'Finalizer', 'Finalization', 'finalizer', 
    'ObjectiveEvaluator', 'ObjectiveEvaluation', 'objective_evaluator'
  ]
  const grouped: Record<string, ReasoningStep[]> = {}
  const events = props.events || []
  
  // Find transfer events to determine when agents complete
  const transferEvents = events.filter(e => 
    e.title.includes('transferred') || 
    e.title.includes('Handoff') ||
    (typeof e.content === 'string' && e.content.includes('transferred'))
  ).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  
  agentSources.forEach(source => {
    // Get events that explicitly have this agent name
    const directEvents = events.filter(e => e.agentName === source)
    
    // Also get events that mention this agent in the title or content
    const relatedEvents = events.filter(e => {
      if (e.agentName === source) return false // Already included above
      
      const title = e.title.toLowerCase()
      const content = typeof e.content === 'string' ? e.content.toLowerCase() : JSON.stringify(e.content).toLowerCase()
      const sourceLower = source.toLowerCase()
      
      return title.includes(sourceLower) || content.includes(sourceLower)
    })
    
    let allEvents = [...directEvents, ...relatedEvents]
    
    if (allEvents.length > 0) {
      // Check if this agent was completed by a transfer event
      const agentCompletedByTransfer = transferEvents.some(transferEvent => {
        const transferContent = typeof transferEvent.content === 'string' ? transferEvent.content : JSON.stringify(transferEvent.content)
        const transferTitle = transferEvent.title
        
        // Check if this transfer event indicates the agent completed
        return (transferTitle.includes('transferred') || transferContent.includes('transferred')) &&
               (transferTitle.toLowerCase().includes(source.toLowerCase()) || 
                transferContent.toLowerCase().includes(source.toLowerCase()))
      })
      
      // If agent was completed by transfer, mark its running events as complete
      if (agentCompletedByTransfer) {
        allEvents = allEvents.map(event => {
          if (event.status === 'running') {
            return { ...event, status: 'complete' as const }
          }
          return event
        })
      }
      
      // Remove duplicates based on id, title and content
      const uniqueEvents = allEvents.filter((event, index, arr) => {
        return arr.findIndex(e => 
          e.id === event.id || (
            e.title === event.title && 
            JSON.stringify(e.content) === JSON.stringify(event.content) &&
            e.timestamp === event.timestamp
          )
        ) === index
      })
      grouped[source] = uniqueEvents
    }
  })
  
  return grouped
})

// Filter supervisor-specific events (decisions, handoffs, etc.)
const supervisorSpecificEvents = computed(() => 
  (props.events || []).filter(e => 
    e.agentName === 'supervisor' || 
    e.title.includes('Supervisor') ||
    e.title.includes('Decision') ||
    e.title.includes('Handoff')
  )
)

// Check if supervisor is currently active
const isActive = computed(() => {
  if (!props.events.length) return false
  
  const latestEvent = props.events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]
  
  return latestEvent.status === 'running'
})

// Get current activity description
const currentActivity = computed(() => {
  if (!props.events.length) return 'Waiting for tasks'
  
  const latestEvent = props.events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]
  
  if (latestEvent.type === 'thought' && latestEvent.title.includes('Handoff')) {
    return 'Coordinating agent handoff'
  } else if (latestEvent.title.includes('Decision')) {
    return 'Making routing decisions'
  } else if (latestEvent.status === 'running') {
    return latestEvent.title
  }
  
  return 'Monitoring workflow'
})

// Sort supervisor events by time
const sortedSupervisorEvents = computed(() => 
  [...supervisorSpecificEvents.value].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
)

// Extract routing events for visualization
const routingEvents = computed(() => 
  props.events
    .filter(e => e.title.includes('Handoff') || e.title.includes('Decision'))
    .map(e => ({
      ...e,
      target_agent: extractTargetAgent(e)
    }))
)

// Extract target agent from event data
const extractTargetAgent = (event: ReasoningStep) => {
  const content = typeof event.content === 'string' ? event.content : JSON.stringify(event.content)
  
  if (content.includes('DataAnalyst') || content.includes('data_analyst')) return 'Data Analyst'
  if (content.includes('QueryGenerator') || content.includes('query_generator')) return 'Query Generator'
  if (content.includes('ResultProcessor') || content.includes('result_processor')) return 'Result Processor'
  if (content.includes('Finalizer') || content.includes('finalizer')) return 'Finalizer'
  if (content.includes('ObjectiveEvaluator') || content.includes('objective_evaluator')) return 'Objective Evaluator'
  
  return 'Unknown Agent'
}

// Format time
const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString()
}

// Format content for display
const formatContent = (content: string | object) => {
  if (typeof content === 'string') {
    return content
  }
  return JSON.stringify(content, null, 2)
}

// Get status color
const getStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'text-blue-600'
    case 'complete': return 'text-green-600'
    case 'error': return 'text-red-600'
    default: return 'text-gray-600'
  }
}
</script>

<style scoped>
.supervisor-container {
  @apply transition-all duration-200;
}

.supervisor-event {
  @apply transition-all duration-150 hover:shadow-sm;
}

.routing-item {
  @apply transition-all duration-150 hover:bg-blue-200;
}

.business-view .agent-status-card {
  @apply transition-all duration-200 hover:shadow-sm;
}

.business-view .agent-status-card:hover {
  @apply border-gray-300;
}

.business-view .status-icon {
  @apply flex-shrink-0;
}
</style> 