<script setup lang="ts">
import { useElementSize } from '@vueuse/core'; // Assuming you are using vueuse for element size
import { ConversationState } from '../../types/conversations'; // Add this import
import { Button } from '~/components/ui/button';
import { useClipboard } from '@vueuse/core'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog as ShadDialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Copy, Database, Bot, Loader2 } from 'lucide-vue-next';
import DatabaseSelector from '@/components/Database/Selector.vue'
import ModelSelector from '@/components/Model/Selector.vue'


// Define component props
const props = defineProps({
  conversations: {
    type: Array,
    default: () => []
  },
  isThinking: {
    type: Boolean,
    default: false
  }
});
const emit = defineEmits(['retry', 'start-new-question']);

// Reactive variables
const lastMessage = ref(null);
const lastMessageErrored = ref(false);
// Watch the last message for changes and update the error state
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
  console.log("Last message state:", lastMessage.value?.state);
  console.log("Is error?", lastMessageErrored.value);
}, {deep: true});

// Processing text logic
const processingTexts = ["Fetching Data", "Analysing", "Thinking"];
const currentProcessingText = ref(processingTexts[0]);

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

// Database and Model configuration status
const dbConfigAvailable = ref(false)
const modelConfigAvailable = ref(false)

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

// Check configuration status on mount
onMounted(() => {
  checkConfigStatus()
  
  // Listen for localStorage changes to update status
  window.addEventListener('storage', checkConfigStatus)
})

// Clean up event listener on unmount
onUnmounted(() => {
  window.removeEventListener('storage', checkConfigStatus)
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
            <span class="p-1 flex-shrink-0">
              <Button variant="ghost" size="sm" @click="copy(conversation.message)">
                <Copy class="w-4 h-4" />
              </Button>
            </span>
          </div>
          <ReasoningContainer :message="conversation" class="w-full min-w-0" @start-new-question="handleStartNewQuestion"/>
        </div>
      </CardContent>
    </Card>
    <div v-if="isThinking" class="p-2 flex gap-x-2 items-center text-gray-500">
      <Loader2 class="h-6 w-6 animate-spin" />
      <p class="text-lg"> Processing </p>
    </div>
    <ConversationsErrorHandler v-show="lastMessageErrored" @retry="retry_request"/>
  </div>
</template>

<style scoped>

</style>