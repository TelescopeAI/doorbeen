<script setup lang="ts">
import { useToast } from "primevue/usetoast";
import type { MODEL_CONFIG } from "~/types/models";
import { type ConversationMessage, ConversationState } from "~/types/conversations";
import { useGenerateUUID4 } from "~/composables/uuid";
import { StreamResponse } from "~/types/streaming";
import type { NodeExecutionOutput, NodeExecutionData } from "~/types/streaming";

import { ref, reactive, watch } from 'vue'
import { parseDBConfig } from "~/composables/parsing";
import { getAPIServerURL } from "~/composables/server";
import Card from 'primevue/card';
import {SSEService} from "~/core/streaming/sse";
import { useSession } from '@clerk/vue'
import { useThreadStorage } from '~/composables/useThreadStorage'
import type { Thread } from '~/types/threads'
import { toast } from 'vue-sonner'
import { MessageSquare, Loader2 } from 'lucide-vue-next'
import { Badge } from '~/components/ui/badge'
import ConversationSkeleton from '~/components/Conversations/ConversationSkeleton.vue'

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
const sseService = ref<SSEService | null>(null);

// Thread management
const { 
  getThread, 
  getThreadMessages,
  getMessageNodeEvents,
  createThread,
  initializeCurrentThread,
  getThreadTitle,
  formatThreadDate 
} = useThreadStorage();

// Use the global current thread state
const { currentThread, setCurrentThread } = useCurrentThread();

// Copy all the existing conversation logic from index.vue
let current_question = ref('');
let last_question = ref('');
const streamMessages = ref([])

const update_question = (new_question: string) => {
  console.log('📝 Text input updated:', new_question);
  current_question.value = new_question;
};

const messages: Array<ConversationMessage> = reactive([]);
const current_message = ref<ConversationMessage | null>(null);

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

// Create a ref to hold the cumulative stream state
const cumulativeStreamResponse = ref<StreamResponse>(new StreamResponse(null));

// Function to reset the stream state
const resetStreamState = () => {
  cumulativeStreamResponse.value = new StreamResponse(null);
};

// Enhanced node-specific data processing
const processNodeSpecificData = (nodeOutput: NodeExecutionOutput) => {
  const nodeName = nodeOutput.name;
  const data = nodeOutput.data;
  
  // Handle stream termination
  if (nodeName === 'stream_termination' || nodeName === 'conversation_complete') {
    try {
      console.log('Stream terminated:', data);
      
      // If current message exists, mark it as complete
      if (current_message.value) {
        current_message.value.state = ConversationState.COMPLETED;
        const currentAttempt = current_message.value.attempts?.[current_message.value.attempts.length - 1];
        if (currentAttempt) {
          currentAttempt.result = ConversationState.COMPLETED;
        }
        update_message_stream(current_message.value);
      }
      
      isAgentThinking.value = false;
      current_question.value = ''; // Clear the question input
      return;
    } catch (error) {
      console.error('Error processing termination data:', error);
    }
  }
  
  // Handle both string and structured data
  let structuredData: NodeExecutionData | null = null;
  if (typeof data === 'string') {
    try {
      structuredData = JSON.parse(data);
    } catch {
      // If it's not JSON, treat as simple string content
      structuredData = { content: data };
    }
  } else {
    structuredData = data as NodeExecutionData;
  }

  // Basic node processing - can be enhanced as needed
  console.log('Processing node:', nodeName, 'with data:', structuredData);
};

// Watch for new stream messages with enhanced processing
watch(() => streamMessages, (newMessages) => {
  const newVal = newMessages.value;
  if (newVal.length > 0) {
    const latestMessage = newVal[newVal.length - 1];
    try {
      if (typeof latestMessage === 'string' && latestMessage === 'pong') {
        return;
      }

      const message = latestMessage as any as NodeExecutionOutput;

      if (message.type === 'assistant:node:output') {
        const nodeOutput: NodeExecutionOutput = {
          type: message.type,
          name: message.name,
          data: message.data,
          occurred_at: message.occurred_at
        };

        // Add the nodeOutput to the cumulativeStreamResponse
        if (!cumulativeStreamResponse.value.nodeOutputs) {
          cumulativeStreamResponse.value.nodeOutputs = [];
        }
        cumulativeStreamResponse.value.nodeOutputs.push(nodeOutput);

        // Enhanced processing based on node type
        processNodeSpecificData(nodeOutput);

        // Update the current message's stream
        if (current_message.value) {
          current_message.value.stream = cumulativeStreamResponse.value;
          update_message_stream(current_message.value);
        } else {
          console.error('current_message.value is null');
        }
      } else {
        console.error('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error processing message:', error, 'Raw message:', latestMessage);
    }
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

  // Reset the stream state before starting a new question or retry
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
    console.log("🔐 Getting auth token...");
    const user_auth_token = await window.Clerk?.session?.getToken();
    
    if (!user_auth_token) {
      throw new Error('Authentication token not available');
    }

    console.log("✅ Auth token obtained");

    // Clean up any existing SSE connection
    if (sseService.value) {
      console.log("🧹 Cleaning up existing SSE connection");
      sseService.value.disconnect();
    }

    const requestPayload = {
      question: qn,
      model: model_params,
      connection: parseDBConfig(conn_details),
      stream: true,
      ...(currentThread.value && { thread_id: currentThread.value.id }),
      message_metadata: {
        source: 'conversation_ui',
        timestamp: new Date().toISOString(),
        ...(currentThread.value && { thread_title: currentThread.value.metadata?.title })
      }
    };

    console.log('🚀 Setting up SSE connection with payload:', requestPayload);

    sseService.value = new SSEService(`${getAPIServerURL()}/api/v1/assistants`, user_auth_token, {
      body: requestPayload
    });

    sseService.value.onMessage((sse_event) => {
      console.log('📨 Received SSE data:', sse_event);
      streamMessages.value.push(sse_event);
    });

    await sseService.value.connect();
    console.log('✅ SSE Connection established successfully');

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

// Initialize thread on mount
onMounted(async () => {
  // Load database configuration
  const storedDbConfig = localStorage.getItem('db-config')
  if (storedDbConfig) {
    try {
      const dbConfig = JSON.parse(storedDbConfig)
      if (dbConfig && Object.keys(dbConfig).length > 0) {
        conn_details = dbConfig
        console.log('Loaded database config:', dbConfig)
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
        console.log('Loaded model config:', modelConfig)
      }
    } catch (error) {
      console.error('Error parsing stored model config:', error)
    }
  }

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
            // Try to fetch stored node events for this assistant message
            let streamResponse: StreamResponse
            
            try {
              const nodeEventsData = await getMessageNodeEvents(group.assistant.id)
              
              if (nodeEventsData.node_events && nodeEventsData.node_events.length > 0) {
                // Reconstruct StreamResponse from stored node events
                const nodeOutputs = nodeEventsData.node_events.map((event: any) => ({
                  type: event.type,
                  name: event.name,
                  data: event.data,
                  occurred_at: event.occurred_at
                }))
                
                streamResponse = new StreamResponse({ nodeOutputs })
                console.log(`Reconstructed ${nodeOutputs.length} node events for assistant message ${group.assistant.id}`)
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
              console.warn(`Failed to fetch node events for message ${group.assistant.id}:`, error)
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

const { session } = useSession()
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
              <ConversationsContainer :conversations="messages" :isThinking="isAgentThinking"
                                      @retry="ask_question(true)"/>
            </div>
            
            <!-- Input Area - Always Show -->
            <div class="flex gap-dense min-h-12 p-2 justify-center items-center rounded-xl">
              <TextEditor :initial_content="current_question" @contentUpdated="update_question"
                          @contentReady="ask_question" class="h-full" :disabled="isLoadingThread"/>
              <ButtonIcones icon="solar:square-arrow-up-bold" size="36" class="h-fit btn-dense" 
                           @click="ask_question" :disabled="isLoadingThread"/>
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