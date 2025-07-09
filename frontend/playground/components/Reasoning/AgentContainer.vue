<template>
  <div class="agent-container border rounded-lg p-4 mb-4">
    <!-- Agent Header -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center space-x-3">
        <!-- Agent Icon -->
        <div class="agent-icon">
          <Database v-if="agentSource === 'data_analyst' || agentSource === 'DataAnalyst' || agentSource === 'DataAnalysis'" class="h-6 w-6 text-blue-500" />
          <Code v-else-if="agentSource === 'query_generator' || agentSource === 'QueryGenerator' || agentSource === 'QueryGeneration'" class="h-6 w-6 text-green-500" />
          <BarChart3 v-else-if="agentSource === 'result_processor' || agentSource === 'ResultProcessor' || agentSource === 'ResultProcessing'" class="h-6 w-6 text-purple-500" />
          <FileText v-else-if="agentSource === 'finalizer' || agentSource === 'Finalizer' || agentSource === 'Finalization'" class="h-6 w-6 text-orange-500" />
          <CheckCircle v-else-if="agentSource === 'objective_evaluator' || agentSource === 'ObjectiveEvaluator' || agentSource === 'ObjectiveEvaluation'" class="h-6 w-6 text-indigo-500" />
          <Settings v-else-if="agentSource === 'supervisor' || agentSource === 'Supervisor'" class="h-6 w-6 text-gray-500" />
          <Cpu v-else class="h-6 w-6 text-gray-400" />
        </div>
        
        <!-- Agent Name and Status -->
        <div>
          <h3 class="font-semibold text-lg">{{ agentDisplayName }}</h3>
          <p class="text-sm text-gray-500">{{ currentStageDisplay }}</p>
        </div>
      </div>
      
      <!-- Agent Status Indicator -->
      <div class="flex items-center space-x-2">
        <div class="status-indicator">
          <Loader2 v-if="agentStatus === 'running'" class="h-5 w-5 animate-spin text-blue-500" />
          <CheckCircle v-else-if="agentStatus === 'completed'" class="h-5 w-5 text-green-500" />
          <AlertCircle v-else-if="agentStatus === 'error'" class="h-5 w-5 text-red-500" />
          <Clock v-else class="h-5 w-5 text-gray-400" />
        </div>
        <Badge :variant="statusVariant">{{ agentStatus }}</Badge>
      </div>
    </div>

    <!-- Progress Bar -->
    <div v-if="currentProgress !== null" class="mb-3">
      <div class="flex justify-between text-sm text-gray-600 mb-1">
        <span>{{ latestProgressMessage }}</span>
        <span>{{ currentProgress }}%</span>
      </div>
      <Progress :value="currentProgress" class="h-2" />
    </div>

    <!-- Agent Events Timeline -->
    <div class="space-y-2">
      <Collapsible v-model:open="showDetails">
        <CollapsibleTrigger class="flex items-center justify-between w-full p-2 hover:bg-gray-50 rounded">
          <span class="text-sm font-medium">Activity Details ({{ events.length }} events)</span>
          <ChevronDown :class="{ 'rotate-180': showDetails }" class="h-4 w-4 transition-transform" />
        </CollapsibleTrigger>
        <CollapsibleContent class="space-y-2 mt-2">
          <div v-for="event in sortedEvents" :key="event.id" class="event-item">
            <div class="flex items-start space-x-3 p-3 rounded border-l-4" :class="getEventBorderClass(event)">
              <!-- Event Icon -->
              <div class="event-icon mt-0.5">
                <CheckCircle v-if="event.type === 'tool_output'" class="h-4 w-4 text-green-500" />
                <AlertCircle v-else-if="event.status === 'error'" class="h-4 w-4 text-red-500" />
                <AlertTriangle v-else-if="event.type === 'tool_call'" class="h-4 w-4 text-yellow-500" />
                <Play v-else-if="event.type === 'thought'" class="h-4 w-4 text-blue-500" />
                <Square v-else-if="event.type === 'agent_output'" class="h-4 w-4 text-gray-500" />
                <Zap v-else-if="event.type === 'tool_call'" class="h-4 w-4 text-purple-500" />
                <MessageSquare v-else class="h-4 w-4 text-gray-400" />
              </div>
              
              <!-- Event Content -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <p class="text-sm font-medium text-gray-900">{{ event.title }}</p>
                  <time class="text-xs text-gray-500">{{ formatTime(event.timestamp) }}</time>
                </div>
                                 <pre v-if="event.content" class="text-sm text-gray-600 mt-1 whitespace-pre-wrap">{{ formatContent(event.content) }}</pre>
                                 
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>

    <!-- Agent Output (if any) -->
    <div v-if="agentOutput" class="mt-4 p-4 bg-gray-50 rounded">
      <h4 class="font-medium mb-2">Output</h4>
      <component 
        :is="getOutputComponent()" 
        :node="agentOutput" 
        @start-new-question="$emit('start-new-question', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { 
  Database, Code, BarChart3, FileText, CheckCircle, Settings, Cpu,
  Loader2, AlertCircle, Clock, ChevronDown, Play, Square, Zap, 
  MessageSquare, AlertTriangle
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

// Import existing components
import DataExploration from '~/components/Node/DataExploration.vue'
import GenerateQuery from '~/components/Node/GenerateQuery.vue'
import AnalyseExecutionResults from '~/components/Node/AnalyseExecutionResults.vue'
import GenerateFinalAnswer from '~/components/Node/GenerateFinalAnswer.vue'
import SupervisorEvent from '~/components/Node/SupervisorEvent.vue'
import Fallback from '~/components/Node/Fallback.vue'

interface ReasoningStep {
  id: string
  type: 'thought' | 'tool_call' | 'tool_output' | 'agent_output'
  title: string
  content: string | object
  status: 'running' | 'complete' | 'error'
  agentName?: string
  timestamp: string
  progress?: number // Added for progress events
}

interface Props {
  agentSource: string
  events: ReasoningStep[]
  agentOutput?: any
}

const props = defineProps<Props>()
const emit = defineEmits(['start-new-question'])

const showDetails = ref(false)

// Agent display mapping
const agentDisplayNames = {
  'data_analyst': 'Data Analyst',
  'DataAnalyst': 'Data Analyst', 
  'DataAnalysis': 'Data Analyst',
  'query_generator': 'Query Generator',
  'QueryGenerator': 'Query Generator',
  'QueryGeneration': 'Query Generator',
  'result_processor': 'Result Processor',
  'ResultProcessor': 'Result Processor',
  'ResultProcessing': 'Result Processor',
  'finalizer': 'Finalizer',
  'Finalizer': 'Finalizer',
  'Finalization': 'Finalizer',
  'objective_evaluator': 'Objective Evaluator',
  'ObjectiveEvaluator': 'Objective Evaluator',
  'ObjectiveEvaluation': 'Objective Evaluator',
  'supervisor': 'Supervisor',
  'Supervisor': 'Supervisor',
  'system': 'System'
}

const agentDisplayName = computed(() => 
  agentDisplayNames[props.agentSource as keyof typeof agentDisplayNames] || props.agentSource
)

// Compute agent status based on events
const agentStatus = computed(() => {
  if (!props.events.length) return 'pending'
  
  const hasError = props.events.some(e => e.status === 'error')
  if (hasError) return 'error'
  
  // Check for explicit completion signals
  const hasComplete = props.events.some(e => e.status === 'complete')
  const hasRunning = props.events.some(e => e.status === 'running')
  
  // Check for transfer/handoff events that indicate completion
  const hasTransferOut = props.events.some(e => 
    e.title.includes('transferred') || 
    e.title.includes('Handoff') ||
    (typeof e.content === 'string' && e.content.includes('transferred'))
  )
  
  // Check for progress events that reached 100%
  const hasFullProgress = props.events.some(e => e.progress === 100)
  
  // Agent is completed if:
  // 1. Has complete events and no running events, OR
  // 2. Has been transferred out, OR  
  // 3. Has reached 100% progress
  if ((hasComplete && !hasRunning) || hasTransferOut || hasFullProgress) {
    return 'completed'
  }
  
  if (hasRunning) return 'running'
  if (hasComplete) return 'completed'
  
  return 'pending'
})

const statusVariant = computed(() => {
  switch (agentStatus.value) {
    case 'completed': return 'default'
    case 'running': return 'secondary'
    case 'error': return 'destructive'
    default: return 'outline'
  }
})

// Get current progress (simulate progress based on event types)
const currentProgress = computed(() => {
  if (!props.events.length) return null
  
  // Look for progress events with actual progress values
  const progressEvents = props.events
    .filter(e => e.progress !== undefined)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  
  if (progressEvents.length > 0) {
    return progressEvents[0].progress || 0
  }
  
  // Fallback: calculate based on completed vs total steps
  const totalSteps = props.events.length
  const completedSteps = props.events.filter(e => e.status === 'complete').length
  
  if (totalSteps === 0) return null
  return Math.round((completedSteps / totalSteps) * 100)
})

const latestProgressMessage = computed(() => {
  // Look for the most recent progress event first
  const progressEvents = props.events
    .filter(e => e.progress !== undefined)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  
  if (progressEvents.length > 0) {
    return progressEvents[0].title
  }
  
  // Fallback to latest event
  const latestEvent = props.events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]
  
  return latestEvent ? latestEvent.title : ''
})

// Get current stage display
const currentStageDisplay = computed(() => {
  const latestEvent = props.events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]
  
  if (!latestEvent) return 'Ready'
  
  // Map event types to stage names
  switch (latestEvent.type) {
    case 'thought': return 'Thinking'
    case 'tool_call': return 'Using Tools'
    case 'tool_output': return 'Processing Results'
    case 'agent_output': return 'Generating Output'
    default: return 'Processing'
  }
})

// Sort events by time
const sortedEvents = computed(() => 
  [...props.events].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
)

// Event styling
const getEventBorderClass = (event: ReasoningStep) => {
  switch (event.status) {
    case 'complete': return 'border-l-green-500 bg-green-50'
    case 'error': return 'border-l-red-500 bg-red-50'
    case 'running': return 'border-l-blue-500 bg-blue-50'
    default: return 'border-l-gray-500 bg-gray-50'
  }
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

// Get appropriate output component
const getOutputComponent = () => {
  const source = props.agentSource.toLowerCase()
  
  if (source.includes('data_analyst') || source.includes('dataanalyst') || source.includes('dataanalysis')) {
    return DataExploration
  }
  if (source.includes('query_generator') || source.includes('querygenerator') || source.includes('querygeneration')) {
    return GenerateQuery
  }
  if (source.includes('result_processor') || source.includes('resultprocessor') || source.includes('resultprocessing')) {
    return AnalyseExecutionResults
  }
  if (source.includes('finalizer') || source.includes('finalization') || 
      source.includes('objective_evaluator') || source.includes('objectiveevaluator') || source.includes('objectiveevaluation')) {
    return GenerateFinalAnswer
  }
  if (source.includes('supervisor')) {
    return SupervisorEvent
  }
  
  return Fallback
}
</script>

<style scoped>
.agent-container {
  @apply transition-all duration-200 hover:shadow-md;
}

.event-item {
  @apply transition-all duration-150 hover:shadow-sm;
}
</style> 