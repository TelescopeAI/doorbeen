<script setup lang="ts">
import { ref, onMounted } from 'vue';

const props = defineProps({
  node: {
    type: [Object, String],
    required: true
  }
});

const nodeData = ref<any>(null);

onMounted(() => {
  console.log('InterpretInput - Raw props.node:', props.node);
  console.log('InterpretInput - Type of props.node:', typeof props.node);
  
  try {
    if (typeof props.node === 'string') {
      console.log('InterpretInput - Attempting to parse string:', props.node);
      nodeData.value = JSON.parse(props.node);
    } else {
      console.log('InterpretInput - Using object directly:', props.node);
      nodeData.value = props.node;
    }
    console.log('InterpretInput - Final nodeData:', nodeData.value);
  } catch (error) {
    console.error('InterpretInput - Error parsing node data:', error);
    console.error('InterpretInput - Raw data that failed to parse:', props.node);
    nodeData.value = props.node; // Fallback to original node if parsing fails
  }
});
</script>

<template>
  <div class="prose-dense text-density-high">
    <div v-if="nodeData" class="conversation-dense">
              <div class="mb-3">
          <h3 class="text-lg font-semibold mb-1">Objective</h3>
          <p class="text-gray-600">{{ nodeData.objective }}</p>
        </div>

      <div class="mb-3" v-if="nodeData.plan && nodeData.plan.groups">
        <h3 class="text-xl font-semibold mb-2">Analysis Plan</h3>
        <ol class="list-decimal list-inside">
          <li v-for="(group, index) in nodeData.plan.groups" :key="index" class="mb-2">
            <span class="font-semibold">{{ group.name }}:</span>
            <ul class="list-disc list-inside ml-4">
              <li v-for="task in group.tasks" :key="task.name">
                {{ task.operation }}
              </li>
            </ul>
          </li>
        </ol>
      </div>

      <div class="mb-6">
        <h3 class="text-xl font-semibold mb-2">Reasoning</h3>
        <p class="text-gray-600">{{ nodeData.reasoning }}</p>
      </div>

      <div v-if="nodeData.tests && nodeData.tests.length > 0">
        <h3 class="text-xl font-semibold mb-2">Validation Tests</h3>
        <ul class="list-disc list-inside">
          <li v-for="(test, index) in nodeData.tests" :key="index" class="mb-1">
            {{ test }}
          </li>
        </ul>
      </div>

      <div v-if="nodeData.operations && nodeData.operations.length > 0">
        <h3 class="text-xl font-semibold mb-2">Operations</h3>
        <ul class="list-disc list-inside">
          <li v-for="(operation, index) in nodeData.operations" :key="index" class="mb-1">
            {{ operation }}
          </li>
        </ul>
      </div>
    </div>

    <div v-else class="text-center text-gray-500">
      Loading interpretation data...
    </div>
  </div>
</template>

<style scoped>
@media (max-width: 640px) {
  .text-2xl {
    font-size: 1.5rem;
  }
  .text-xl {
    font-size: 1.25rem;
  }
}
</style>