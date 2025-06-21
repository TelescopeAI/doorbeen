<script setup lang="ts">
import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Copy } from 'lucide-vue-next';
import { ref, onMounted } from 'vue';
import { useToast } from '~/components/ui/toast/use-toast';

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const nodeData = ref<any>(null);
const { toast } = useToast();

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
    toast({
      title: 'Copied!',
      description: 'SQL query copied to clipboard',
    });
  } catch (err) {
    toast({
      title: 'Error',
      description: 'Failed to copy to clipboard',
      variant: 'destructive',
    });
  }
};
</script>

<template>
  <div class="sql-query-container">
    <div class="flex justify-between items-center mb-3">
      <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200">Generated SQL Query</h3>
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
</template>

<style scoped>
.sql-query-container {
  width: 100%;
  max-width: 100%;
}

.sql-display {
  max-width: 100%;
  border: 1px solid #374151;
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

/* Dark theme for SQL display */
.sql-display {
  background: #111827;
}

.sql-display .bg-gray-800 {
  background: #1f2937;
}

.sql-display .bg-gray-900 {
  background: #111827;
}
</style>