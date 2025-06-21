<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { Card, CardContent, CardTitle } from '~/components/ui/card';
import { Badge } from '~/components/ui/badge';

const props = defineProps({
  node: {
    type: [Object, String],
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

const objectiveStatus = computed(() => {
  const metCount = nodeData.value?.query?.met_reasons?.length || 0;
  const unmetCount = nodeData.value?.query?.unmet_reasons?.length || 0;

  if (metCount === 0 && unmetCount > 0) {
    return { text: 'No Objectives Met', variant: 'destructive' };
  } else if (metCount > 0 && unmetCount === 0) {
    return { text: 'All Objectives Met', variant: 'default' };
  } else if (metCount > 0 && unmetCount > 0) {
    return { text: 'Some Objectives Met', variant: 'secondary' };
  } else {
    return { text: 'Unknown Status', variant: 'outline' };
  }
});
</script>

<template>
  <div class="p-4">
    <Card class="mb-4">
      <CardContent>
        <div class="mb-4">
          <h3 class="text-lg font-semibold mb-2">Objective Status:</h3>
          <Badge :variant="objectiveStatus.variant" class="text-sm">
            {{ objectiveStatus.text }}
          </Badge>
        </div>
        <div v-if="nodeData?.query?.met_reasons?.length > 0" class="mb-4">
          <h3 class="text-lg font-semibold mb-2">Met Objectives:</h3>
          <ul class="list-disc pl-5">
            <li v-for="(reason, index) in nodeData.query.met_reasons" :key="index" class="text-sm">
              {{ reason }}
            </li>
          </ul>
        </div>
        <div v-if="nodeData?.query?.unmet_reasons?.length > 0" class="mb-4">
          <h3 class="text-lg font-semibold mb-2">Unmet Objectives:</h3>
          <ul class="list-disc pl-5">
            <li v-for="(reason, index) in nodeData.query.unmet_reasons" :key="index" class="text-sm">
              {{ reason }}
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardTitle>
        <h2 class="text-xl font-bold">Insights</h2>
      </CardTitle>
      <CardContent>
        <ul class="list-disc pl-5">
          <li v-for="(insight, index) in nodeData?.insights" :key="index" class="text-sm mb-2">
            {{ insight }}
          </li>
        </ul>
        <div v-if="nodeData?.next_step" class="mt-4">
          <h3 class="text-lg font-semibold mb-2">Next Step:</h3>
          <p class="text-sm">{{ nodeData.next_step }}</p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>

</style>