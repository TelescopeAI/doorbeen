<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
});

const nodeData = computed(() => JSON.parse(props.node));
</script>

<template>
  <div class="">
    <div class="mb-6">
      <h3 class="text-xl font-semibold mb-2">Objective</h3>
      <p class="text-gray-600">{{ nodeData.objective }}</p>
    </div>

    <div class="mb-6">
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

    <div>
      <h3 class="text-xl font-semibold mb-2">Validation Tests</h3>
      <ul class="list-disc list-inside">
        <li v-for="(test, index) in nodeData.tests" :key="index" class="mb-1">
          {{ test }}
        </li>
      </ul>
    </div>

    <div>
      <h3 class="text-xl font-semibold mb-2">Operations</h3>
      <ul class="list-disc list-inside">
        <li v-for="(operation, index) in nodeData.operations" :key="index" class="mb-1">
          {{ operation }}
        </li>
      </ul>
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