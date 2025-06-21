<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Card, CardContent, CardTitle } from '~/components/ui/card';
import { Badge } from '~/components/ui/badge';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { BarChart3, TrendingUp, Settings, Eye, Info } from 'lucide-vue-next';

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
  <div class="query-visualization bg-gray-50 p-4 rounded-lg">
    <div v-if="nodeData" class="space-y-6">
      
      <!-- Visualization Plan -->
      <div v-if="nodeData.visualization_plan" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-purple-600 mb-3 flex items-center">
          <BarChart3 class="w-5 h-5 mr-2" />
          Visualization Plan
        </h3>
        
        <!-- Chart Type -->
        <div v-if="nodeData.visualization_plan.chart_type" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Recommended Chart Type:</h4>
          <Badge variant="default" class="px-3 py-1 text-lg">
            {{ nodeData.visualization_plan.chart_type }}
          </Badge>
        </div>

        <!-- Chart Description -->
        <div v-if="nodeData.visualization_plan.description" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Chart Description:</h4>
          <div class="bg-purple-50 p-3 rounded border-l-4 border-purple-400">
            <p class="text-sm text-gray-700">{{ nodeData.visualization_plan.description }}</p>
          </div>
        </div>

        <!-- X and Y Axis -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div v-if="nodeData.visualization_plan.x_axis">
            <h4 class="font-medium text-gray-700 mb-2">X-Axis:</h4>
            <div class="bg-blue-50 p-3 rounded">
              <p class="text-sm font-medium text-blue-700">{{ nodeData.visualization_plan.x_axis.column }}</p>
              <p class="text-xs text-blue-600">{{ nodeData.visualization_plan.x_axis.type }}</p>
            </div>
          </div>
          
          <div v-if="nodeData.visualization_plan.y_axis">
            <h4 class="font-medium text-gray-700 mb-2">Y-Axis:</h4>
            <div class="bg-green-50 p-3 rounded">
              <p class="text-sm font-medium text-green-700">{{ nodeData.visualization_plan.y_axis.column }}</p>
              <p class="text-xs text-green-600">{{ nodeData.visualization_plan.y_axis.type }}</p>
            </div>
          </div>
        </div>

        <!-- Aggregations -->
        <div v-if="nodeData.visualization_plan.aggregations && nodeData.visualization_plan.aggregations.length > 0" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Data Aggregations:</h4>
          <div class="flex flex-wrap gap-2">
            <Badge 
              v-for="agg in nodeData.visualization_plan.aggregations" 
              :key="agg"
              variant="secondary"
              class="px-2 py-1"
            >
              {{ agg }}
            </Badge>
          </div>
        </div>

        <!-- Color Coding -->
        <div v-if="nodeData.visualization_plan.color_by" class="mb-4">
          <h4 class="font-medium text-gray-700 mb-2">Color Coding:</h4>
          <div class="bg-orange-50 p-3 rounded">
            <p class="text-sm text-orange-700">Group by: {{ nodeData.visualization_plan.color_by }}</p>
          </div>
        </div>
      </div>

      <!-- Chart Recommendations -->
      <div v-if="nodeData.chart_recommendations && nodeData.chart_recommendations.length > 0" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-blue-600 mb-3 flex items-center">
          <TrendingUp class="w-5 h-5 mr-2" />
          Alternative Chart Options
        </h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card 
            v-for="(rec, index) in nodeData.chart_recommendations" 
            :key="index"
            class="p-3 border border-gray-200"
          >
            <CardTitle>
              <span class="text-sm font-medium">{{ rec.type }}</span>
            </CardTitle>
            <CardContent>
              <p class="text-xs text-gray-600 mb-2">{{ rec.description }}</p>
              <Badge variant="secondary" class="text-xs">
                {{ rec.suitability || 'Good' }}
              </Badge>
            </CardContent>
          </Card>
        </div>
      </div>

      <!-- Visualization Settings -->
      <div v-if="nodeData.visualization_settings" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-gray-600 mb-3 flex items-center">
          <Settings class="w-5 h-5 mr-2" />
          Visualization Settings
        </h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Title and Labels -->
          <div>
            <h4 class="font-medium text-gray-700 mb-2">Chart Labels:</h4>
            <div class="space-y-2">
              <div v-if="nodeData.visualization_settings.title" class="text-sm">
                <span class="font-medium">Title:</span> {{ nodeData.visualization_settings.title }}
              </div>
              <div v-if="nodeData.visualization_settings.x_label" class="text-sm">
                <span class="font-medium">X-Label:</span> {{ nodeData.visualization_settings.x_label }}
              </div>
              <div v-if="nodeData.visualization_settings.y_label" class="text-sm">
                <span class="font-medium">Y-Label:</span> {{ nodeData.visualization_settings.y_label }}
              </div>
            </div>
          </div>

          <!-- Display Options -->
          <div v-if="nodeData.visualization_settings.options">
            <h4 class="font-medium text-gray-700 mb-2">Display Options:</h4>
            <div class="flex flex-wrap gap-2">
              <Badge 
                v-for="(value, key) in nodeData.visualization_settings.options" 
                :key="key"
                variant="secondary"
                class="text-xs px-2 py-1"
              >
                {{ key }}: {{ value }}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Preview for Chart -->
      <div v-if="nodeData.data_preview" class="bg-white p-4 rounded-md shadow">
        <h3 class="text-lg font-semibold text-green-600 mb-3 flex items-center">
          <Eye class="w-5 h-5 mr-2" />
          Data Preview for Visualization
        </h3>
        
        <div class="bg-gray-50 p-3 rounded overflow-x-auto">
          <pre class="text-xs text-gray-700">{{ JSON.stringify(nodeData.data_preview, null, 2) }}</pre>
        </div>
      </div>

    </div>
    
    <div v-else class="text-center text-gray-500">
      <Alert>
        <Info class="h-4 w-4" />
        <AlertDescription>
        Planning data visualization...
        </AlertDescription>
      </Alert>
    </div>
  </div>
</template>

<style scoped>
.query-visualization {
  max-height: 80vh;
  overflow-y: auto;
}

pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  line-height: 1.4;
  max-height: 200px;
  overflow-y: auto;
}
</style> 