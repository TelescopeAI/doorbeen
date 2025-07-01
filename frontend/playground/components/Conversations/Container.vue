<script setup lang="ts">
import { useElementSize } from '@vueuse/core'; // Assuming you are using vueuse for element size
import { ConversationState } from '../../types/conversations'; // Add this import
import { Button } from '~/components/ui/button';
import { useClipboard } from '@vueuse/core'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog as ShadDialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Copy, Database, Bot, Loader2, Settings, ChevronDown, Plus, Minus } from 'lucide-vue-next';
import DatabaseSelector from '@/components/Database/Selector.vue'
import ModelSelector from '@/components/Model/Selector.vue'
import { computed, watch } from 'vue'
import { Transition } from 'vue'


// Define component props
const props = defineProps({
  conversations: {
    type: Array,
    default: () => []
  },
  isThinking: {
    type: Boolean,
    default: false
  },
  currentMessage: {
    type: Object,
    default: null
  }
});
const emit = defineEmits(['retry', 'start-new-question', 'mode-changed']);

// Reactive variables
const lastMessage = ref(null);
const lastMessageErrored = ref(false);
// Watch the last message for changes and update the error context
watchEffect(() => {
  if (props.conversations.length > 0) {

    lastMessage.value = props.conversations[props.conversations.length - 1];
    lastMessageErrored.value = lastMessage.value.state === ConversationState.ERROR;
  } else {
    lastMessage.value = null;
    lastMessageErrored.value = false;
  }

  console.log("watchEffect triggered:");
  console.log("Last message:", lastMessage.value);
  console.log("Last message context:", lastMessage.value?.state);
  console.log("Is error?", lastMessageErrored.value);
}, {deep: true});

// Processing text logic
const processingTexts = ["Fetching Data", "Analysing", "Thinking"];
const currentProcessingText = ref('Analyzing your question...')

let intervalId = null;

// Watch for changes in isThinking and update the processing text
watchEffect(() => {
  if (props.isThinking) {
    let i = 0;
    intervalId = setInterval(() => {
      currentProcessingText.value = processingTexts[i];
      i = (i + 1) % processingTexts.length;
    }, 3000);
  } else {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }
});

// Clean up interval on component unmount
onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId);
  }
});

// Initialize total stats with default values to prevent undefined errors
const total_stats = ref({
  total_tokens: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  total_cost: 0
});

watchEffect(() => {
  // Recalculate total stats whenever conversations change
  total_stats.value = props.conversations.reduce((acc, conversation) => {
    if (conversation.stats) {
      acc.total_tokens += conversation.stats.total_tokens || 0;
      acc.prompt_tokens += conversation.stats.prompt_tokens || 0;
      acc.completion_tokens += conversation.stats.completion_tokens || 0;
      acc.total_cost += conversation.stats.total_cost || 0;
    }
    return acc;
  }, { total_tokens: 0, prompt_tokens: 0, completion_tokens: 0, total_cost: 0 });
});

// Layout logic using vueuse/core to get element size
const totals_window = ref(null);
const { width } = useElementSize(totals_window);
const isMobileMode = ref(false);
const layout = ref('horizontal');

watchEffect(() => {
  isMobileMode.value = width.value < 650;
  layout.value = isMobileMode.value ? 'vertical' : 'horizontal';
});

const get_fieldset_class = (state: string) => {
  const is_error = state === 'ERROR';
  const base_classes = "max-w-full px-4 pt-2 py-3 inline-size-min rounded-md border bg-surface-0 dark:bg-surface-900 " +
                       "text-surface-700 dark:text-surface-0/80"
  const border_class = is_error ? "border-red-500" : "border-surface-200 dark:border-surface-700";
  return `${base_classes} ${border_class}`;
}
const retry_request = () => {
  console.log("Retrying... [ConversationsContainer]");
  emit('retry');
}
import { useUser } from '@clerk/vue'

const { isLoaded, user } = useUser()
const user_profile_image = ref(user.value?.imageUrl)
const copied_content = ref('')
const { text, copy, copied, isSupported } = useClipboard({ copied_content })
const is_settings_visible = ref(false)

const handleStartNewQuestion = (question: string) => {
  console.log('Conversations Container received start-new-question:', question);
  emit('start-new-question', question);
};

// Helper function to get step title from node name
const getStepTitle = (nodeName: string) => {
  if(nodeName === 'init_assistant'){
    return 'Determining if this is a new question or a followup'
  }
  else if(nodeName === 'qa_grade_node'){
    return 'Grading the quality of the question'
  }
  else if(nodeName === 'supervisor_node'){
    return 'Multi-agent supervisor coordinating analysis'
  }
  else if(nodeName === 'supervisor_initialized'){
    return 'Supervisor initialized - Multi-agent coordination starting'
  }
  else if(nodeName === 'agent_handoff'){
    return 'Supervisor delegating task to specialized agent'
  }
  else if(nodeName === 'agent_completed'){
    return 'Agent completed task - returning to supervisor'
  }
  else if(nodeName === 'agent_failed'){
    return 'Agent encountered error - supervisor handling retry'
  }
  else if(nodeName === 'agent_retry'){
    return 'Supervisor retrying failed agent with different strategy'
  }
  else if(nodeName === 'supervisor_completed'){
    return 'Multi-agent coordination completed successfully'
  }
  else if(nodeName === 'data_analysis'){
    return 'Data Analysis Agent exploring database structure'
  }
  else if(nodeName === 'query_generation'){
    return 'Query Generation Agent creating SQL queries'
  }
  else if(nodeName === 'result_processing'){
    return 'Result Processing Agent analyzing query results'
  }
  else if(nodeName === 'objective_evaluation'){
    return 'Objective Evaluation Agent checking if goals are met'
  }
  else if(nodeName === 'finalization'){
    return 'Finalization Agent preparing final response'
  }
  else if(nodeName === 'supervisor_start'){
    return 'Supervisor initializing multi-agent coordination'
  }
  else if(nodeName === 'supervisor_completion'){
    return 'Supervisor completing multi-agent coordination'
  }
  else if(nodeName === 'enrich_input_node'){
    return 'Enriching the question with more context'
  }
  else if(nodeName === 'input_followup_node'){
    return 'Processing followup question based on the previous conversation'
  }
  else if(nodeName === 'interpret_input_node'){
    return 'Understanding the question and forming the objective'
  }
  else if(nodeName === 'data_exploration_node'){
    return 'Exploring the database to understand the available data'
  }
  else if(nodeName === 'determine_input_objectives'){
    return 'Clarifying the input objectives and determining what data to gather'
  }
  else if(nodeName === 'generate_sql_query_node'){
    return 'Generating the SQL Query to fetch the data'
  }
  else if(nodeName === 'execute_sql_query_node'){
    return 'Executing the SQL Query'
  }
  else if(nodeName === 'handle_execution_failure_node'){
    return 'Trying to fix the generated query'
  }
  else if(nodeName === 'process_results_node'){
    return 'Analysing the data to find insights'
  }
  else if(nodeName === 'query_visualization_node'){
    return 'Planning data visualization and charts'
  }
  else if(nodeName === 'final_answer_node'){
    return 'Generating Final Answer'
  }
  else if(nodeName === 'stream_termination'){
    return 'Analysis Stream Status'
  }
  else {
    return 'Processing...'
  }
};

// Database and Model configuration status
const dbConfigAvailable = ref(false)
const modelConfigAvailable = ref(false)

// Mode selection state
const currentMode = ref<'linear' | 'supervisor'>('linear')

// Dialog states
const isDatabaseDialogOpen = ref(false)
const isModelDialogOpen = ref(false)

// Event handlers for dialog closing
const handleDBConfigSaved = () => {
  // Add a small delay to sync with toast appearance
  setTimeout(() => {
    isDatabaseDialogOpen.value = false
    checkConfigStatus() // Refresh configuration status
  }, 500)
}

const handleModelConfigSaved = () => {
  // Add a small delay to sync with toast appearance
  setTimeout(() => {
    isModelDialogOpen.value = false
    checkConfigStatus() // Refresh configuration status
  }, 500)
}

// Check configuration status
const checkConfigStatus = () => {
  // Check for existing database configuration
  const storedDbConfig = localStorage.getItem('db-config')
  if (storedDbConfig) {
    try {
      const dbConfig = JSON.parse(storedDbConfig)
      dbConfigAvailable.value = !!(dbConfig && Object.keys(dbConfig).length > 0)
    } catch (error) {
      console.error('Error parsing stored database config:', error)
      dbConfigAvailable.value = false
    }
  } else {
    dbConfigAvailable.value = false
  }

  // Check for existing model configuration
  const storedModelConfig = localStorage.getItem('model-config')
  if (storedModelConfig) {
    try {
      const modelConfig = JSON.parse(storedModelConfig)
      modelConfigAvailable.value = !!(modelConfig && Object.keys(modelConfig).length > 0)
    } catch (error) {
      console.error('Error parsing stored model config:', error)
      modelConfigAvailable.value = false
    }
  } else {
    modelConfigAvailable.value = false
  }
}

// Mode selection functions
const loadModeConfig = () => {
  const storedMode = localStorage.getItem('analysis-mode')
  if (storedMode && (storedMode === 'linear' || storedMode === 'supervisor')) {
    currentMode.value = storedMode as 'linear' | 'supervisor'
  } else {
    currentMode.value = 'linear' // Default to linear
  }
}

const setMode = (mode: 'linear' | 'supervisor') => {
  currentMode.value = mode
  localStorage.setItem('analysis-mode', mode)
  console.log('Mode changed to:', mode)
  emit('mode-changed', mode)
}

const getModeDisplayName = (mode: 'linear' | 'supervisor') => {
  return mode === 'linear' ? 'Linear' : 'Supervisor'
}

const getModeDescription = (mode: 'linear' | 'supervisor') => {
  return mode === 'linear' 
    ? 'Sequential step-by-step analysis'
    : 'Multi-agent coordinated analysis'
}

// Check configuration status on mount
onMounted(() => {
  checkConfigStatus()
  loadModeConfig()
  
  // Listen for localStorage changes to update status
  window.addEventListener('storage', checkConfigStatus)
})

// Clean up event listener on unmount
onUnmounted(() => {
  window.removeEventListener('storage', checkConfigStatus)
})

// Watch the current message for real-time updates
watchEffect(() => {
  // This ensures reactivity is maintained for nested properties
  if (props.currentMessage?.stream?.nodeOutputs) {
    // Access the property to ensure Vue tracks it
    props.currentMessage.stream.nodeOutputs.length;
  }
});

// Computed property to track nodeOutputs reactively
const currentNodeOutputs = computed(() => {
  return props.currentMessage?.stream?.nodeOutputs || [];
});

// Computed property to check if we should show detailed progress
const shouldShowDetailedProgress = computed(() => {
  return props.isThinking && 
         props.currentMessage && 
         props.currentMessage.stream && 
         currentNodeOutputs.value.length > 0;
});

// Computed property for the current step
const currentStep = computed(() => {
  const outputs = currentNodeOutputs.value;
  return outputs.length > 0 ? outputs[outputs.length - 1] : null;
});

// Additional debugging for props changes
watch(() => props.currentMessage, (newMessage, oldMessage) => {
  // Watch for currentMessage changes (removed debug logs)
}, { deep: true });

watch(() => props.isThinking, (newThinking, oldThinking) => {
  // Watch for isThinking changes (removed debug logs)
});

// Track minimized messages
const minimizedMessages = ref<Set<string>>(new Set())

// Function to toggle minimize state for a message
const toggleMinimize = (messageId: string) => {
  if (minimizedMessages.value.has(messageId)) {
    minimizedMessages.value.delete(messageId)
  } else {
    minimizedMessages.value.add(messageId)
  }
}

// Function to check if a message is minimized
const isMinimized = (messageId: string) => {
  return minimizedMessages.value.has(messageId)
}

// Function to minimize all messages
const minimizeAll = () => {
  props.conversations.forEach(conversation => {
    minimizedMessages.value.add(conversation.id)
  })
}

// Function to expand all messages
const expandAll = () => {
  minimizedMessages.value.clear()
}

// Computed property to check if all messages are minimized
const allMinimized = computed(() => {
  return props.conversations.length > 0 && props.conversations.every(conversation => 
    minimizedMessages.value.has(conversation.id)
  )
})

// Computed property to check if any messages are minimized
const anyMinimized = computed(() => {
  return minimizedMessages.value.size > 0
})

</script>



<template>
  <div class="conversations-container flex flex-col conversation-dense max-w-full text-density-high">
    <!-- Database and Model Selector Buttons -->
    <div class="flex gap-dense mb-2">
      <!-- Database Selector Button -->
      <ShadDialog v-model:open="isDatabaseDialogOpen">
        <DialogTrigger as-child>
          <Button variant="outline" class="flex items-center gap-2">
            <Database class="w-4 h-4" />
            <span class="hidden sm:inline">Database</span>
            <span v-if="dbConfigAvailable" class="text-green-600 dark:text-green-400 text-xs">✓</span>
            <span v-else class="text-red-600 dark:text-red-400 text-xs">✕</span>
          </Button>
        </DialogTrigger>
        <DialogContent class="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Database Configuration</DialogTitle>
            <DialogDescription>
              Configure your database connection settings.
            </DialogDescription>
          </DialogHeader>
          <DatabaseSelector @configSaved="handleDBConfigSaved" />
        </DialogContent>
      </ShadDialog>

      <!-- Model Selector Button -->
      <ShadDialog v-model:open="isModelDialogOpen">
        <DialogTrigger as-child>
          <Button variant="outline" class="flex items-center gap-2">
            <Bot class="w-4 h-4" />
            <span class="hidden sm:inline">Model</span>
            <span v-if="modelConfigAvailable" class="text-green-600 dark:text-green-400 text-xs">✓</span>
            <span v-else class="text-red-600 dark:text-red-400 text-xs">✕</span>
          </Button>
        </DialogTrigger>
        <DialogContent class="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Model Configuration</DialogTitle>
            <DialogDescription>
              Configure your LLM settings and API credentials.
            </DialogDescription>
          </DialogHeader>
          <ModelSelector @configSaved="handleModelConfigSaved" />
        </DialogContent>
      </ShadDialog>

      <!-- Mode Selector Dropdown -->
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" class="flex items-center gap-2">
            <Settings class="w-4 h-4" />
            <span class="hidden sm:inline">Mode</span>
            <span class="text-xs text-blue-600 dark:text-blue-400">{{ getModeDisplayName(currentMode) }}</span>
            <ChevronDown class="w-3 h-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <DropdownMenuItem 
            @click="setMode('linear')"
            class="cursor-pointer"
            :class="{ 'bg-blue-50 dark:bg-blue-900/20': currentMode === 'linear' }"
          >
            <div class="flex flex-col">
              <div class="flex items-center gap-2">
                <span class="font-medium">Linear</span>
                <span v-if="currentMode === 'linear'" class="text-blue-600 dark:text-blue-400 text-xs">✓</span>
              </div>
              <span class="text-xs text-muted-foreground">{{ getModeDescription('linear') }}</span>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem 
            @click="setMode('supervisor')"
            class="cursor-pointer"
            :class="{ 'bg-blue-50 dark:bg-blue-900/20': currentMode === 'supervisor' }"
          >
            <div class="flex flex-col">
              <div class="flex items-center gap-2">
                <span class="font-medium">Supervisor</span>
                <span v-if="currentMode === 'supervisor'" class="text-blue-600 dark:text-blue-400 text-xs">✓</span>
              </div>
              <span class="text-xs text-muted-foreground">{{ getModeDescription('supervisor') }}</span>
            </div>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      
      <!-- Minimize All / Expand All Button (only show when there are conversations) -->
      <Button 
        v-if="props.conversations.length > 0"
        variant="outline" 
        size="sm"
        @click="allMinimized ? expandAll() : minimizeAll()"
        class="flex items-center gap-2"
        :title="allMinimized ? 'Expand all messages' : 'Minimize all messages'"
      >
        <Plus v-if="allMinimized" class="w-4 h-4" />
        <Minus v-else class="w-4 h-4" />
        <span class="hidden sm:inline">{{ allMinimized ? 'Expand All' : 'Minimize All' }}</span>
      </Button>
    </div>
<!--    <Panel header="Summary Usage" toggleable collapsed ref="totals_window">-->
<!--      <Splitter class="w-full border-2" :layout="layout">-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit text-gray-500">Total Tokens</p>-->
<!--            <p class="font-semibold"> {{total_stats.total_tokens}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="w-full flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit text-gray-500">Input Tokens</p>-->
<!--            <p class="font-semibold"> {{total_stats.prompt_tokens}}</p>-->

<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit text-gray-500">Output Tokens</p>-->
<!--            <p class="font-semibold"> {{total_stats.completion_tokens}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center min-w-[25%]">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit w-fit text-gray-500 ">Total Cost</p>-->
<!--            <p class="font-semibold">$ {{total_stats.total_cost.toFixed(10)}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--      </Splitter>-->
<!--    </Panel>-->
    <Card v-for="conversation in conversations" :key="conversation.id"
          class="max-w-[80vw] overflow-x-clip"
          :class="get_fieldset_class(conversation.state)">
      <CardContent class="p-6">
        <div class="w-full min-w-0 flex flex-col gap-y-5 overflow-x-auto justify-between items-start">
          <div class="w-full min-w-0 flex flex-row justify-between items-center gap-x-6">
            <p class="text-md font-semibold overflow-x-auto min-w-0"> {{ conversation.message }}</p>
            <div class="flex items-center gap-2 flex-shrink-0">
              <!-- Minimize/Expand Button -->
              <Button 
                variant="ghost" 
                size="sm" 
                @click="toggleMinimize(conversation.id)" 
                class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800"
                :title="isMinimized(conversation.id) ? 'Expand analysis steps' : 'Minimize analysis steps'"
              >
                <Plus v-if="isMinimized(conversation.id)" class="w-4 h-4" />
                <Minus v-else class="w-4 h-4" />
              </Button>
              <!-- Copy Button -->
              <Button variant="ghost" size="sm" @click="copy(conversation.message)" class="p-1" title="Copy question">
                <Copy class="w-4 h-4" />
              </Button>
            </div>
          </div>
          <!-- Conditionally show ReasoningContainer based on minimize state -->
          <Transition
            enter-active-class="transition-all duration-300 ease-out"
            leave-active-class="transition-all duration-300 ease-in"
            enter-from-class="opacity-0 max-h-0 overflow-hidden"
            enter-to-class="opacity-100 max-h-screen"
            leave-from-class="opacity-100 max-h-screen"
            leave-to-class="opacity-0 max-h-0 overflow-hidden"
          >
            <ReasoningContainer 
              v-if="!isMinimized(conversation.id)" 
              :message="conversation" 
              class="w-full min-w-0" 
              @start-new-question="handleStartNewQuestion"
            />
          </Transition>
          <!-- Show minimized state indicator -->
          <Transition
            enter-active-class="transition-all duration-300 ease-out"
            leave-active-class="transition-all duration-300 ease-in"
            enter-from-class="opacity-0"
            enter-to-class="opacity-100"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
          >
            <div 
              v-if="isMinimized(conversation.id)"
              class="w-full text-center py-3 text-sm text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              @click="toggleMinimize(conversation.id)"
            >
              <div class="flex items-center justify-center gap-2">
                <Plus class="w-4 h-4" />
                <span class="italic">Analysis steps minimized - click to expand</span>
                <Plus class="w-4 h-4" />
              </div>
            </div>
          </Transition>
        </div>
      </CardContent>
    </Card>
    <!-- Real-time Progress Display -->
    <div v-if="props.isThinking" class="space-y-4">
      <!-- Show current processing step if we have stream data -->
      <Card v-if="shouldShowDetailedProgress" 
            class="border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
        <CardContent class="p-4">
          <div class="flex items-center gap-3">
            <Loader2 class="h-5 w-5 animate-spin text-blue-600" />
            <div class="flex-1">
              <div class="font-medium text-blue-900 dark:text-blue-100">
                Processing Step {{ currentNodeOutputs.length }}
              </div>
              <div class="text-sm text-blue-700 dark:text-blue-300">
                {{ getStepTitle(currentStep?.name || '') }}
              </div>
            </div>
            <div class="text-xs text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded">
              {{ currentStep?.name || '' }}
            </div>
          </div>
          
          <!-- Progress bar -->
          <div class="mt-3">
            <div class="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
              <div class="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out animate-pulse" 
                   :style="{ width: '60%' }"></div>
            </div>
            <div class="text-xs text-blue-600 dark:text-blue-400 mt-1">
              Analyzing your question...
            </div>
          </div>
        </CardContent>
      </Card>
      
      <!-- Show initial processing state when we have currentMessage but no node outputs yet -->
      <Card v-else-if="props.currentMessage && props.currentMessage.stream" 
            class="border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
        <CardContent class="p-4">
          <div class="flex items-center gap-3">
            <Loader2 class="h-5 w-5 animate-spin text-blue-600" />
            <div class="flex-1">
              <div class="font-medium text-blue-900 dark:text-blue-100">
                Initializing Analysis
              </div>
              <div class="text-sm text-blue-700 dark:text-blue-300">
                Setting up processing pipeline...
              </div>
            </div>
          </div>
          
          <!-- Progress bar -->
          <div class="mt-3">
            <div class="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
              <div class="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out animate-pulse" 
                   :style="{ width: '30%' }"></div>
            </div>
            <div class="text-xs text-blue-600 dark:text-blue-400 mt-1">
              Starting analysis...
            </div>
          </div>
        </CardContent>
      </Card>
      
      <!-- Fallback processing indicator (only if no currentMessage) -->
      <div v-else class="p-4 flex gap-x-3 items-center text-gray-500 bg-gray-50 dark:bg-gray-900 rounded-lg border">
        <Loader2 class="h-6 w-6 animate-spin" />
        <div>
          <div class="font-medium">Processing</div>
          <div class="text-sm">{{ currentProcessingText }}</div>
        </div>
      </div>
    </div>
    <ConversationsErrorHandler v-show="lastMessageErrored" @retry="retry_request"/>
  </div>
</template>

<style scoped>

</style>