<script setup lang="ts">
import {onMounted, ref} from "vue";
import Tag from "primevue/tag";

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
  <div class="flex gap-x-4 items-center justify-center">
    <pre class="bg-gray-50 p-3 rounded overflow-x-auto">
          <code class="text-sm">{{ nodeData?.query }}</code>
  </pre>
  </div>
</template>

<style scoped>

</style>