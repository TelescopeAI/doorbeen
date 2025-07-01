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
import {SSEService} from "~/core/streaming/sse";
import { useSession } from '@clerk/vue'
import { useThreadStorage } from '~/composables/useThreadStorage'
import type { Thread } from '~/types/threads'
import { toast } from 'vue-sonner'
import { MessageSquare, Loader2 } from 'lucide-vue-next'
import { Badge } from '~/components/ui/badge'
import ConversationSkeleton from '~/components/Conversations/ConversationSkeleton.vue'
import SubmitButton from '~/components/ui/submit-button/SubmitButton.vue'

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

// Use the global current thread context
const { currentThread, setCurrentThread } = useCurrentThread();

// Copy all the existing conversation logic from index.vue
let current_question = ref('');
let last_question = ref('');
const streamMessages = ref<any[]>([])

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

// Create a ref to hold the cumulative stream context
const cumulativeStreamResponse = ref<StreamResponse>(new StreamResponse(null));

// Function to reset the stream context
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
watch(streamMessages, (newMessages) => {
  console.log('🎯 Watch function triggered! Array length:', newMessages.length);
  const newVal = newMessages;
  
  if (newVal && newVal.length > 0) {
    const latestMessage = newVal[newVal.length - 1];
    console.log('🎯 Latest message type:', latestMessage?.type);
    
    try {
      if (typeof latestMessage === 'string' && latestMessage === 'pong') {
        return;
      }

      const message = latestMessage as any as NodeExecutionOutput;
      console.log('🔄 Frontend received event:', message.type, message);

      // Handle different event types
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
          // Ensure the stream and nodeOutputs array exist
          if (!current_message.value.stream) {
            current_message.value.stream = new StreamResponse(null);
          }
          if (!current_message.value.stream.nodeOutputs) {
            current_message.value.stream.nodeOutputs = [];
          }
          
          // Add the new node output directly to the reactive array
          current_message.value.stream.nodeOutputs.push(nodeOutput);
          
          // Also update other stream properties from cumulative response
          Object.assign(current_message.value.stream, {
            agentOutputs: cumulativeStreamResponse.value.agentOutputs,
            supervisorDecisions: cumulativeStreamResponse.value.supervisorDecisions,
            agentHandoffs: cumulativeStreamResponse.value.agentHandoffs,
            currentAgent: cumulativeStreamResponse.value.currentAgent,
            agentProgress: cumulativeStreamResponse.value.agentProgress,
            explorationStatus: cumulativeStreamResponse.value.explorationStatus,
            circuitBreakerStatus: cumulativeStreamResponse.value.circuitBreakerStatus,
            resultAnalysis: cumulativeStreamResponse.value.resultAnalysis
          });
          
          update_message_stream(current_message.value);
        }
      }
      // Handle agent coordination events
      else if (message.type === 'assistant:agent:output') {
        const agentOutput: AgentCoordinationOutput = {
          type: message.type,
          name: message.name,
          data: message.data,
          occurred_at: message.occurred_at,
          node_equivalent: message.node_equivalent
        };

        // Add to agent outputs in stream response
        if (!cumulativeStreamResponse.value.agentOutputs) {
          cumulativeStreamResponse.value.agentOutputs = [];
        }
        cumulativeStreamResponse.value.agentOutputs.push(agentOutput);

        // Update agent progress if available
        if (message.data?.agent_progress) {
          cumulativeStreamResponse.value.agentProgress = message.data.agent_progress;
        }

        // Update current agent if available
        if (message.data?.agent_name) {
          cumulativeStreamResponse.value.currentAgent = message.data.agent_name;
        }

        // Update objectives status if available
        if (message.data?.objectives_status) {
          cumulativeStreamResponse.value.resultAnalysis = {
            objectivesMet: message.data.objectives_status.overall_status === 'complete',
            insights: [],
            alternatives: [],
            nextSteps: ''
          };
        }

        // Convert agent output to familiar node output for backward compatibility
        const compatibleNodeOutput: NodeExecutionOutput = {
          type: 'assistant:node:output',
          name: agentOutput.node_equivalent || cumulativeStreamResponse.value.getFamiliarNodeName(message.data?.agent_name || message.name),
          data: message.data,
          occurred_at: message.occurred_at
        };

        if (!cumulativeStreamResponse.value.nodeOutputs) {
          cumulativeStreamResponse.value.nodeOutputs = [];
        }
        cumulativeStreamResponse.value.nodeOutputs.push(compatibleNodeOutput);

        // Process as node data for existing UI components
        processNodeSpecificData(compatibleNodeOutput);

        // Update the current message's stream
        if (current_message.value) {
          // Create a new stream object to trigger reactivity
          current_message.value.stream = { ...cumulativeStreamResponse.value };
          
          // Force reactivity update
          triggerRef(current_message);
          
          update_message_stream(current_message.value);
        }
      }
      // Handle supervisor decisions
      else if (message.type === 'supervisor:decision') {
        if (!cumulativeStreamResponse.value.supervisorDecisions) {
          cumulativeStreamResponse.value.supervisorDecisions = [];
        }
        cumulativeStreamResponse.value.supervisorDecisions.push(message.data);

        // Update the current message's stream
        if (current_message.value) {
          // Create a new stream object to trigger reactivity
          current_message.value.stream = { ...cumulativeStreamResponse.value };
          
          // Force reactivity update
          triggerRef(current_message);
          
          update_message_stream(current_message.value);
        }
      }
      // Handle agent handoffs
      else if (message.type === 'agent:handoff') {
        if (!cumulativeStreamResponse.value.agentHandoffs) {
          cumulativeStreamResponse.value.agentHandoffs = [];
        }
        cumulativeStreamResponse.value.agentHandoffs.push(message.data);

        // Update the current message's stream
        if (current_message.value) {
          // Create a new stream object to trigger reactivity
          current_message.value.stream = { ...cumulativeStreamResponse.value };
          
          // Force reactivity update
          triggerRef(current_message);
          
          update_message_stream(current_message.value);
        }
      }
      // Handle thread info events (these are informational)
      else if (message.type === 'thread_info') {
        console.log('📄 Thread info received:', message);
        // Just log these, no need to update UI
      }
      // Handle agent tool invocation
      else if (message.type === 'agent:tool:invoke') {
        // Treat as a node output for display purposes
        const nodeOutput: NodeExecutionOutput = {
          type: 'assistant:node:output',
          name: message.name, // Tool name
          data: message.data, // Tool call data
          occurred_at: message.occurred_at
        };

        if (!cumulativeStreamResponse.value.nodeOutputs) {
          cumulativeStreamResponse.value.nodeOutputs = [];
        }
        cumulativeStreamResponse.value.nodeOutputs.push(nodeOutput);
        processNodeSpecificData(nodeOutput);

        if (current_message.value) {
          if (!current_message.value.stream) {
            current_message.value.stream = new StreamResponse(null);
          }
          if (!current_message.value.stream.nodeOutputs) {
            current_message.value.stream.nodeOutputs = [];
          }
          current_message.value.stream.nodeOutputs.push(nodeOutput);
          update_message_stream(current_message.value);
        }
      }
      // Handle agent text streaming
      else if (message.type === 'agent:stream:output') {
        console.log('🔄 Processing agent:stream:output event:', message);
        
        // Create a node output for the analysis steps section
        const nodeOutput: NodeExecutionOutput = {
          type: 'assistant:node:output',
          name: message.name, // Agent name (e.g., QueryGenerator, DataAnalyst)
          data: message.data, // The content data
          occurred_at: message.occurred_at
        };

        if (!cumulativeStreamResponse.value.nodeOutputs) {
          cumulativeStreamResponse.value.nodeOutputs = [];
        }
        cumulativeStreamResponse.value.nodeOutputs.push(nodeOutput);
        processNodeSpecificData(nodeOutput);

        if (current_message.value) {
          // For the chat message content, format the JSON nicely if it's JSON
          let displayContent = message.data.content;
          try {
            const parsedContent = JSON.parse(message.data.content);
            // If it's a valid JSON object, format it nicely
            displayContent = JSON.stringify(parsedContent, null, 2);
          } catch (e) {
            // If it's not JSON, use as-is
            displayContent = message.data.content;
          }
          
          if (typeof current_message.value.content !== 'string') {
            current_message.value.content = '';
          }
          // Append formatted content to the current message
          current_message.value.content += displayContent + '\n\n';
          console.log('📝 Updated message content:', current_message.value.content);
          
          // Also update the stream with the node output
          if (!current_message.value.stream) {
            current_message.value.stream = new StreamResponse(null);
          }
          current_message.value.stream = { ...cumulativeStreamResponse.value };
          
          update_message_stream(current_message.value);
        } else {
          console.warn('⚠️ No current_message.value available for agent:stream:output');
        }
      }
      // Handle agent lifecycle events
      else if (message.type === 'agent:start' || message.type === 'agent:end') {
        if (!cumulativeStreamResponse.value.agentProgress) {
          cumulativeStreamResponse.value.agentProgress = [];
        }
        cumulativeStreamResponse.value.agentProgress.push({
          agent_name: message.name,
          status: message.type === 'agent:start' ? 'starting' : 'finished',
          description: message.data.description,
        });
        if (message.type === 'agent:start') {
          cumulativeStreamResponse.value.currentAgent = message.name;
        }
        if (current_message.value) {
          current_message.value.stream = { ...cumulativeStreamResponse.value };
          triggerRef(current_message);
          update_message_stream(current_message.value);
        }
      }
      // Handle unknown event types
      else {
        console.warn('Unknown message type:', message.type, 'Full message:', message);
        // Don't treat unknown types as errors anymore, just log them
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
      use_supervisor: currentAnalysisMode.value === 'supervisor',
      ...(currentThread.value && { thread_id: currentThread.value.id }),
      message_metadata: {
        source: 'conversation_ui',
        timestamp: new Date().toISOString(),
        analysis_mode: currentAnalysisMode.value,
        ...(currentThread.value && { thread_title: currentThread.value.metadata?.title })
      }
    };


    sseService.value = new SSEService(`${getAPIServerURL()}/api/v1/assistants`, user_auth_token, {
      body: requestPayload
    });

    sseService.value.onMessage((sse_event) => {
      console.log('📨 Pushing event to streamMessages:', sse_event.type, sse_event);
      // Instead of pushing to the array, create a new array to trigger reactivity
      streamMessages.value = [...streamMessages.value, sse_event];
      console.log('📨 streamMessages length now:', streamMessages.value.length);
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

// Function to abort the current processing
function abort_processing() {
  console.log('🛑 User requested to abort processing');
  
  // Disconnect the SSE service - this will abort the underlying fetch request
  if (sseService.value) {
    console.log('🧹 Disconnecting SSE service');
    sseService.value.disconnect();
    sseService.value = null;
  }
  
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

  // Load analysis mode configuration
  loadAnalysisMode()

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

const handleStartNewQuestion = (question: string) => {
  console.log('Chat page received start-new-question:', question);
  current_question.value = question;
  ask_question();
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
                                      :currentMessage="current_message"
                                      @retry="ask_question(true)"
                                      @start-new-question="handleStartNewQuestion"
                                      @mode-changed="handleModeChange"/>
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