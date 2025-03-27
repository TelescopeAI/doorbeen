<script setup lang="ts">
import { useElementSize } from '@vueuse/core'; // Assuming you are using vueuse for element size
import { ConversationState } from '../../types/conversations'; // Add this import
import Button from 'primevue/button';
import { useClipboard } from '@vueuse/core'
import Panel from 'primevue/panel';
import Splitter from 'primevue/splitter';
import SplitterPanel from 'primevue/splitterpanel';
import Fieldset from 'primevue/fieldset';
import Avatar from 'primevue/avatar';



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
const emit = defineEmits(['retry']);

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
  const base_classes = "flex max-w-full px-4 pt-2 py-3 inline-size-min rounded-md border bg-surface-0 dark:bg-surface-900 " +
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
</script>



<template>
  <div class="conversations-container flex flex-col gap-y-10 max-w-full">
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
    <div class="flex justify-end">
        <Button @click="is_settings_visible = true" icon="pi pi-cog" />
        <Dialog v-model:visible="is_settings_visible" modal header="Settings"
                class="bg-[#f7f7f7] border-none min-w-[80vw] min-h-[70vh] justify-between"
                :pt="{content: {class: 'grow'}}"
                :pt-options="{mergeSections: true, mergeProps: true}"

        >
          <div class="h-full grid grid-cols-6 grid-rows-10 gap-4 mb-8">

            <label for="email" class="font-semibold w-24">User ID</label>
            <Inplace>
              <template #display>
                <Button label="Show" severity="secondary"/>
              </template>
              <template #content>
                <p class="m-0">
                  {{ user.id}}
                </p>
              </template>
            </Inplace>
          </div>
          <div class="flex justify-end gap-2">
            <Button type="button" label="Cancel" severity="secondary" @click="is_settings_visible = false"></Button>
            <Button type="button" label="Save" @click="is_settings_visible = false"></Button>
          </div>

        </Dialog>

    </div>
    <Fieldset v-for="conversation in conversations" :key="conversation.id"
              class="max-w-[80vw] overflow-x-clip"
              :pt="{
                root: {
                  class: get_fieldset_class(conversation.state),
                },
                toggleableContent: {
                  class: 'min-w-0 w-full px-3 flex flex-col gap-y-6'
                },
                content: {
                  class: 'w-full'
                }
              }"
              :ptOptions="{mergeSections: true, mergeProps:true}"
              >
      <template #legend>
        <span class="flex items-center justify-center gap-2">
          <span>
            <Avatar v-if="conversation.isAgent" shape="circle" class="bg-surface-700">
              <template #icon>
                <Icon name="mdi:robot" size="20" class="text-white"/>
              </template>
            </Avatar>
            <Avatar v-else :image="user_profile_image" shape="circle"/>
          </span>
        </span>
      </template>

      <div class="w-full min-w-0 flex flex-col gap-y-5 overflow-x-auto justify-between items-start">
        <div class="w-full min-w-0 flex flex-row justify-between items-center gap-x-6">
          <p class="text-md font-semibold overflow-x-auto min-w-0"> {{ conversation.message }}</p>
          <span class="p-1 flex-shrink-0">
            <Button icon="pi pi-clone" severity="info" text @click="copy(conversation.message)"/>
          </span>
        </div>
        <ReasoningContainer :message="conversation" class="w-full min-w-0"/>
      </div>
<!--      <div v-if="conversation?.stats && conversation.isAgent" class="flex w-full gap-x-3 rounded overflow-x-auto">-->
<!--      <Splitter class="w-full border-2 min-w-full">-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            &lt;!&ndash;              <p class="text-sm h-fit text-gray-500">Total Tokens</p>&ndash;&gt;-->
<!--            <p class="font-semibold"> {{conversation.stats.name}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit text-gray-500">Total Tokens</p>-->
<!--            <p class="font-semibold"> {{conversation.stats.total_tokens}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="w-full flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit text-gray-500">Input Tokens</p>-->
<!--            <p class="font-semibold"> {{conversation.stats.prompt_tokens}}</p>-->

<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit text-gray-500">Output Tokens</p>-->
<!--            <p class="font-semibold"> {{conversation.stats.completion_tokens}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--        <SplitterPanel class="flex items-center justify-center min-w-[25%]">-->
<!--          <div class="flex justify-center items-center gap-x-1 p-2 rounded-lg">-->
<!--            <p class="text-sm h-fit w-fit text-gray-500 ">Total Cost</p>-->
<!--            <p class="font-semibold">$ {{conversation.stats.total_cost.toFixed(10)}}</p>-->
<!--          </div>-->
<!--        </SplitterPanel>-->
<!--      </Splitter>-->
<!--    </div>-->
    </Fieldset>
    <div v-if="isThinking" class="p-2 flex gap-x-2 items-center text-gray-500">
      <Icon name="svg-spinners:blocks-shuffle-3" size="24"/>
      <p class="text-lg"> Processing </p>
    </div>
    <ConversationsErrorHandler v-show="lastMessageErrored" @retry="retry_request"/>
  </div>
</template>

<style scoped>

</style>