<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { Badge } from '~/components/ui/badge';
import { MessageCircle, CheckCircle, XCircle, Info } from 'lucide-vue-next';

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
</script>

<template>
  <div class="input-followup bg-gray-50 p-4 rounded-lg">
    <div v-if="nodeData" class="space-y-4">
      
      <!-- Followup Status -->
      <div class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-indigo-600 mb-3 flex items-center">
          <MessageCircle class="w-5 h-5 mr-2" />
          Follow-up Analysis
        </h3>
        
        <!-- Direct Answer Check -->
        <div v-if="nodeData.can_answer_directly !== undefined" class="mb-4">
          <div class="flex items-center mb-2">
            <CheckCircle v-if="nodeData.can_answer_directly" class="w-5 h-5 text-green-500 mr-2" />
            <XCircle v-else class="w-5 h-5 text-red-500 mr-2" />
            <span class="font-medium">
              {{ nodeData.can_answer_directly ? 'Can answer directly from context' : 'Requires additional processing' }}
            </span>
          </div>
          
          <div v-if="nodeData.can_answer_directly" class="bg-green-50 p-3 rounded border-l-4 border-green-400">
            <p class="text-sm text-green-700">This follow-up question can be answered using previous conversation context.</p>
          </div>
          <div v-else class="bg-orange-50 p-3 rounded border-l-4 border-orange-400">
            <p class="text-sm text-orange-700">This question needs further analysis and data processing.</p>
          </div>
        </div>

        <!-- Context Analysis -->
        <div v-if="nodeData.context_analysis" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Context Analysis:</h4>
          <div class="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
            <p class="text-sm text-gray-700">{{ nodeData.context_analysis }}</p>
          </div>
        </div>

        <!-- Follow-up Type -->
        <div v-if="nodeData.followup_type" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Question Type:</h4>
          <Badge variant="secondary" class="px-3 py-1">
            {{ nodeData.followup_type }}
          </Badge>
        </div>

        <!-- Reasoning -->
        <div v-if="nodeData.reasoning" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Analysis Reasoning:</h4>
          <div class="bg-gray-50 p-3 rounded">
            <p class="text-sm text-gray-700">{{ nodeData.reasoning }}</p>
          </div>
        </div>

        <!-- Next Steps -->
        <div v-if="nodeData.next_steps" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Next Steps:</h4>
          <div class="bg-purple-50 p-3 rounded border-l-4 border-purple-400">
            <p class="text-sm text-gray-700">{{ nodeData.next_steps }}</p>
          </div>
        </div>

      </div>
    </div>
    
    <div v-else class="text-center text-gray-500">
      <Alert>
        <Info class="h-4 w-4" />
        <AlertDescription>
        Analyzing follow-up question...
        </AlertDescription>
      </Alert>
    </div>
  </div>
</template>

<style scoped>
.input-followup {
  max-width: 100%;
}
</style> 