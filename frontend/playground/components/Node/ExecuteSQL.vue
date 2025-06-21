<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import { Card, CardContent, CardTitle } from '~/components/ui/card';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { toast } from 'vue-sonner';
import { Copy, CheckCircle, XCircle, Info } from 'lucide-vue-next';

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const nodeData = ref<any>(null);

onMounted(() => {
  try {
    nodeData.value = typeof props.node === 'string' ? JSON.parse(props.node) : props.node;
  } catch (error) {
    console.error('Error parsing node data:', error);
  }
});

const formatSQL = (sql: string) => {
  if (!sql) return '';
  
  // Basic SQL formatting - add line breaks after common keywords
  return sql
    .replace(/\s+/g, ' ')
    .replace(/\b(SELECT|FROM|WHERE|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|GROUP BY|ORDER BY|HAVING|UNION|INSERT|UPDATE|DELETE|WITH)\b/gi, '\n$1')
    .replace(/,\s*(?=[A-Za-z])/g, ',\n    ')
    .replace(/\n\s*/g, '\n')
    .trim();
};

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(nodeData.value?.query || '');
    toast.success('SQL Query Copied!', {
      description: 'The SQL query has been copied to your clipboard.',
    });
  } catch (err) {
    toast.error('Copy Failed', {
      description: 'Failed to copy SQL query to clipboard. Please try again.',
    });
  }
};

const executionStatus = computed(() => {
  if (!nodeData.value) return null;
  
  if (nodeData.value.error) {
    return {
      type: 'error',
      message: 'Query execution failed',
      details: nodeData.value.error
    };
  }
  
  if (nodeData.value.result !== undefined && nodeData.value.result !== null) {
    const resultCount = Array.isArray(nodeData.value.result) ? nodeData.value.result.length : 0;
    return {
      type: 'success',
      message: 'Query executed successfully',
      count: resultCount
    };
  }
  
  return {
    type: 'info',
    message: 'Query Execution',
    details: 'No specific result information available'
  };
});

const sampleResults = computed(() => {
  if (!nodeData.value?.result || !Array.isArray(nodeData.value.result)) {
    return [];
  }
  
  // Return first 10 rows
  return nodeData.value.result.slice(0, 10);
});

const resultColumns = computed(() => {
  if (sampleResults.value.length === 0) return [];
  
  return Object.keys(sampleResults.value[0]).map(key => ({
    field: key,
    header: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }));
});

const executionTime = computed(() => {
  return nodeData.value?.execution_time || 'N/A';
});
</script>

<template>
  <div class="sql-execution-container space-y-4">
    
    <!-- Execution Status -->
    <Card v-if="executionStatus" class="execution-status">
      <CardContent>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <CheckCircle v-if="executionStatus.type === 'success'" class="w-5 h-5 text-green-500" />
            <XCircle v-else-if="executionStatus.type === 'error'" class="w-5 h-5 text-red-500" />
            <Info v-else class="w-5 h-5 text-blue-500" />
            
            <div class="flex flex-col">
              <h4 class="font-semibold text-gray-800 dark:text-gray-200 text-left">{{ executionStatus.message }}</h4>
              <div class="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400 mt-1">
                <span v-if="executionStatus.count !== undefined">{{ executionStatus.count }} records returned</span>
                <span v-if="executionTime !== 'N/A'">Execution time: {{ executionTime }}</span>
              </div>
            </div>
          </div>
          
          <Badge 
            :variant="executionStatus.type === 'success' ? 'default' : executionStatus.type === 'error' ? 'destructive' : 'secondary'"
            class="text-center"
          >
            {{ executionStatus.type === 'success' ? 'Success' : executionStatus.type === 'error' ? 'Failed' : 'Completed' }}
          </Badge>
        </div>
        
        <!-- Error Details -->
        <div v-if="executionStatus.type === 'error' && executionStatus.details" class="mt-3">
          <Alert variant="destructive">
            <XCircle class="h-4 w-4" />
            <AlertDescription>{{ executionStatus.details }}</AlertDescription>
          </Alert>
        </div>
      </CardContent>
    </Card>

    <!-- SQL Query Display -->
    <div class="sql-query-section">
      <div class="flex justify-between items-center mb-3">
        <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200">Executed SQL Query</h3>
        <Button 
          variant="outline"
          size="sm"
          @click="copyToClipboard"
          :disabled="!nodeData?.query"
        >
          <Copy class="w-4 h-4 mr-2" />
          Copy
        </Button>
      </div>
      
      <div class="sql-display bg-gray-900 rounded-lg overflow-hidden shadow-lg">
        <div class="bg-gray-800 px-4 py-2 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-red-500 rounded-full"></div>
            <div class="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <div class="w-3 h-3 bg-green-500 rounded-full"></div>
          </div>
          <Badge variant="secondary" class="text-gray-400 text-sm font-mono">SQL</Badge>
        </div>
        
        <div class="p-4 overflow-x-auto">
          <pre class="text-sm font-mono leading-relaxed"><code class="sql-syntax">{{ formatSQL(nodeData?.query || 'Loading...') }}</code></pre>
        </div>
      </div>
    </div>

    <!-- Results Preview -->
    <div v-if="sampleResults.length > 0" class="results-preview">
      <Card>
        <CardTitle>
          <div class="flex items-center justify-between">
            <span>Results Preview</span>
            <Badge variant="secondary">
              {{ sampleResults.length }} of {{ nodeData?.result?.length || 0 }} rows
            </Badge>
          </div>
        </CardTitle>
        
        <CardContent>
          <DataTable 
            :value="sampleResults" 
            :scrollable="true" 
            scrollHeight="300px"
            class="mt-2"
            :paginator="false"
            responsiveLayout="scroll"
          >
            <Column 
              v-for="col in resultColumns" 
              :key="col.field" 
              :field="col.field" 
              :header="col.header"
              style="min-width: 120px"
            >
              <template #body="{ data }">
                <span class="text-sm">{{ data[col.field] }}</span>
              </template>
            </Column>
          </DataTable>
          
          <div v-if="nodeData?.result?.length > 10" class="mt-3 text-center">
            <Alert>
              <Info class="h-4 w-4" />
              <AlertDescription>
              Showing first 10 of {{ nodeData.result.length }} total records
              </AlertDescription>
            </Alert>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- No Results Message -->
    <div v-else-if="executionStatus?.type === 'success'" class="no-results">
      <Alert>
        <Info class="h-4 w-4" />
        <AlertDescription>
        Query executed successfully but returned no results
        </AlertDescription>
      </Alert>
    </div>
    
  </div>
</template>

<style scoped>
.sql-execution-container {
  width: 100%;
  max-width: 100%;
}

.sql-display {
  max-width: 100%;
  border: 1px solid #374151;
  background: #111827;
}

.sql-syntax {
  color: #e5e7eb;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  background: transparent;
}

pre {
  margin: 0;
  padding: 0;
  background: transparent;
}

code {
  background: transparent;
  font-family: 'JetBrains Mono', 'Fira Code', 'Monaco', 'Cascadia Code', 'Roboto Mono', monospace;
}

.sql-display .bg-gray-800 {
  background: #1f2937;
}

.sql-display .bg-gray-900 {
  background: #111827;
}

.execution-status {
  border-left: 4px solid #10b981;
}

.results-preview .p-datatable {
  font-size: 0.875rem;
}

.results-preview .p-datatable .p-datatable-thead > tr > th {
  background: #f8fafc;
  border-bottom: 2px solid #e2e8f0;
  font-weight: 600;
  color: #374151;
}

.results-preview .p-datatable .p-datatable-tbody > tr > td {
  border-bottom: 1px solid #e2e8f0;
  padding: 0.5rem;
}
</style>