<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Panel from 'primevue/panel';
import { Alert, AlertDescription } from '~/components/ui/alert';
import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Separator } from '~/components/ui/separator';
import { 
  Hash, 
  User, 
  Calendar, 
  Mail, 
  Phone, 
  MapPin, 
  Info, 
  DollarSign, 
  BarChart3, 
  Star, 
  Calculator, 
  Tag,
  TrendingUp,
  Table,
  ExternalLink,
  CheckCircle,
  Lightbulb,
  ArrowRight
} from 'lucide-vue-next';
import MDRenderer from '../MDRenderer.vue';

const props = defineProps({
  node: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['start-new-question']);

const nodeData = ref<any>(null);
const results = ref<any[]>([]);
const columns = ref<{ field: string; header: string }[]>([]);

const dataTable = ref<any>(null);

const isSingleResult = computed(() => results.value.length === 1);

// Helper function to format field names for better display
const formatFieldName = (fieldName: string) => {
  return fieldName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l: string) => l.toUpperCase());
};

// Helper function to determine badge variant based on field type
const getBadgeVariant = (key: string, value: any) => {
  if (typeof value === 'number') {
    if (key.toLowerCase().includes('id') || key.toLowerCase().includes('count')) {
      return 'secondary';
    }
    if (key.toLowerCase().includes('rate') || key.toLowerCase().includes('score')) {
      return 'outline';
    }
    if (key.toLowerCase().includes('total') || key.toLowerCase().includes('sum')) {
      return 'default';
    }
    return 'secondary';
  }
  if (typeof value === 'string') {
    if (key.toLowerCase().includes('status') || key.toLowerCase().includes('state')) {
      return 'outline';
    }
    if (key.toLowerCase().includes('type') || key.toLowerCase().includes('category')) {
      return 'secondary';
    }
    return 'default';
  }
  return 'secondary';
};

// Helper function to get appropriate icon for field
const getFieldIcon = (key: string, value: any) => {
  if (key.toLowerCase().includes('id')) return Hash;
  if (key.toLowerCase().includes('name') || key.toLowerCase().includes('title')) return User;
  if (key.toLowerCase().includes('date') || key.toLowerCase().includes('time')) return Calendar;
  if (key.toLowerCase().includes('email')) return Mail;
  if (key.toLowerCase().includes('phone')) return Phone;
  if (key.toLowerCase().includes('address')) return MapPin;
  if (key.toLowerCase().includes('status') || key.toLowerCase().includes('state')) return Info;
  if (key.toLowerCase().includes('price') || key.toLowerCase().includes('cost') || key.toLowerCase().includes('amount')) return DollarSign;
  if (key.toLowerCase().includes('count') || key.toLowerCase().includes('total') || key.toLowerCase().includes('sum')) return BarChart3;
  if (key.toLowerCase().includes('rate') || key.toLowerCase().includes('score')) return Star;
  if (typeof value === 'number') return Calculator;
  return Tag;
};

const processResults = () => {
  try {
    const parsedNode = JSON.parse(props.node);
    nodeData.value = parsedNode;
    
    console.log('Processing node data:', parsedNode);

    if (parsedNode && parsedNode.results) {
      results.value = [...parsedNode.results];
      console.log('Found results:', results.value);
      
      if (results.value.length > 0) {
        columns.value = Object.keys(results.value[0]).map(key => ({
          field: key,
          header: formatFieldName(key)
        }));
        console.log('Generated columns:', columns.value);
      }
    } else {
      console.log('No results found in parsed node');
      results.value = [];
      columns.value = [];
    }
  } catch (error) {
    console.error('Error parsing node data:', error);
    console.log('Raw node prop:', props.node);
    nodeData.value = null;
    results.value = [];
    columns.value = [];
  }
};

onMounted(processResults);

// Watch for changes in the node prop
watch(() => props.node, processResults);

// Helper function to determine column minimum width based on content type
const getColumnMinWidth = (fieldName: string) => {
  // ID columns can be narrower
  if (fieldName.toLowerCase().includes('id')) {
    return '80px';
  }
  // Date/time columns need more space
  if (fieldName.toLowerCase().includes('date') || fieldName.toLowerCase().includes('time')) {
    return '140px';
  }
  // Numeric columns can be medium width
  if (fieldName.toLowerCase().includes('count') || 
      fieldName.toLowerCase().includes('duration') || 
      fieldName.toLowerCase().includes('avg') ||
      fieldName.toLowerCase().includes('amount') ||
      fieldName.toLowerCase().includes('score')) {
    return '120px';
  }
  // Text columns need more space
  return '150px';
};

// Helper function to format cell values for better display
const formatCellValue = (value: any) => {
  if (value === null || value === undefined) {
    return '—';
  }
  
  // Handle numbers - add proper formatting
  if (typeof value === 'number') {
    // If it's a decimal with many places, round to 2 decimal places
    if (value % 1 !== 0) {
      return Number(value.toFixed(2)).toString();
    }
    return value.toString();
  }
  
  // Handle very long strings - truncate if necessary
  if (typeof value === 'string' && value.length > 50) {
    return value.substring(0, 47) + '...';
  }
  
  return String(value);
};

const exportCSV = () => {
  if (dataTable.value) {
    dataTable.value.exportCSV();
  }
};

const handleFollowUpQuestion = (question: string) => {
  console.log('Starting new conversation with question:', question);
  emit('start-new-question', question);
};
</script>

<template>
  <div class="w-full max-w-full overflow-hidden p-4 flex flex-col gap-y-12">
    <div class="w-full max-w-full">
      <!-- Debug Information (remove in production) -->
      <div class="debug-info mb-4 p-4 bg-gray-100 rounded text-xs">
        <strong>Debug Info:</strong><br>
        Node Data: {{ nodeData ? 'Found' : 'Not found' }}<br>
        Results Length: {{ results.length }}<br>
        Columns Length: {{ columns.length }}<br>
        Is Single Result: {{ isSingleResult }}<br>
        Results Preview: {{ results.slice(0, 1) }}
      </div>

      <MDRenderer v-if="nodeData && nodeData.message" :md="nodeData.message" cid="final_message" severity="info" :closable="false" class="mb-10">
      </MDRenderer>
    </div>

    <div class="w-full max-w-full overflow-hidden">
      <!-- Enhanced Single Result Display -->
      <div v-if="isSingleResult && results[0]" class="single-result-container">
        <Panel header="Analysis Result" :toggleable="false" class="result-panel">
          <template #header>
            <div class="flex items-center gap-2">
              <TrendingUp class="w-5 h-5 text-blue-600" />
              <span class="font-semibold text-lg">Analysis Result</span>
              <Badge variant="secondary" class="ml-auto">
                {{ Object.keys(results[0]).length }} fields
              </Badge>
            </div>
          </template>
          
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card 
              v-for="(value, key) in results[0]" 
              :key="String(key)" 
              class="field-card hover:shadow-lg transition-all duration-200"
            >
              <CardContent>
                <div class="flex flex-col gap-3">
                  <div class="flex items-center gap-2">
                    <component :is="getFieldIcon(String(key), value)" class="w-4 h-4 text-gray-600 dark:text-gray-400" />
                    <span class="font-medium text-sm text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                      {{ formatFieldName(String(key)) }}
                    </span>
                  </div>
                  
                  <div class="flex items-center justify-center min-h-12">
                    <Badge 
                      :variant="getBadgeVariant(String(key), value)"
                      class="text-base font-semibold px-4 py-2"
                    >
                      {{ String(value) }}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          
          <!-- Summary section for single results -->
          <Separator class="my-4" />
          <div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>{{ Object.keys(results[0]).length }} data points analyzed</span>
            <span class="flex items-center gap-1">
              <CheckCircle class="w-4 h-4 text-green-500" />
              Complete
            </span>
          </div>
        </Panel>
      </div>

      <!-- Multiple Results Display -->
      <div v-else-if="results.length > 1" class="w-full max-w-full">
        <!-- Table Header -->
        <div class="flex justify-between items-center mb-4 w-full">
          <div class="flex items-center gap-2 min-w-0 flex-1">
            <Table class="w-5 h-5 text-blue-600 flex-shrink-0" />
            <span class="font-semibold text-gray-900 dark:text-gray-100 truncate">Analysis Results</span>
            <Badge variant="secondary" class="flex-shrink-0">
              {{ results.length }} rows
            </Badge>
          </div>
          <Button
            variant="outline"
            @click="exportCSV"
            class="flex-shrink-0"
          >
            <ExternalLink class="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>

        <!-- DataTable with proper width constraints -->
        <div class="w-full max-w-full overflow-hidden rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-sm">
          <div class="w-full max-w-full overflow-x-auto">
            <DataTable
              ref="dataTable"
              :value="results"
              :paginator="true"
              :rows="10"
              :rowsPerPageOptions="[10, 20, 50]"
              :scrollable="true"
              scrollHeight="400px"
              class="w-full min-w-full"
              tableStyle="width: 100%"
              paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
              currentPageReportTemplate="Showing {first} to {last} of {totalRecords} entries"
              showGridlines
            >
              <Column
                v-for="col in columns"
                :key="col.field"
                :field="col.field"
                :header="col.header"
                :sortable="true"
                :style="{ minWidth: getColumnMinWidth(col.field), maxWidth: '200px' }"
                headerClass="bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-semibold py-3 px-4 text-left text-sm"
                bodyClass="py-3 px-4 text-sm text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-600"
              >
                <template #body="{ data }">
                  <div class="max-w-[180px] overflow-hidden text-ellipsis whitespace-nowrap" :title="String(data[col.field])">
                    {{ formatCellValue(data[col.field]) }}
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </div>
        
        <!-- Table Info -->
        <Alert class="mt-4">
          <Info class="h-4 w-4" />
          <AlertDescription>
            Scroll horizontally to view all columns • Use pagination to navigate through rows
          </AlertDescription>
        </Alert>
      </div>
    </div>

    <!-- Follow-up Questions Section -->
    <div v-if="nodeData && nodeData.next_questions && nodeData.next_questions.length > 0" class="follow-up-questions">
      <div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <div class="flex items-center mb-4">
          <Lightbulb class="w-6 h-6 text-blue-600 dark:text-blue-400 mr-3" />
          <h3 class="text-lg font-semibold text-blue-800 dark:text-blue-200">Continue Your Analysis</h3>
        </div>
        
        <p class="text-sm text-blue-700 dark:text-blue-300 mb-4">
          Explore these related questions to dive deeper into your data:
        </p>
        
        <div class="grid gap-3">
          <Button
            v-for="(question, index) in nodeData.next_questions"
            :key="index"
            variant="outline"
            class="justify-start text-left p-3 h-auto whitespace-normal"
            @click="handleFollowUpQuestion(question)"
          >
              <div class="flex items-start gap-3 w-full">
              <ArrowRight class="w-4 h-4 text-blue-600 dark:text-blue-400 mt-1 flex-shrink-0" />
                <span class="text-sm leading-relaxed text-gray-800 dark:text-gray-200">{{ question }}</span>
              </div>
          </Button>
        </div>
        
        <div class="mt-4 text-xs text-blue-600 dark:text-blue-400 flex items-center">
          <Info class="w-4 h-4 mr-2" />
          <span>Click any question to start a new analysis conversation</span>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Clean Tailwind-based styles - remove problematic CSS overrides */

/* Follow-up Questions */
.follow-up-questions .p-button {
  @apply rounded-lg transition-all duration-200;
}

.follow-up-questions .p-button:hover {
  @apply -translate-y-0.5 shadow-lg;
}

.follow-up-questions .p-button:active {
  @apply translate-y-0;
}

/* Single Result Cards */
.single-result-container {
  @apply w-full;
}

.result-panel {
  @apply bg-gradient-to-br from-white to-gray-50 border border-gray-200;
}

.dark .result-panel {
  @apply from-gray-800 to-gray-900 border-gray-700;
}

.field-card {
  @apply border border-gray-200 rounded-xl bg-white min-h-[120px] transition-all duration-200;
}

.dark .field-card {
  @apply border-gray-700 bg-gray-800;
}

.field-card:hover {
  @apply border-blue-400 -translate-y-1 shadow-lg;
}

/* Panel overrides */
:deep(.p-panel-header) {
  @apply bg-transparent border-none p-6;
}

:deep(.p-panel-content) {
  @apply px-6 pb-6;
}

/* DataTable clean overrides - minimal and non-intrusive */
:deep(.p-datatable .p-datatable-thead > tr > th) {
  @apply border-b-2 border-gray-300 dark:border-gray-600;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  @apply border-b border-gray-200 dark:border-gray-700;
}

:deep(.p-datatable .p-datatable-tbody > tr:hover) {
  @apply bg-gray-50 dark:bg-gray-700/50;
}

/* Ensure proper width constraints */
:deep(.p-datatable) {
  @apply w-full max-w-full;
  table-layout: fixed;
}

:deep(.p-datatable .p-datatable-wrapper) {
  @apply w-full max-w-full overflow-x-auto;
}

:deep(.p-datatable .p-datatable-table) {
  @apply w-full;
  table-layout: fixed;
  width: 100% !important;
}

:deep(.p-datatable .p-datatable-scrollable-wrapper) {
  @apply w-full max-w-full;
}

:deep(.p-datatable .p-datatable-scrollable-view) {
  @apply w-full max-w-full;
}

:deep(.p-datatable .p-datatable-scrollable-body) {
  @apply overflow-x-auto;
}

/* Ensure column cells don't overflow */
:deep(.p-datatable .p-datatable-thead > tr > th),
:deep(.p-datatable .p-datatable-tbody > tr > td) {
  @apply overflow-hidden;
  word-wrap: break-word;
  text-overflow: ellipsis;
}

/* Remove debug info in production */
.debug-info {
  @apply block bg-gray-100 dark:bg-gray-800 p-4 rounded text-xs mb-4;
}
</style>