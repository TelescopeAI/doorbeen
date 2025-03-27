<script setup lang="ts">
import { useToast } from "primevue/usetoast";
import { sql_agent_request } from "~/composables/network";
import type { MODEL_CONFIG } from "~/types/models";
import { type ConversationMessage, ConversationState } from "~/types/conversations";
import Navbar from "~/components/Navbar.vue";
import { useGenerateUUID4 } from "~/composables/uuid";
import { StreamResponse } from "~/types/streaming";
import type { NodeExecutionOutput } from "~/types/streaming";

import { ref, reactive, watch } from 'vue'
import { parseDBConfig } from "~/composables/parsing";
import { getAPIServerURL } from "~/composables/server";
import Panel from 'primevue/panel';
import Card from 'primevue/card';
import {SSEService} from "~/core/streaming/sse";
import { useAuth, useSession } from '@clerk/vue'

const toast = useToast();
const connection = reactive({
  host: "localhost", port: "5432", username: "root", password: "password",
  database: "", db_type: "bigquery"
});
let model_params: MODEL_CONFIG = reactive({
  name: "", api_key: ""
});
const sseService = ref(null);

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


// Watch for new stream messages
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
  const { ask, ask_sample_db } = await sql_agent_request(sample_mode.value);
  message.state = ConversationState.PROCESSING;
  message.attempts[message.attempts.length - 1].result = ConversationState.PROCESSING;
  await update_message_stream(message);
  isAgentThinking.value = true;
  // const { getToken } = useAuth()
  console.log("Session Token: ", await window.Clerk.session.getToken())
  const user_auth_token = await window.Clerk.session.getToken()

  sseService.value = new SSEService( `${getAPIServerURL()}/api/v1/assistants`, user_auth_token, {
    body: {
      question: qn,
      model: model_params,
      connection: parseDBConfig(conn_details),
      stream: true
    }
  });

  sseService.value.onMessage((sse_event) => {
    const data = sse_event
    console.log('Received SSE data:', sse_event);
    streamMessages.value.push(data)
  });

  await sseService.value.connect();


  // Send message using the new streaming service
  // sendMessage(JSON.stringify({
  //   question: qn,
  //   model: model_params,
  //   connection: parseDBConfig(conn_details),
  //   stream: true
  // }));


  let agent_message, error;

  // Non-streaming implementation
  if (!sample_mode.value) {
    ({ agent_message, error } = await ask(qn, conn_details, model_params));
  } else {
    ({ agent_message, error } = await ask_sample_db(qn));
  }

  const currentAttempt = message.attempts[message.attempts.length - 1];

  if (error?.value) {
    message.state = ConversationState.ERROR;
    currentAttempt.result = ConversationState.ERROR;
    currentAttempt.response = error.value;
    message.error = error.value;
    console.log("Updating message with error state:", message);
    await update_message_stream(message);
    toast.add({ severity: 'error', summary: 'Error', detail: error.value, life: 3000 });
  } else {
    message.state = ConversationState.COMPLETED;
    currentAttempt.result = ConversationState.COMPLETED;
    currentAttempt.response = agent_message.message;
    console.log("Agent Message Received: ", agent_message);
    if (agent_message.stats) message.stats = agent_message.stats;
    current_question.value = '';
  }

  await update_message_stream(message);
  isAgentThinking.value = false;
}
const { session } = useSession()

</script>

<template>
  <div class="p-4 md:p-10 flex flex-col gap-y-10">
    <Navbar/>
    <div class="w-full flex flex-col gap-y-4">
      <div>
<!--        This session has been active since {{ session }}.-->
      </div>
      <div class="config flex flex-col md:flex-row gap-y-6 md:gap-x-6">
        <div class="card md:w-3/5"
             :class="{'md:w-full': !show_model_config_ui}">
          <Panel header="Database" toggleable :collapsed="config_collapse_state.db" :pt="{root: {
            class:'border-surface-200 dark:border-surface-700'
          }}" :ptOptions="{mergeSections:true, mergeProps: true}">
            <div>
              <div class="w-full flex flex-row gap-10 flex-wrap justify-stretch">
                <DatabaseSelector :sample_mode="sample_mode"
                                  @DBConfigUpdated="connection_details_updated"
                                  @sampleModeUpdated="update_sample_mode"
                                  @dbConfigAvailableInStorage="update_db_collapse_state"
                />
              </div>
            </div>
          </Panel>
        </div>
        <div class="card md:w-2/5 h-full" v-show="show_model_config_ui">
          <Panel header="Model" toggleable :collapsed="config_collapse_state.model" class="rounded-b-xl h-full">
            <div class="h-full ">
              <div class="w-full flex flex-row gap-10 flex-wrap justify-stretch">
                <ModelSelector @modelConfigUpdated="model_updated"
                               @modelConfigAvailableInStorage="update_model_collapse_state"/>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      <Card class="border border-blue-900 grow max-w-full">
        <template #content>
          <div class="flex flex-col gap-y-6">
            <ConversationsContainer :conversations="messages" :isThinking="isAgentThinking"
                                    @retry="ask_question(true)"/>
            <div class="flex gap-x-2 min-h-20 border p-2 justify-center items-center rounded-xl">
              <TextEditor :initial_content="current_question" @contentUpdated="update_question"
                          @contentReady="ask_question" class="h-full"/>
              <ButtonIcones icon="solar:square-arrow-up-bold" size="36" class="h-fit" @click="ask_question"/>
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