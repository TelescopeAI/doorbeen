<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { Card, CardContent, CardTitle } from '~/components/ui/card';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { Badge } from '~/components/ui/badge';
import { 
  AlertTriangle, 
  CheckCircle, 
  Info, 
  Shield, 
  Check, 
  X 
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
    if (typeof props.node === 'string') {
      nodeData.value = JSON.parse(props.node);
    } else {
      nodeData.value = props.node;
    }
  } catch (error) {
    console.error('Error parsing stream termination data:', error);
    nodeData.value = props.node;
  }
});

const terminationInfo = computed(() => {
  if (!nodeData.value) return null;
  
  return {
    complete: nodeData.value.streaming_complete || false,
    reason: nodeData.value.termination_reason || 'Unknown',
    eventsProcessed: nodeData.value.total_events_processed || 'N/A',
    circuitBreaker: nodeData.value.circuit_breaker_triggered || false,
    lastNode: nodeData.value.last_node_processed || 'Unknown'
  };
});

const getStatusInfo = computed(() => {
  if (!terminationInfo.value) return null;
  
  const info = terminationInfo.value;
  
  if (info.circuitBreaker || info.reason === 'circuit_breaker_triggered') {
    return {
      variant: 'destructive',
      icon: AlertTriangle,
      title: 'Analysis Stopped - Protection Activated',
      message: 'The system activated protective measures after encountering repeated technical challenges.',
      description: 'This prevents infinite processing loops and preserves system resources.'
    };
  }
  
  if (info.reason === 'graph_completed' && info.complete) {
    return {
      variant: 'default',
      icon: CheckCircle,
      title: 'Analysis Completed Successfully',
      message: 'All analysis steps have been completed successfully.',
      description: 'The system has finished processing your request and generated results.'
    };
  }
  
  if (info.reason === 'no_events_processed') {
    return {
      variant: 'default',
      icon: Info,
      title: 'No Processing Required',
      message: 'The request was handled without requiring complex analysis steps.',
      description: 'This typically happens for simple queries or cached results.'
    };
  }
  
  return {
    variant: 'default',
    icon: Info,
    title: 'Analysis Stream Ended',
    message: 'The analysis process has concluded.',
    description: 'Processing completed with partial results or early termination.'
  };
});
</script>

<template>
  <div class="stream-termination-container">
    <div v-if="terminationInfo && getStatusInfo" class="termination-display">
      <Card>
        <CardTitle>
          <div class="flex items-center gap-3">
            <component 
              :is="getStatusInfo.icon"
              :class="{
                'text-green-500': getStatusInfo.variant === 'default' && getStatusInfo.icon === CheckCircle,
                'text-red-500': getStatusInfo.variant === 'destructive',
                'text-orange-500': getStatusInfo.variant === 'default' && getStatusInfo.title.includes('No Processing'),
                'text-blue-500': getStatusInfo.variant === 'default' && !getStatusInfo.title.includes('No Processing') && getStatusInfo.icon !== CheckCircle
              }"
              class="w-5 h-5"
            />
            <span>{{ getStatusInfo.title }}</span>
          </div>
        </CardTitle>
        
        <CardContent>
          <div class="space-y-4">
            <!-- Main Status Message -->
            <Alert 
              :variant="getStatusInfo.variant"
              class="mb-3"
            >
              <component :is="getStatusInfo.icon" class="h-4 w-4" />
              <AlertDescription>{{ getStatusInfo.message }}</AlertDescription>
            </Alert>
            
            <!-- Status Details -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="status-detail">
                <span class="font-medium text-gray-700 dark:text-gray-300">Status:</span>
                <Badge 
                  :variant="(getStatusInfo.variant === 'destructive' ? 'destructive' : 'default') as 'destructive' | 'default'"
                  class="ml-2"
                >
                  {{ terminationInfo.reason.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) }}
                </Badge>
              </div>
              
              <div v-if="terminationInfo.eventsProcessed !== 'N/A'" class="status-detail">
                <span class="font-medium text-gray-700 dark:text-gray-300">Events Processed:</span>
                <Badge 
                  variant="secondary"
                  class="ml-2"
                >
                  {{ terminationInfo.eventsProcessed }}
                </Badge>
              </div>
              
              <div v-if="terminationInfo.lastNode !== 'Unknown'" class="status-detail">
                <span class="font-medium text-gray-700 dark:text-gray-300">Last Step:</span>
                <span class="text-sm text-gray-600 dark:text-gray-400 ml-2">
                  {{ terminationInfo.lastNode.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) }}
                </span>
              </div>
              
              <div class="status-detail">
                <span class="font-medium text-gray-700 dark:text-gray-300">Stream Complete:</span>
                <Check v-if="terminationInfo.complete" class="w-4 h-4 text-green-500 ml-2" />
                <X v-else class="w-4 h-4 text-red-500 ml-2" />
              </div>
            </div>
            
            <!-- Description -->
            <div class="description-section mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p class="text-sm text-gray-600 dark:text-gray-400">
                {{ getStatusInfo.description }}
              </p>
            </div>
            
            <!-- Circuit Breaker Specific Info -->
            <div v-if="terminationInfo.circuitBreaker" class="circuit-breaker-info mt-4">
              <div class="bg-orange-50 dark:bg-orange-900/20 p-3 rounded-lg border-l-4 border-orange-400">
                <h4 class="font-medium text-orange-800 dark:text-orange-200 mb-2 flex items-center">
                  <Shield class="w-4 h-4 mr-2" />
                  Protective Measures Activated
                </h4>
                <p class="text-sm text-orange-700 dark:text-orange-300">
                  The analysis was stopped to prevent system overload. This typically occurs when:
                </p>
                <ul class="text-sm text-orange-700 dark:text-orange-300 mt-2 ml-4 list-disc">
                  <li>Database queries encounter repeated syntax errors</li>
                  <li>Connection issues prevent successful execution</li>
                  <li>Complex queries require optimization</li>
                </ul>
                <p class="text-sm text-orange-700 dark:text-orange-300 mt-2">
                  Try rephrasing your question or checking your database connection.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Error State -->
    <div v-else class="error-state">
      <Alert variant="destructive">
        <AlertTriangle class="h-4 w-4" />
        <AlertDescription>
        Unable to parse stream termination data. Please check the system logs for more information.
        </AlertDescription>
      </Alert>
    </div>
  </div>
</template>

<style scoped>
.stream-termination-container {
  min-height: 120px;
  width: 100%;
}

.status-detail {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.description-section {
  border-left: 3px solid #e2e8f0;
}

.circuit-breaker-info {
  animation: pulse-orange 2s infinite;
}

@keyframes pulse-orange {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(251, 146, 60, 0.3);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(251, 146, 60, 0);
  }
}

.error-state {
  padding: 1rem;
}
</style> 