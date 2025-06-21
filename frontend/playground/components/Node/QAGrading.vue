<script setup lang="ts">
import { computed } from 'vue';
import { Star } from 'lucide-vue-next';

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
});

const calculateScore = (score: number) => 5 - score;

const qaData = computed(() => {
  const aspects = ['completeness', 'relevance', 'specificity', 'overall'];
  const processedData = {};
  const nodeData = JSON.parse(props.node)
  aspects.forEach(aspect => {
    if (nodeData[aspect] && typeof nodeData[aspect].score === 'number') {
      processedData[aspect] = {
        name: aspect.charAt(0).toUpperCase() + aspect.slice(1),
        score: calculateScore(nodeData[aspect].score),
        reason: nodeData[aspect].reason || 'No reason provided'
      };
    }
  });

  processedData.should_enrich = nodeData.should_enrich ?? false;

  return processedData;
});

const aspects = computed(() => Object.keys(qaData.value).filter(key => key !== 'should_enrich'));

// Helper function to generate star array for rating
const getStarArray = (score: number) => {
  return Array.from({ length: 5 }, (_, index) => index < score);
};
</script>

<template>
  <div class="p-4">
    <div v-if="aspects.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="aspect in aspects" :key="aspect" class="mb-4">
        <h3 class="text-lg font-semibold mb-2">{{ qaData[aspect].name }}</h3>
        <div class="flex items-center mb-2">
          <div class="flex items-center gap-1">
            <Star
              v-for="(filled, index) in getStarArray(qaData[aspect].score)"
              :key="index"
              :class="filled ? 'text-yellow-400 fill-current' : 'text-gray-300'"
              class="w-5 h-5"
          />
          </div>
          <span class="ml-2 text-sm text-gray-600">{{ qaData[aspect].score }}/5</span>
        </div>
        <p class="text-sm text-gray-700">{{ qaData[aspect].reason }}</p>
      </div>
    </div>
    <div v-else class="text-gray-600">No QA data available.</div>
    <div class="mt-4">
      <h3 class="text-lg font-semibold mb-2">Enrichment Needed</h3>
      <p class="text-sm text-gray-700">
        {{ qaData.should_enrich ? 'Yes' : 'No' }}
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Add any additional custom styles here */
</style>