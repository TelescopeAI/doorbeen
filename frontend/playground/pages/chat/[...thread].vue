<script setup lang="ts">
import type { MODEL_CONFIG } from "~/types/models";
import { type ConversationMessage, ConversationState } from "~/types/conversations";
import { useGenerateUUID4 } from "~/composables/uuid";
import { StreamResponse } from "~/types/streaming";
import type { NodeExecutionOutput, NodeExecutionData, AgentCoordinationOutput } from "~/types/streaming";

import { ref, reactive, watch, nextTick, triggerRef } from 'vue'
import { parseDBConfig } from "~/composables/parsing";
import { getAPIServerURL } from "~/composables/server";
import Card from 'primevue/card';
import { useSession } from '@clerk/vue'
import { useThreadStorage } from '~/composables/useThreadStorage'
import type { Thread } from '~/types/threads'
import { toast } from 'vue-sonner'
import { MessageSquare, Loader2, Copy } from 'lucide-vue-next'
import { Badge } from '~/components/ui/badge'
import ConversationSkeleton from '~/components/Conversations/ConversationSkeleton.vue'
import SubmitButton from '~/components/ui/submit-button/SubmitButton.vue'
import StreamingContainer from '~/components/Reasoning/StreamingContainer.vue'
import { useStreaming } from '~/composables/useStreaming'
import { useClipboard } from '@vueuse/core'
import { Button } from '@/components/ui/button'
import { Database, Bot, Settings, ChevronDown } from 'lucide-vue-next'
import { Dialog as ShadDialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Toggle } from '@/components/ui/toggle'
import ModelSelector from '~/components/Model/Selector.vue'
import DatabaseSelector from '~/components/Database/Selector.vue'

// Get thread ID from route params
const route = useRoute()
const threadId = route.params.thread?.[0] as string

// Validate thread ID
if (!threadId || threadId === 'undefined' || threadId === 'null') {
  console.error('Invalid thread ID:', threadId)
  // Redirect to index if invalid thread ID
  await navigateTo('/')
}

const connection = reactive({
  host: "localhost", port: "5432", username: "root", password: "password",
  database: "", db_type: "bigquery"
});
let model_params: MODEL_CONFIG = reactive({
  name: "", api_key: ""
});

// Use the new streaming composable
const streaming = useStreaming();

// Thread management
const { 
  getThread, 
  getThreadMessages,
  getMessageAllEvents,
  createThread,
  initializeCurrentThread,
  getThreadTitle,
  formatThreadDate 
} = useThreadStorage();

// Use the global current thread context
const { currentThread, setCurrentThread } = useCurrentThread();

// Question input handling
let current_question = ref('');
let last_question = ref('');

const update_question = (new_question: string) => {
  console.log('📝 Text input updated:', new_question);
  current_question.value = new_question;
};

const messages: Array<ConversationMessage> = reactive([]);
const current_message = ref<ConversationMessage | null>(null);

// Use streaming state instead of local state
let isAgentThinking = ref(false);
const isLoadingThread = ref(true);
const isLoadingMessages = ref(false);
let conn_details = reactive({});

const connection_details_updated = (new_conn: any) => {
  conn_details = new_conn;
  toast.success('Connection Updated', { description: 'Database Credentials Updated' });
};

const config_collapse_state = reactive({model: false, db: false});

const update_db_collapse_state = () => {
  config_collapse_state.db = true;
};

const update_model_collapse_state = () => {
  config_collapse_state.model = true;
};

const model_updated = (model_config: MODEL_CONFIG) => {
  model_params = model_config;
  toast.success('Model Updated', { 
    description: model_config.name + " would be used for all subsequent conversations" 
  });
};

const show_model_config_ui = ref(true);
const sample_mode = ref(false);
const update_sample_mode = (mode_status: boolean) => {
  sample_mode.value = mode_status;
  show_model_config_ui.value = !mode_status;
};

const update_message_stream = async (message: ConversationMessage) => {
  console.log("Updating message stream:", message);
  if (!messages.some(msg => msg.id === message.id)) {
    messages.push({ ...message });
  } else {
    const index = messages.findIndex(msg => msg.id === message.id);
    messages[index] = { ...message };
  }
  console.log("Updated messages array:", messages);
};

// Function to reset the stream context (now simplified with new composables)
const resetStreamState = () => {
  streaming.stateManager.resetState();
};

// Watch for streaming state changes and update current message
watch(() => streaming.state, (newState) => {
  if (current_message.value && newState.streamStarted) {
    // Convert the new unified state to the legacy StreamResponse format for backward compatibility
    const legacyStream = new StreamResponse({
      nodeOutputs: newState.thinkingSteps.map(step => ({
        type: 'assistant:node:output',
        name: step.agentName || 'unknown',
        data: { content: typeof step.content === 'string' ? step.content : JSON.stringify(step.content, null, 2) },
        occurred_at: step.timestamp
      }))
    });
  
    // Update the current message with the new stream data
    current_message.value.stream = legacyStream;
    
    
    // Update message state based on streaming state
    if (newState.error) {
      current_message.value.state = ConversationState.ERROR;
      current_message.value.error = newState.error;
    } else if (!newState.isStreaming && newState.streamStarted) {
        current_message.value.state = ConversationState.COMPLETED;
        const currentAttempt = current_message.value.attempts?.[current_message.value.attempts.length - 1];
        if (currentAttempt) {
          currentAttempt.result = ConversationState.COMPLETED;
        }
      isAgentThinking.value = false;
      current_question.value = ''; // Clear the question input
    }
          
          update_message_stream(current_message.value);
  }
}, { deep: true });

async function ask_question(retry: boolean = false) {
  retry = retry === true;
  let qn = retry ? last_question.value : current_question.value;
  if (!retry) last_question.value = qn;
  
  console.log("Asking Question: ", qn);

  // Check if we have required configurations
  console.log('Current configurations:', { conn_details, model_params });
  
  if (!conn_details) {
    toast.error('Configuration Missing', { description: 'Please configure your database connection first' });
    return;
  }
  
  if (!model_params || !model_params.name) {
    toast.error('Configuration Missing', { description: 'Please configure your AI model first' });
    return;
  }
  
  if (!qn || qn.trim() === '') {
    toast.error('Question Required', { description: 'Please enter a question first' });
    return;
  }

  // Reset the stream context before starting a new question or retry
  resetStreamState();

  // If we don't have a current thread but we're in a chat route, create one
  if (!currentThread.value && threadId) {
    try {
      const newThread = await createThread({
        metadata: {
          title: qn.substring(0, 50) + (qn.length > 50 ? '...' : ''),
          first_question: qn,
          source: 'chat_route'
        }
      })
      setCurrentThread(newThread)
      console.log('Created new thread for chat route:', newThread.id)
    } catch (error) {
      console.error('Failed to create thread:', error)
      toast.error('Thread Creation Failed', {
        description: 'Could not create conversation thread'
      })
      return
    }
  }

  let message: ConversationMessage;
  if (retry && messages.length > 0) {
    message = messages[messages.length - 1];
    if (!message.attempts) message.attempts = [];
    message.attempts.push({
      count: message.attempts.length,
      result: ConversationState.INITIATED,
      response: ''
    });
  } else {
    message = {
      id: useGenerateUUID4(),
      isAgent: false,
      message: qn,
      time: new Date(),
      state: ConversationState.INITIATED,
      attempts: [{
        count: 0,
        result: ConversationState.INITIATED,
        response: ''
      }],
      stream: new StreamResponse(null)
    };
    messages.push(message);
  }

  current_message.value = message;
  message.state = ConversationState.PROCESSING;
  if (message.attempts && message.attempts.length > 0) {
    message.attempts[message.attempts.length - 1].result = ConversationState.PROCESSING;
  }
  await update_message_stream(message);
  isAgentThinking.value = true;

  try {
    console.log("🚀 Starting stream with new composable");

    // Use the new streaming composable
    await streaming.startStream({
      threadId: currentThread.value?.id || threadId,
      message: qn,
      modelParams: model_params,
      connectionDetails: parseDBConfig(conn_details),
      useSupervisor: currentAnalysisMode.value === 'supervisor'
    });

    console.log('✅ Stream started successfully');

  } catch (error: any) {
    console.error('❌ Error setting up SSE connection:', error);
    const currentAttempt = message.attempts?.[message.attempts.length - 1];
    if (currentAttempt) {
      message.state = ConversationState.ERROR;
      currentAttempt.result = ConversationState.ERROR;
      currentAttempt.response = error?.message || 'Failed to establish connection';
      message.error = error?.message || 'Failed to establish connection';
      await update_message_stream(message);
    }
    toast.error('Connection Error', { description: error?.message || 'Failed to connect to server' });
    isAgentThinking.value = false;
  }
}

// Function to abort the current processing
function abort_processing() {
  console.log('🛑 User requested to abort processing');
  
  // Use the new streaming composable to stop the stream
  streaming.stopStream();
  
  // Reset the thinking context immediately
  isAgentThinking.value = false;
  
  // Update the current message context to show it was cancelled
  if (current_message.value) {
    const message = current_message.value;
    message.state = ConversationState.ERROR;
    
    if (message.attempts && message.attempts.length > 0) {
      const currentAttempt = message.attempts[message.attempts.length - 1];
      currentAttempt.result = ConversationState.ERROR;
      currentAttempt.response = 'Analysis was cancelled by user';
    }
    
    message.error = 'Analysis was cancelled by user';
    // Don't await this since we want immediate feedback
    update_message_stream(message);
  }
  
  toast.info('Analysis Stopped', { description: 'Processing has been cancelled' });
}

// Initialize thread on mount
onMounted(async () => {
  // Load database configuration
  const storedDbConfig = localStorage.getItem('db-config')
  if (storedDbConfig) {
    try {
      const dbConfig = JSON.parse(storedDbConfig)
      if (dbConfig && Object.keys(dbConfig).length > 0) {
        conn_details = dbConfig
      }
    } catch (error) {
      console.error('Error parsing stored database config:', error)
    }
  }

  // Load model configuration
  const storedModelConfig = localStorage.getItem('model-config')
  if (storedModelConfig) {
    try {
      const modelConfig = JSON.parse(storedModelConfig)
      if (modelConfig && Object.keys(modelConfig).length > 0) {
        model_params.name = modelConfig.name || ''
        model_params.api_key = modelConfig.api_key || ''
      }
    } catch (error) {
      console.error('Error parsing stored model config:', error)
    }
  }

  // Load analysis mode configuration
  loadAnalysisMode()

  // Check configuration status
  checkConfigStatus()

  // Load debug mode configuration
  loadDebugMode()

  // Initialize thread management only if we don't have a specific thread ID from URL
  if (!threadId) {
    await initializeCurrentThread()
  }

  if (threadId) {
    try {
      isLoadingThread.value = true
      const thread = await getThread(threadId) // This will automatically set as current thread
      
      // Load thread messages
      isLoadingMessages.value = true
      const messagesResponse = await getThreadMessages(threadId, 1, 100) // Load more messages for history
      
      // Convert thread messages to conversation messages and populate the messages array
      if (messagesResponse.messages && messagesResponse.messages.length > 0) {
        // Clear existing messages
        messages.splice(0, messages.length)
        
        // Sort messages by creation date to ensure proper order
        const sortedMessages = messagesResponse.messages.sort((a, b) => 
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        )
        
        // Convert thread messages to conversation messages with proper pairing
        const convertedMessages: ConversationMessage[] = []
        
        // Group messages by pairs (user question + assistant response)
        const messageGroups: { user?: any, assistant?: any }[] = []
        let currentGroup: { user?: any, assistant?: any } = {}
        
        for (const message of sortedMessages) {
          if (message.role === 'user') {
            // If we have a pending group, save it and start a new one
            if (currentGroup.user || currentGroup.assistant) {
              messageGroups.push(currentGroup)
              currentGroup = {}
            }
            currentGroup.user = message
          } else if (message.role === 'assistant') {
            currentGroup.assistant = message
          }
        }
        
        // Don't forget the last group
        if (currentGroup.user || currentGroup.assistant) {
          messageGroups.push(currentGroup)
        }
        
        // Convert groups to conversation messages
        for (const group of messageGroups) {
          // Only process groups that have a user message (question)
          if (!group.user) continue
          
          // Add user message first
          convertedMessages.push({
            id: group.user.id,
            isAgent: false,
            message: group.user.content,
            time: new Date(group.user.created_at),
            state: ConversationState.COMPLETED,
            attempts: [{
              count: 0,
              result: ConversationState.COMPLETED,
              response: group.user.content
            }],
            stream: new StreamResponse({})
          })
          
          // Add assistant response or placeholder
          if (group.assistant) {
            // Try to fetch stored events for this assistant message
            let streamResponse: StreamResponse
            
            try {
              const eventsData = await getMessageAllEvents(group.assistant.id)
              
              if (eventsData.events && eventsData.events.length > 0) {
                // Reconstruct StreamResponse from stored events (including agent lifecycle events)
                const nodeOutputs = eventsData.events.map((event: any) => ({
                  type: event.type,
                  name: event.name,
                  data: event.data,
                  category: event.category,
                  source: event.source,
                  stage: event.stage,
                  occurred_at: event.occurred_at
                }))
                
                streamResponse = new StreamResponse({ nodeOutputs })
                console.log(`Reconstructed ${nodeOutputs.length} events (including agent lifecycle) for assistant message ${group.assistant.id}`)
              } else {
                // No stored events, create basic response
                streamResponse = new StreamResponse({
                  nodeOutputs: [{
                    type: 'assistant:node:output',
                    name: 'historical_response',
                    data: { content: group.assistant.content },
                    occurred_at: group.assistant.created_at
                  }]
                })
              }
            } catch (error) {
              console.warn(`Failed to fetch events for message ${group.assistant.id}:`, error)
              // Fallback to basic response
              streamResponse = new StreamResponse({
                nodeOutputs: [{
                  type: 'assistant:node:output',
                  name: 'historical_response',
                  data: { content: group.assistant.content },
                  occurred_at: group.assistant.created_at
                }]
              })
            }
            
            // Extract human-readable content from JSON if needed
            let displayMessage = group.assistant.content
            try {
              const parsedContent = JSON.parse(group.assistant.content)
              if (parsedContent && typeof parsedContent === 'object') {
                // If it's a structured response, extract the meaningful content
                displayMessage = parsedContent.summary || 
                               parsedContent.answer || 
                               parsedContent.result || 
                               parsedContent.content ||
                               'Analysis completed'
              }
            } catch {
              // Not JSON, use as-is
            }
            
            convertedMessages.push({
              id: group.assistant.id,
              isAgent: true,
              message: displayMessage,
              time: new Date(group.assistant.created_at),
              state: ConversationState.COMPLETED,
              attempts: [{
                count: 0,
                result: ConversationState.COMPLETED,
                response: displayMessage
              }],
              stream: streamResponse
            })
          } else {
            // User question without assistant response - show placeholder
            convertedMessages.push({
              id: useGenerateUUID4(),
              isAgent: true,
              message: "💭 This response was not stored in the conversation history. You can re-ask this question to get a new response.",
              time: new Date(group.user.created_at),
              state: ConversationState.COMPLETED,
              attempts: [{
                count: 0,
                result: ConversationState.COMPLETED,
                response: "Response not stored in history"
              }],
              stream: new StreamResponse({
                nodeOutputs: [{
                  type: 'assistant:node:output',
                  name: 'missing_response_placeholder',
                  data: { 
                    content: "This response was not stored in the conversation history.",
                    is_placeholder: true
                  },
                  occurred_at: group.user.created_at
                }]
              })
            })
          }
        }
        
        // Add converted messages to the conversation
        messages.push(...convertedMessages)
        console.log(`Loaded ${convertedMessages.length} historical messages for thread`)
        
        toast.success('Conversation History Loaded', {
          description: `Restored ${convertedMessages.length} previous messages`
        })
      } else {
        console.log('No previous messages found for this thread')
      }
      
      console.log('Loaded thread:', thread, 'Messages:', messagesResponse.messages)
      
      toast.success('Thread Loaded', {
        description: `Loaded conversation: ${getThreadTitle(thread)}`
      })
      
      isLoadingMessages.value = false
      isLoadingThread.value = false
    } catch (error) {
      console.error('Failed to load thread:', error)
      toast.error('Failed to load conversation', {
        description: 'The requested conversation could not be found'
      })
      isLoadingMessages.value = false
      isLoadingThread.value = false
      // Redirect to main page
      await navigateTo('/')
    }
  } else {
    isLoadingThread.value = false
  }

  // Check if there's a question parameter from index page
  const questionParam = route.query.question as string
  if (questionParam && currentThread.value) {
    // Auto-populate the question field and ask it
    current_question.value = questionParam
    console.log('Auto-asking question from index:', questionParam)
    
    // Remove the question parameter from URL
    await navigateTo(`/chat/${threadId}`, { replace: true })
    
    // Ask the question after a brief delay to ensure everything is initialized
    setTimeout(() => {
      ask_question()
    }, 500)
  }
})

const handleStartNewQuestion = (question: string) => {
  console.log('Chat page received start-new-question:', question);
  current_question.value = question;
  ask_question();
};

// Format time for display
const formatTime = (time: Date) => {
  return time.toLocaleTimeString();
};

// Copy functionality with toast
const { copy } = useClipboard();

const copyQuestion = async (question: string) => {
  try {
    await copy(question);
    toast.success('Question Copied!', {
      description: 'The question has been copied to your clipboard.',
    });
  } catch (err) {
    toast.error('Copy Failed', {
      description: 'Failed to copy question to clipboard. Please try again.',
    });
  }
};

// Convert node outputs to ReasoningStep events
const convertNodeOutputsToEvents = (nodeOutputs: any[]) => {
  if (!nodeOutputs || !Array.isArray(nodeOutputs)) return [];
  
  return nodeOutputs.map((output, index) => {
    let type: 'thought' | 'tool_call' | 'tool_output' | 'agent_output' = 'thought';
    
    // Determine event type based on the event type field
    if (output.type?.includes('tool')) {
      type = 'tool_output';
    } else if (output.type?.includes('agent')) {
      type = 'agent_output';
    } else if (output.type?.includes('assistant')) {
      type = 'agent_output';
    }
    
    // Extract agent name from various sources
    let agentName = output.data?.agent_name || 
                   output.source ||
                   output.name ||
                   undefined;
    
    // Clean up agent name for display
    if (agentName) {
      // Convert source names to display names
      const sourceMapping: Record<string, string> = {
        'data_analyst': 'DataAnalyst',
        'query_generator': 'QueryGenerator', 
        'result_processor': 'ResultProcessor',
        'finalizer': 'Finalizer',
        'objective_evaluator': 'ObjectiveEvaluator',
        'supervisor': 'Supervisor'
      };
      agentName = sourceMapping[agentName] || agentName;
    }
    
    // Create a better title based on event type and content
    let title = output.name || 'Event';
    if (output.type?.includes('agent:start')) {
      title = `${agentName || 'Agent'} Started`;
    } else if (output.type?.includes('agent:end')) {
      title = `${agentName || 'Agent'} Completed`;
    } else if (output.type?.includes('agent:progress')) {
      title = `${agentName || 'Agent'} Progress`;
    } else if (output.data?.scope) {
      title = `${agentName || 'Agent'}: ${output.data.scope}`;
    }
    
    return {
      id: `event-${index}-${output.occurred_at || Date.now()}`,
      type,
      title,
      content: output.data?.content || output.data?.description || output.data || '',
      status: 'complete' as const,
      agentName,
      timestamp: output.occurred_at || new Date().toISOString(),
      progress: output.data?.progress || undefined
    };
  });
};

// Analysis mode handling functions
const handleModeChange = (mode: 'linear' | 'supervisor') => {
  currentAnalysisMode.value = mode;
  console.log('Analysis mode changed to:', mode);
};

const loadAnalysisMode = () => {
  const storedMode = localStorage.getItem('analysis-mode');
  if (storedMode && (storedMode === 'linear' || storedMode === 'supervisor')) {
    currentAnalysisMode.value = storedMode as 'linear' | 'supervisor';
  } else {
    currentAnalysisMode.value = 'linear'; // Default to linear
  }
};

const { session } = useSession()

// Analysis mode state
const currentAnalysisMode = ref<'linear' | 'supervisor'>('linear');

// Configuration status tracking
const dbConfigAvailable = ref(false)
const modelConfigAvailable = ref(false)

// Dialog states
const isDatabaseDialogOpen = ref(false)
const isModelDialogOpen = ref(false)

// Debug mode state
const isDebugMode = ref(false)

// Load debug mode from localStorage
const loadDebugMode = () => {
  const storedDebugMode = localStorage.getItem('debug-mode')
  if (storedDebugMode !== null) {
    isDebugMode.value = storedDebugMode === 'true'
  } else {
    isDebugMode.value = false // Default to business user mode
  }
}

// Toggle debug mode
const toggleDebugMode = () => {
  isDebugMode.value = !isDebugMode.value
  localStorage.setItem('debug-mode', isDebugMode.value.toString())
  console.log('Debug mode changed to:', isDebugMode.value)
}

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
const getModeDisplayName = (mode: 'linear' | 'supervisor') => {
  return mode === 'linear' ? 'Linear' : 'Supervisor'
}

const getModeDescription = (mode: 'linear' | 'supervisor') => {
  return mode === 'linear' 
    ? 'Sequential step-by-step analysis'
    : 'Multi-agent coordinated analysis'
}

const setMode = (mode: 'linear' | 'supervisor') => {
  currentAnalysisMode.value = mode
  localStorage.setItem('analysis-mode', mode)
  console.log('Mode changed to:', mode)
}
</script>

<template>
  <div class="page-dense flex flex-col text-density-high">
    <!-- Thread info header -->
    <div v-if="currentThread" class="mb-4 p-4 bg-muted/50 rounded-lg">
      <div class="flex items-center gap-2 text-sm text-muted-foreground">
        <MessageSquare class="h-4 w-4" />
        <span>Conversation: {{ getThreadTitle(currentThread) }}</span>
        <Badge variant="secondary" class="text-xs">
          {{ formatThreadDate(currentThread.updated_at) }}
        </Badge>
      </div>
    </div>

    <!-- Configuration Controls -->
    <div class="flex gap-dense mb-4">
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
            <span class="text-xs text-blue-600 dark:text-blue-400">{{ getModeDisplayName(currentAnalysisMode) }}</span>
            <ChevronDown class="w-3 h-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <DropdownMenuItem 
            @click="setMode('linear')"
            class="cursor-pointer"
            :class="{ 'bg-blue-50 dark:bg-blue-900/20': currentAnalysisMode === 'linear' }"
          >
            <div class="flex flex-col">
              <div class="flex items-center gap-2">
                <span class="font-medium">Linear</span>
                <span v-if="currentAnalysisMode === 'linear'" class="text-blue-600 dark:text-blue-400 text-xs">✓</span>
              </div>
              <span class="text-xs text-muted-foreground">{{ getModeDescription('linear') }}</span>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem 
            @click="setMode('supervisor')"
            class="cursor-pointer"
            :class="{ 'bg-blue-50 dark:bg-blue-900/20': currentAnalysisMode === 'supervisor' }"
          >
            <div class="flex flex-col">
              <div class="flex items-center gap-2">
                <span class="font-medium">Supervisor</span>
                <span v-if="currentAnalysisMode === 'supervisor'" class="text-blue-600 dark:text-blue-400 text-xs">✓</span>
              </div>
              <span class="text-xs text-muted-foreground">{{ getModeDescription('supervisor') }}</span>
            </div>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <!-- Debug Mode Toggle -->
      <div class="flex items-center gap-2">
        <Toggle 
          :pressed="isDebugMode"
          @click="toggleDebugMode"
          aria-label="Toggle debug mode"
          class="flex items-center gap-2"
        >
          <Settings class="w-4 h-4" />
          <span class="hidden sm:inline">Debug</span>
        </Toggle>
        <span v-if="isDebugMode" class="text-orange-600 dark:text-orange-400 text-xs font-medium">ON</span>
        <span v-else class="text-gray-500 text-xs">OFF</span>
      </div>
    </div>

    <div class="w-full flex flex-col section-dense">
      <div>
<!--        This session has been active since {{ session }}.-->
      </div>

      <Card class="border border-blue-900 grow max-w-full card-dense">
        <template #content>
          <div class="flex flex-col conversation-dense">
            <!-- Loading State -->
            <div v-if="isLoadingThread || isLoadingMessages" class="space-y-4">
              <!-- Thread Loading Header -->
              <div v-if="isLoadingThread" class="flex items-center gap-2 p-4 bg-muted/50 rounded-lg">
                <Loader2 class="h-4 w-4 animate-spin" />
                <span class="text-sm text-muted-foreground">Loading conversation...</span>
              </div>
              
              <!-- Messages Loading -->
              <div v-if="isLoadingMessages" class="space-y-2">
                <div class="flex items-center gap-2 px-4">
                  <Loader2 class="h-4 w-4 animate-spin" />
                  <span class="text-sm text-muted-foreground">Loading conversation history...</span>
                </div>
                <ConversationSkeleton :count="2" />
              </div>
            </div>
            
            <!-- Loaded Content -->
            <div v-else>
              <!-- Show streaming interface for all messages -->
              <div class="space-y-6">
                <!-- Historical conversations -->
                <div v-for="message in messages" :key="message.id" class="message-container">
                  <!-- User Question -->
                  <div v-if="!message.isAgent" class="user-message mb-4 p-4 bg-blue-50 rounded-lg">
                    <div class="flex items-start space-x-3">
                      <div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                        U
                      </div>
                      <div class="flex-1">
                        <p class="text-sm font-medium text-gray-900">You</p>
                        <div class="mt-1 text-gray-700">{{ message.message }}</div>
                      </div>
                      <Button variant="ghost" size="sm" class="h-8 w-8 p-0 text-gray-500 hover:text-gray-700" @click="copyQuestion(message.message)">
                        <Copy class="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  <!-- Agent Response -->
                  <div v-else class="agent-response">
                    <div class="flex items-start space-x-3 mb-4">
                      <div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                        AI
                      </div>
                      <div class="flex-1">
                        <p class="text-sm font-medium text-gray-900">Assistant</p>
                        <div class="mt-1 text-gray-600 text-sm">{{ formatTime(message.time) }}</div>
                      </div>
                    </div>
                    
                    <!-- Use StreamingContainer for agent responses -->
                    <StreamingContainer 
                      v-if="message.stream && message.stream.nodeOutputs"
                      :events="convertNodeOutputsToEvents(message.stream.nodeOutputs)"
                      :debug-mode="isDebugMode"
                                      @start-new-question="handleStartNewQuestion"
                    />
              
                    <!-- Fallback for messages without stream data -->
                    <div v-else class="p-4 border rounded-lg bg-gray-50">
                      <p class="text-gray-700">{{ message.message }}</p>
                    </div>
                  </div>
                </div>
                
                <!-- Current streaming message -->
                <div v-if="streaming.state.streamStarted && current_message" class="current-streaming">
                  <div class="flex items-start space-x-3 mb-4">
                    <div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                      AI
                    </div>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-gray-900">Assistant</p>
                      <div class="mt-1 text-gray-600 text-sm">Analyzing...</div>
                    </div>
                  </div>
                  
                <StreamingContainer 
                    :events="streaming.state.thinkingSteps"
                    :final-answer="streaming.state.finalAnswer || undefined"
                    :debug-mode="isDebugMode"
                  @start-new-question="handleStartNewQuestion"
                />
                </div>
              </div>
            </div>
            
            <!-- Input Area - Always Show -->
            <div class="flex gap-dense min-h-12 p-2 justify-center items-center rounded-xl">
              <TextEditor :initial_content="current_question" @contentUpdated="update_question"
                          @contentReady="ask_question" class="h-full" :disabled="isLoadingThread"/>
              <SubmitButton 
                :is-processing="isAgentThinking"
                :disabled="isLoadingThread"
                size="lg"
                class="h-fit btn-dense"
                @click="ask_question"
                @abort="abort_processing"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
    <Toast />
  </div>
</template>

<style scoped>
/* Your scoped styles here */
</style> 