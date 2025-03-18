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
</script>

<template>
  <div class="">
    <div v-if="nodeData" class="space-y-6">
      <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-2 text-blue-600">Reframed Question</h3>
        <p class="text-gray-700">{{ nodeData.improved_input }}</p>
      </div>

      <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-2 text-yellow-600">Assumptions</h3>
        <ul class="space-y-4">
          <li v-for="(assumptions, category) in nodeData.assumptions" :key="category">
            <h4 class="font-semibold capitalize text-yellow-900 mb-2">{{ category }}</h4>
            <ul class="list-disc pl-5 space-y-2">
              <li v-for="(assumption, idx) in assumptions" :key="idx" class="text-gray-700">
                {{ assumption }}
              </li>
            </ul>
          </li>
        </ul>
      </div>

      <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-2 text-purple-600">Variations</h3>
        <ul class="list-disc pl-5">
          <li v-for="(variation, index) in nodeData.variations" :key="index" class="text-gray-700 mb-2">
            {{ variation }}
          </li>
        </ul>
      </div>
    </div>

    <div v-else class="text-center text-gray-500">
      No data available
    </div>
  </div>
</template>

<style scoped>
/* Add any additional component-specific styles here */
</style>