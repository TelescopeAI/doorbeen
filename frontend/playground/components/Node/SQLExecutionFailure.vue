<script setup lang="ts">
import { ref, onMounted } from 'vue';

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
});

const nodeData = ref(null);

onMounted(() => {
  try {
    nodeData.value = typeof props.node === 'string' ? JSON.parse(props.node) : props.node;
  } catch (error) {
    console.error('Error parsing node data:', error);
  }
});

function formatTitle(key: string): string {
  return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}
</script>

<template>
  <div class="sql-execution-failure bg-gray-100 p-4 rounded-lg shadow-md max-w-4xl mx-auto">
    <div v-if="nodeData" class="space-y-6">
      <div v-for="(value, key) in nodeData" :key="key" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">{{ formatTitle(key) }}</h3>
        <pre v-if="key.includes('query')" class="bg-gray-50 p-3 rounded overflow-x-auto">
          <code class="text-sm">{{ value }}</code>
        </pre>
        <p v-else class="text-gray-700">{{ value }}</p>
      </div>
    </div>
    <div v-else class="text-red-500 font-semibold">
      Failed to load SQL execution failure data.
    </div>
  </div>
</template>

<style scoped>

</style>
