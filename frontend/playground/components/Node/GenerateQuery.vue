<script setup lang="ts">
import Tag from 'primevue/tag';
import {ref} from "vue";

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})
const nodeData = ref<any>(null);

onMounted(() => {
  try {
    nodeData.value = typeof props.node === 'string' ? JSON.parse(props.node) : props.node;
  } catch (error) {
    console.error('Error parsing node data:', error);
  }
});
</script>

<template>
<div class="flex gap-x-4 w-full items-center justify-center">
  <pre class="bg-gray-50 p-3 rounded max-w-full wrap">
          <code class="text-sm max-w-screen-lg">{{ nodeData?.query }}</code>
  </pre>
</div>
</template>

<style scoped>

</style>