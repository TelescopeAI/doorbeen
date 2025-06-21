<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Badge } from '~/components/ui/badge';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { Search, History, Info } from 'lucide-vue-next';

const props = defineProps({
  node: {
    type: [Object, String],
    required: true
  }
});

const nodeData = ref<any>(null);

onMounted(() => {
  try {
    nodeData.value = typeof props.node === 'string' ? JSON.parse(props.node) : props.node;
  } catch (error) {
    console.error('Error parsing node data:', error);
  }
});

// Helper functions for the template
const getQuestionTypeDisplay = () => {
  if (!nodeData.value) return 'Unknown';
  
  // Show "Related Question" only when there's actually a recall reference
  if (nodeData.value.question_type === 'related' && nodeData.value.recall_reference) {
    return 'Related Question';
  } else if (nodeData.value.question_type === 'new' || !nodeData.value.recall_reference) {
    return 'New Question';
  } else {
    return 'New Question'; // Default fallback
  }
};

const getQuestionTypeVariant = () => {
  if (!nodeData.value) return 'secondary';
  
  // Only show as 'secondary' (blue) if there's actually a recall reference
  if (nodeData.value.question_type === 'related' && nodeData.value.recall_reference) {
    return 'secondary';
  } else {
    return 'default'; // Default for new questions
  }
};

const getConfidenceVariant = (level: string) => {
  switch(level?.toLowerCase()) {
    case 'high': return 'default';
    case 'medium': return 'secondary'; 
    case 'low': return 'destructive';
    default: return 'outline';
  }
};
</script>

<template>
  <div class="new-or-followup bg-gray-50 p-4 rounded-lg">
    <div v-if="nodeData" class="space-y-4">
      
      <!-- Question Type Determination -->
      <div class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-blue-600 mb-3 flex items-center">
          <Search class="w-5 h-5 mr-2" />
          Question Analysis
        </h3>
        
        <!-- Question Type with intelligent classification -->
        <div v-if="nodeData.question_type !== undefined" class="mb-4">
          <div class="flex items-center mb-2">
            <span class="font-medium text-gray-700 mr-2">Question Type:</span>
            <Badge :variant="getQuestionTypeVariant()">
              {{ getQuestionTypeDisplay() }}
            </Badge>
          </div>
        </div>

        <!-- Recall Reference - Only show when there's a meaningful connection -->
        <div v-if="nodeData.recall_reference" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2 flex items-center">
            <History class="w-4 h-4 mr-2 text-blue-500" />
            Recall Reference:
          </h4>
          <div class="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
            <p class="text-sm text-blue-700">{{ nodeData.recall_reference }}</p>
          </div>
        </div>

        <!-- Context Analysis -->
        <div v-if="nodeData.context_analysis" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Context Analysis:</h4>
          <div class="bg-gray-50 p-3 rounded border-l-4 border-gray-400">
            <p class="text-sm text-gray-700">{{ nodeData.context_analysis }}</p>
          </div>
        </div>

        <!-- Confidence Level -->
        <div v-if="nodeData.confidence_level" class="mb-4">
          <div class="flex items-center">
            <span class="font-medium text-gray-700 mr-2">Confidence:</span>
            <Badge :variant="getConfidenceVariant(nodeData.confidence_level)">
              {{ nodeData.confidence_level.toUpperCase() }}
            </Badge>
          </div>
        </div>

        <!-- Database Context -->
        <div v-if="nodeData.database_context" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Database Context:</h4>
          <div class="bg-green-50 p-3 rounded border-l-4 border-green-400">
            <p class="text-sm text-green-700">{{ nodeData.database_context }}</p>
          </div>
        </div>

        <!-- Available Tables (if exists from legacy data) -->
        <div v-if="nodeData.available_tables && nodeData.available_tables.length > 0" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Available Tables:</h4>
          <div class="flex flex-wrap gap-2">
            <Badge 
              v-for="table in nodeData.available_tables.slice(0, 10)" 
              :key="table"
              variant="secondary"
            >
              {{ table }}
            </Badge>
            <Badge 
              v-if="nodeData.available_tables.length > 10"
              variant="secondary"
            >
              +{{ nodeData.available_tables.length - 10 }} more
            </Badge>
          </div>
        </div>

      </div>
    </div>
    
    <div v-else class="text-center text-gray-500">
      <Alert>
        <Info class="h-4 w-4" />
        <AlertDescription>
        Analyzing question context...
        </AlertDescription>
      </Alert>
    </div>
  </div>
</template>



<style scoped>
.new-or-followup {
  max-width: 100%;
}
</style>