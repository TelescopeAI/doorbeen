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

const toast = useToast();
const connection = reactive({
  host: "localhost", port: "5432", username: "root", password: "password",
  database: "", db_type: "bigquery"
});
let model_params: MODEL_CONFIG = reactive({
  name: "", api_key: ""
});
const sseService = ref<SSEService | null>(null);

// Initialize configurations from localStorage
onMounted(() => {
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
})

const model_updated = (model_config: MODEL_CONFIG) => {
  model_params = model_config;
  toast.add({ severity: 'success', summary: 'Model Updated',
              detail: model_config.name + " would be used for all subsequent conversations", life: 3000 });
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
let conn_details = reactive(null);
const connection_details_updated = (new_conn: any) => {
  conn_details = new_conn;
  toast.add({ severity: 'success', summary: 'Connection Updated', detail: 'Database Credentials Updated', life: 3000 });
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

// Create a ref to hold the cumulative stream state
const cumulativeStreamResponse = ref<StreamResponse>(new StreamResponse());

// Function to reset the stream state
const resetStreamState = () => {
  cumulativeStreamResponse.value = new StreamResponse();
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
    toast.add({ severity: 'error', summary: 'Configuration Missing', detail: 'Please configure your database connection first', life: 3000 });
    return;
  }
  
  if (!model_params || !model_params.name) {
    toast.add({ severity: 'error', summary: 'Configuration Missing', detail: 'Please configure your AI model first', life: 3000 });
    return;
  }
  
  if (!qn || qn.trim() === '') {
    toast.add({ severity: 'error', summary: 'Question Required', detail: 'Please enter a question first', life: 3000 });
    return;
  }

  // Reset the stream state before starting a new question or retry
  resetStreamState();

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
      stream: new StreamResponse()
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
      stream: true
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
    toast.add({ severity: 'error', summary: 'Connection Error', detail: error?.message || 'Failed to connect to server', life: 3000 });
    isAgentThinking.value = false;
  }
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
              <ButtonIcones icon="solar:square-arrow-up-bold" size="36" class="h-fit btn-dense" @click="ask_question"/>
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