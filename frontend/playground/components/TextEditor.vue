<script setup lang="ts">
import { Input } from '@/components/ui/input'

const props = defineProps({
  initial_content: {
    type: String,
    default: ""
  },
  placeholder: {
    type: String,
    default: 'Ask away....'
  }
});

const emit = defineEmits(['contentUpdated', 'contentReady']);

const inputValue = ref(props.initial_content);

// Watch for changes in input value and emit contentUpdated
watch(inputValue, (newValue) => {
  emit('contentUpdated', newValue);
});

// Handle Enter key press
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    console.log("Enter Pressed");
    emit('contentReady', inputValue.value);
    inputValue.value = ''; // Clear content after Enter
  }
};

// Watch for changes in initial_content prop
watch(() => props.initial_content, (newVal) => {
  inputValue.value = newVal;
});
</script>

<template>
  <Input 
    v-model="inputValue"
    :placeholder="placeholder"
    class="h-full w-full p-2 focus:outline-none"
    @keydown="handleKeydown"
  />
</template>

<style scoped>
/* Styles removed as they were TipTap specific */
</style>
