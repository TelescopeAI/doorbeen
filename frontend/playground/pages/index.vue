<script setup lang="ts">
import { toast } from 'vue-sonner';
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
import SubmitButton from '~/components/ui/submit-button/SubmitButton.vue';
import { useSession } from '@clerk/vue'
import { useThreadStorage } from '~/composables/useThreadStorage'
import type { Thread } from '~/types/threads'


const route = useRoute();
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
  currentThread, 
  setCurrentThread, 
  getThread, 
  createThread,
  initializeCurrentThread 
} = useThreadStorage();

// Initialize configurations from localStorage
onMounted(async () => {
  // Load database configuration
  const storedDbConfig = localStorage.getItem('db-config')
  if (storedDbConfig) {
    try {
      const dbConfig = JSON.parse(storedDbConfig)
      if (dbConfig && Object.keys(dbConfig).length > 0) {
        conn_details = dbConfig  // Don't wrap in reactive here since it's already reactive
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

  // Initialize thread management for new conversations
  await initializeCurrentThread()
  
  // Clear any existing thread for new conversations
  setCurrentThread(null)
})

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
  const qn = current_question.value;
  
  console.log("Index page: Creating thread and redirecting for question:", qn);

  // Check if we have required configurations
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

  // Show loading context
  isAgentThinking.value = true;

  // Create a new thread for this conversation and redirect to chat route
  try {
    console.log("Creating new thread...");
    const newThread = await createThread({
      metadata: {
        title: qn.substring(0, 50) + (qn.length > 50 ? '...' : ''),
        created_from: 'index_page',
        source: 'new_conversation'
      }
    });
    
    console.log("Thread created successfully:", newThread);
    console.log("Thread ID:", newThread?.id);
    console.log("Thread ID type:", typeof newThread?.id);
    
    if (!newThread || !newThread.id) {
      throw new Error('Thread creation returned invalid thread');
    }
    
    console.log("Navigating to chat route...");
    
    // Navigate to the chat route with the new thread and pass the question
    await navigateTo(`/chat/${newThread.id}?question=${encodeURIComponent(qn)}`);
    
    // Refresh sidebar threads after successful navigation
    if (process.client && (window as any).refreshSidebarThreads) {
      await (window as any).refreshSidebarThreads();
    }
    
  } catch (error) {
    console.error('Failed to create thread:', error);
    toast.error('Thread Creation Failed', { description: 'Could not create new conversation' });
    isAgentThinking.value = false;
  }
}

// Function to abort the current processing
function abort_processing() {
  console.log('🛑 User requested to abort processing');
  
  // For the index page, we just stop the thinking context
  // since we're immediately redirecting to chat route
  isAgentThinking.value = false;
  
  toast.info('Analysis Stopped', { description: 'Processing has been cancelled' });
}

const { session } = useSession()

</script>

<template>
  <div class="page-dense flex flex-col text-density-high">

    <div class="w-full flex flex-col section-dense">
      <div>
<!--        This session has been active since {{ session }}.-->
      </div>


      <Card class="border border-blue-900 grow max-w-full card-dense">
        <template #content>
          <div class="flex flex-col conversation-dense">
            <ConversationsContainer :conversations="messages" :isThinking="isAgentThinking"
                                    @retry="ask_question(true)"/>
            <div class="flex gap-dense min-h-12 p-2 justify-center items-center rounded-xl">
              <TextEditor :initial_content="current_question" @contentUpdated="update_question"
                          @contentReady="ask_question" class="h-full"/>
              <SubmitButton 
                :is-processing="isAgentThinking"
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