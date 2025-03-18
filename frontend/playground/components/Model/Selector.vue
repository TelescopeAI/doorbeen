<script setup lang="ts">

import { useStorage } from "@vueuse/core";

const props = defineProps({
  variant: {
    type: String,
    default: 'gpt-4o'
  },
  api_key: {
    type: String,
    default: ""
  }
})

const models = reactive([
  {maker: 'OpenAI',  options: [], icon: 'logos:openai-icon'},
  {maker: 'Anthropic', disabled: true, value: 'postgresql', icon: 'logos:anthropic-icon'},
  {maker: 'Mistral', disabled: true, value: 'mysql', icon: "logos:mistral-ai-icon"},
  {maker: 'HuggingFace', disabled: true, value: 'oracle', icon: 'logos:hugging-face-icon'},
]);
const model_versions = [
  {
    name: 'gpt-4o-mini',
    value: 'gpt-4o-mini',
    expense: 'CHEAP'
  },
  {
    name: 'gpt-4o',
    value: 'gpt-4o',
    expense: 'EXPENSIVE'
  },
  {
    name: 'gpt-4-turbo',
    value: 'gpt-4-turbo',
    expense: 'MODERATE'
  }, {
    name: 'gpt-4-turbo-preview',
    value: 'gpt-4-turbo-preview',
    expense: 'MODERATE'
  }, {
    name: 'gpt-4-0125-preview',
    value: 'gpt-4-0125-preview',
    expense: 'MODERATE'
  }, {
    name: 'gpt-4',
    value: 'gpt-4',
    expense: 'MODERATE'
  }, {
    name: 'gpt-3.5-turbo',
    value: 'gpt-3.5-turbo',
    expense: 'CHEAP'
  }
]
const emit = defineEmits(['modelConfigUpdated', 'modelConfigAvailableInStorage'])

const stored_model_config = useStorage('model-config', {});
const model_config = reactive(stored_model_config.value)
emit('modelConfigUpdated', model_config)

if (Object.keys(stored_model_config.value).length > 0) {
  emit('modelConfigAvailableInStorage', true)
}


const model_toggle = ref(null)
const { width } = useElementSize(model_toggle)
const isMobileMode = computed(() => width.value < 650)



const db_form = ref(null)
const save_model_config = () => {
  const node = db_form?.value.node
  node.submit()
}
const db_form_submit_handler = async (formData: Object) => {
  emit('modelConfigUpdated', formData)
  stored_model_config.value = formData
  console.log("Model Form Submitted ", formData)
}

const handleIconClick = (node, e) => {
  node.props.suffixIcon = node.props.suffixIcon === 'eye' ? 'eyeClosed' : 'eye'
  node.props.type = node.props.type === 'password' ? 'text' : 'password'
}

const evaluate_expense = (expense: string) => {
  const evaluation = {
    color: "bg-green-900",
    count: 1
  }
  if (expense === 'EXPENSIVE') {
    evaluation.count = 2
    evaluation.color = 'text-red-300'
  } else if (expense === 'MODERATE') {
    evaluation.count = 1
    evaluation.color = 'text-amber-500'
  } else if (expense === 'CHEAP') {
    evaluation.count = 1
    evaluation.color = 'text-green-500'
  }
  return evaluation
}
</script>

<template>
  <div class="w-full flex flex-col gap-y-6">
    <div>
      <FormKit
          type="form"
          id="model_config_form"
          ref="db_form"
          submit-label="Save"
          outer-class="flex"
          :submit-attrs="{
                      outerClass: 'flex flex-row',
                      wrapperClass: 'flex justify-center',
                      ignore: false
                }"
          @submit="db_form_submit_handler"
          :actions="false"
      >


        <FormKit
            type="togglebuttons"
            :options="models"
            ref="model_toggle"
            wrapper-class="w-full"
            outer-class="max-w-full"
            options-class="w-full wrap"
            singleToggle-class="bg-slate-50"
            :ignore="true"
            :vertical="isMobileMode"
        >
          <template #default="context">
            <div class="flex gap-x-3 justify-center items-center w-full text-nowrap">
              <Icon :name="context.option.icon" size="24"/>

              {{ context.option.maker }}
            </div>

          </template>
        </FormKit>
        <FormKit
            id="model-version-selector"
            type="dropdown"
            name="name"
            label="Variant"
            placeholder="Models"
            outer-class="max-w-full"
            :options="model_versions"
            :value="model_config.name"
        >
          <template #option="{ option, classes }">
            <div :class="`${classes.option} min-w-full flex items-center justify-between`">
              {{ option.name }}

              <span class="pr-5">
                <Icon name="bx:bxs-badge-dollar" size="16" v-for="expense in evaluate_expense(option.expense).count"
                      :class="`${evaluate_expense(option.expense).color}`" class="drop-shadow"/>
        </span>
            </div>
          </template>
        </FormKit>
        <FormKit
            type="password"
            name="api_key"
            label="API Key"
            prefix-icon="password"
            suffix-icon="eyeClosed"
            @suffix-icon-click="handleIconClick"
            suffix-icon-class="hover:text-blue-500"
            outer-class="max-w-full"
            :value="model_config.api_key"
        />
      </FormKit>
      <FormKit type="button" @click="save_model_config">Save</FormKit>
    </div>

  </div>

</template>

<style scoped>

</style>