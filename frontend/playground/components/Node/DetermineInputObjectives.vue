<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Card, CardContent } from '~/components/ui/card';
import { Badge } from '~/components/ui/badge';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { 
  Target, 
  List, 
  Settings, 
  FileText, 
  CheckCircle, 
  Star, 
  Tags, 
  AlertTriangle, 
  Info 
} from 'lucide-vue-next';

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
  <div class="determine-objectives bg-gray-50 p-4 rounded-lg">
    <div v-if="nodeData" class="space-y-6">
      
      <!-- Primary Objectives -->
      <div v-if="nodeData.primary_objectives && nodeData.primary_objectives.length > 0" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-blue-600 mb-3 flex items-center">
          <Target class="w-5 h-5 mr-2" />
          Primary Objectives
        </h3>
        
        <div class="space-y-3">
          <div 
            v-for="(objective, index) in nodeData.primary_objectives" 
            :key="index"
            class="bg-blue-50 p-3 rounded border-l-4 border-blue-400"
          >
            <div class="flex items-start">
              <span class="bg-blue-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center mr-3 mt-0.5">
                {{ index + 1 }}
              </span>
              <div class="flex-1">
                <p class="text-sm text-gray-700">{{ objective.description || objective }}</p>
                <div v-if="objective.priority" class="mt-2">
                  <Badge variant="secondary" class="text-xs">
                    Priority: {{ objective.priority }}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Secondary Objectives -->
      <div v-if="nodeData.secondary_objectives && nodeData.secondary_objectives.length > 0" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-green-600 mb-3 flex items-center">
          <List class="w-5 h-5 mr-2" />
          Secondary Objectives
        </h3>
        
        <div class="space-y-2">
          <div 
            v-for="(objective, index) in nodeData.secondary_objectives" 
            :key="index"
            class="bg-green-50 p-3 rounded border-l-4 border-green-400"
          >
            <p class="text-sm text-gray-700">{{ objective.description || objective }}</p>
          </div>
        </div>
      </div>

      <!-- Analysis Strategy -->
      <div v-if="nodeData.analysis_strategy" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-purple-600 mb-3 flex items-center">
          <Settings class="w-5 h-5 mr-2" />
          Analysis Strategy
        </h3>
        
        <div class="bg-purple-50 p-3 rounded border-l-4 border-purple-400">
          <p class="text-sm text-gray-700">{{ nodeData.analysis_strategy }}</p>
        </div>
      </div>

      <!-- Expected Deliverables -->
      <div v-if="nodeData.expected_deliverables && nodeData.expected_deliverables.length > 0" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-orange-600 mb-3 flex items-center">
          <FileText class="w-5 h-5 mr-2" />
          Expected Deliverables
        </h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Card 
            v-for="(deliverable, index) in nodeData.expected_deliverables" 
            :key="index"
            class="p-3 border border-gray-200"
          >
            <CardContent>
              <div class="flex items-center">
                <CheckCircle class="w-4 h-4 text-green-500 mr-2" />
                <span class="text-sm">{{ deliverable.type || deliverable }}</span>
              </div>
              <p v-if="deliverable.description" class="text-xs text-gray-600 mt-1">
                {{ deliverable.description }}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <!-- Success Criteria -->
      <div v-if="nodeData.success_criteria && nodeData.success_criteria.length > 0" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-red-600 mb-3 flex items-center">
          <Star class="w-5 h-5 mr-2" />
          Success Criteria
        </h3>
        
        <div class="space-y-2">
          <div 
            v-for="(criteria, index) in nodeData.success_criteria" 
            :key="index"
            class="flex items-start bg-red-50 p-3 rounded"
          >
            <Star class="w-4 h-4 text-red-500 mr-2 mt-0.5 fill-current" />
            <p class="text-sm text-gray-700">{{ criteria.description || criteria }}</p>
          </div>
        </div>
      </div>

      <!-- Question Classification -->
      <div v-if="nodeData.question_type || nodeData.complexity_level" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-gray-600 mb-3 flex items-center">
          <Tags class="w-5 h-5 mr-2" />
          Question Classification
        </h3>
        
        <div class="flex flex-wrap gap-3">
          <div v-if="nodeData.question_type">
            <Badge variant="secondary" class="px-3 py-1">
              Type: {{ nodeData.question_type }}
            </Badge>
          </div>
          <div v-if="nodeData.complexity_level">
            <Badge variant="outline" class="px-3 py-1">
              Complexity: {{ nodeData.complexity_level }}
            </Badge>
          </div>
          <div v-if="nodeData.estimated_effort">
            <Badge variant="secondary" class="px-3 py-1">
              Effort: {{ nodeData.estimated_effort }}
            </Badge>
          </div>
        </div>
      </div>

      <!-- Key Constraints -->
      <div v-if="nodeData.constraints && nodeData.constraints.length > 0" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-yellow-600 mb-3 flex items-center">
          <AlertTriangle class="w-5 h-5 mr-2" />
          Key Constraints
        </h3>
        
        <div class="space-y-2">
          <div 
            v-for="(constraint, index) in nodeData.constraints" 
            :key="index"
            class="bg-yellow-50 p-3 rounded border-l-4 border-yellow-400"
          >
            <p class="text-sm text-gray-700">{{ constraint.description || constraint }}</p>
          </div>
        </div>
      </div>

    </div>
    
    <div v-else class="text-center text-gray-500">
      <Alert>
        <Info class="h-4 w-4" />
        <AlertDescription>
        Determining analysis objectives...
        </AlertDescription>
      </Alert>
    </div>
  </div>
</template>

<style scoped>
.determine-objectives {
  max-height: 80vh;
  overflow-y: auto;
}
</style> 