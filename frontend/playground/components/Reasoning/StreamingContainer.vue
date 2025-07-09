<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import SupervisorContainer from './SupervisorContainer.vue'
import { CheckCircle } from 'lucide-vue-next'

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
  events?: ReasoningStep[]
  finalAnswer?: string
}

const props = withDefaults(defineProps<Props>(), {
  events: () => [],
  finalAnswer: ''
})

const emit = defineEmits(['start-new-question'])

const showOtherEvents = ref(false)

// Filter out system events that don't belong to any agent or supervisor
const otherEvents = computed(() => {
  const agentNames = ['DataAnalyst', 'QueryGenerator', 'ResultProcessor', 'Finalizer', 'ObjectiveEvaluator', 'data_analyst', 'query_generator', 'result_processor', 'finalizer', 'objective_evaluator']
  const filtered = (props.events || []).filter(e => 
    !e.agentName && 
    !e.title.includes('Supervisor') &&
    !e.title.includes('Decision') &&
    !e.title.includes('Handoff') &&
    !agentNames.includes(e.agentName || '')
  )
  
  // Remove duplicates from other events too
  return filtered.filter((event, index, arr) => {
    return arr.findIndex(e => 
      e.title === event.title && 
      JSON.stringify(e.content) === JSON.stringify(event.content)
    ) === index
  })
})

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

<template>
  <div class="streaming-container space-y-4">
    <!-- Supervisor Container (houses all agent containers) -->
    <SupervisorContainer 
      v-if="events.length > 0"
      :events="events"
      @start-new-question="$emit('start-new-question', $event)"
    />

    <!-- Final Answer Section -->
    <div v-if="finalAnswer" class="final-answer bg-green-50 border border-green-200 rounded-lg p-4">
      <div class="flex items-center space-x-2 mb-2">
        <CheckCircle class="h-5 w-5 text-green-600" />
        <h3 class="text-sm font-semibold text-green-800">Final Answer</h3>
      </div>
      <pre class="text-sm text-green-700 whitespace-pre-wrap">{{ finalAnswer }}</pre>
    </div>

    <!-- System Events (non-agent, non-supervisor) -->
    <div v-if="otherEvents.length > 0" class="other-events">
      <Collapsible v-model:open="showOtherEvents">
        <CollapsibleTrigger class="flex items-center justify-between w-full p-3 border rounded hover:bg-gray-50">
          <span class="text-sm font-medium">System Events ({{ otherEvents.length }})</span>
          <ChevronDown :class="{ 'rotate-180': showOtherEvents }" class="h-4 w-4 transition-transform" />
        </CollapsibleTrigger>
        <CollapsibleContent class="mt-2 space-y-2">
          <div v-for="event in otherEvents" :key="event.timestamp" class="p-3 border rounded bg-gray-50">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium">{{ event.title }}</span>
              <time class="text-xs text-gray-500">{{ formatTime(event.timestamp) }}</time>
            </div>
                         <pre v-if="event.content" :class="getStatusColor(event.status)" class="text-sm mt-1 whitespace-pre-wrap">{{ formatContent(event.content) }}</pre>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  </div>
</template>

<style scoped>
.streaming-container {
  @apply w-full;
}

.other-events {
  @apply transition-all duration-200;
}
</style> 