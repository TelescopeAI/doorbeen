<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import DataView from 'primevue/dataview';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import ProgressSpinner from 'primevue/progressspinner';
import Badge from 'primevue/badge';
import Chip from 'primevue/chip';
import Accordion from 'primevue/accordion';
import AccordionTab from 'primevue/accordiontab';

const props = defineProps({
  node: {
    type: [Object, String],
    required: true
  }
});

const nodeData = ref<any>(null);
const isComplete = ref(false);
const activeTab = ref(0);

const parseNodeData = () => {
  try {
    if (typeof props.node === 'string') {
      if (props.node.trim().startsWith('{')) {
        nodeData.value = JSON.parse(props.node);
      } else {
        nodeData.value = {
          exploration_complete: true,
          findings: props.node,
        };
      }
    } else {
      nodeData.value = props.node;
    }
    
    isComplete.value = nodeData.value?.exploration_complete || false;
  } catch (error) {
    console.error('Error parsing node data:', error);
    nodeData.value = null;
    isComplete.value = false;
  }
};

onMounted(parseNodeData);
watch(() => props.node, parseNodeData, { deep: true });

// Computed properties for better data organization
const explorationStats = computed(() => {
  if (!nodeData.value) return null;
  
  const stats = {
    tablesAnalyzed: nodeData.value.priority_tables?.length || 0,
    queriesExecuted: nodeData.value.exploration_queries?.length || 0,
    successfulQueries: nodeData.value.exploration_queries?.filter(q => q.status === 'success')?.length || 0,
    patternsFound: nodeData.value.patterns_found?.length || 0,
    totalRows: 0
  };
  
  // Calculate total rows from queries
  if (nodeData.value.exploration_queries) {
    stats.totalRows = nodeData.value.exploration_queries
      .filter(q => q.status === 'success')
      .reduce((sum, q) => sum + (q.rowCount || 0), 0);
  }
  
  return stats;
});

const queryGroups = computed(() => {
  if (!nodeData.value?.exploration_queries) return [];
  
  const groups = new Map();
  
  nodeData.value.exploration_queries.forEach((query, index) => {
    // Extract table name from query
    const tableMatch = query.query.match(/FROM\s+(\w+)/i);
    const tableName = tableMatch ? tableMatch[1] : 'Unknown';
    
    if (!groups.has(tableName)) {
      groups.set(tableName, []);
    }
    
    groups.get(tableName).push({ ...query, index });
  });
  
  return Array.from(groups.entries()).map(([table, queries]) => ({
    table,
    queries,
    successCount: queries.filter(q => q.status === 'success').length,
    totalRows: queries.reduce((sum, q) => sum + (q.rowCount || 0), 0)
  }));
});

const priorityTablesList = computed(() => {
  return nodeData.value?.priority_tables || [];
});

const hasData = computed(() => {
  return !!(nodeData.value && (
    nodeData.value.findings || 
    nodeData.value.domain_insights ||
    nodeData.value.priority_tables?.length ||
    nodeData.value.exploration_queries?.length
  ));
});

// Format cell values for display
const formatCellValue = (value: any) => {
  if (value === null || value === undefined) {
    return '—';
  }
  
  const stringValue = String(value);
  
  // Truncate long values
  if (stringValue.length > 50) {
    return stringValue.substring(0, 50) + '...';
  }
  
  return stringValue;
};
</script>

<template>
  <div class="exploration-dashboard">
    <!-- Loading State -->
    <div v-if="!isComplete && !hasData" class="loading-state">
      <Card class="text-center p-8">
        <template #content>
          <div class="flex flex-col items-center gap-4">
            <ProgressSpinner style="width: 48px; height: 48px" strokeWidth="3" />
            <div>
              <h3 class="text-xl font-semibold text-gray-700 dark:text-gray-300">Analyzing Database</h3>
              <p class="text-gray-500 dark:text-gray-400 mt-2">
                Discovering tables, relationships, and data patterns...
              </p>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Main Dashboard -->
    <div v-else class="conversation-dense prose-dense">
      
      <!-- Header with Status -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <i class="pi pi-database text-white text-xl"></i>
          </div>
          <div>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Database Exploration</h2>
            <p class="text-gray-600 dark:text-gray-300 flex items-center gap-2">
              <i :class="isComplete ? 'pi pi-check-circle text-green-500' : 'pi pi-clock text-blue-500'"></i>
              {{ isComplete ? 'Analysis Complete' : 'In Progress' }}
            </p>
          </div>
        </div>
        
        <Badge 
          v-if="isComplete" 
          value="Ready for Query Generation" 
          severity="success" 
          size="large"
        />
      </div>

      <!-- Overview Stats Cards -->
      <div v-if="explorationStats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card class="stat-card">
          <template #content>
            <div class="text-center p-4">
              <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
                {{ explorationStats.tablesAnalyzed }}
              </div>
              <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">Tables Analyzed</div>
            </div>
          </template>
        </Card>
        
        <Card class="stat-card">
          <template #content>
            <div class="text-center p-4">
              <div class="text-3xl font-bold text-green-600 dark:text-green-400">
                {{ explorationStats.successfulQueries }}/{{ explorationStats.queriesExecuted }}
              </div>
              <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">Queries Executed</div>
            </div>
          </template>
        </Card>
        
        <Card class="stat-card">
          <template #content>
            <div class="text-center p-4">
              <div class="text-3xl font-bold text-purple-600 dark:text-purple-400">
                {{ explorationStats.totalRows.toLocaleString() }}
              </div>
              <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">Records Sampled</div>
            </div>
          </template>
        </Card>
        
        <Card class="stat-card">
          <template #content>
            <div class="text-center p-4">
              <div class="text-3xl font-bold text-orange-600 dark:text-orange-400">
                {{ explorationStats.patternsFound }}
              </div>
              <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">Patterns Found</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Priority Tables Overview -->
      <Card v-if="priorityTablesList.length" class="priority-tables-card">
        <template #header>
          <div class="flex items-center gap-2 p-4 border-b">
            <i class="pi pi-star-fill text-yellow-500"></i>
            <h3 class="text-lg font-semibold">Priority Tables</h3>
          </div>
        </template>
        <template #content>
          <div class="flex flex-wrap gap-3 p-4">
            <Chip 
              v-for="(table, index) in priorityTablesList" 
              :key="table"
              :label="table"
              :class="[
                'text-sm font-medium',
                index === 0 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200' :
                index === 1 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
              ]"
              icon="pi pi-table"
            />
          </div>
        </template>
      </Card>

      <!-- Detailed Information Tabs -->
      <Card class="details-card">
        <template #content>
          <TabView v-model:activeIndex="activeTab" class="exploration-tabs">
            
            <!-- Domain Analysis Tab -->
            <TabPanel header="Domain Analysis">
              <div class="space-y-6 p-4">
                
                <!-- Domain Insights -->
                <div v-if="nodeData?.domain_insights">
                  <h4 class="text-lg font-semibold mb-3 flex items-center gap-2">
                    <i class="pi pi-lightbulb text-yellow-500"></i>
                    Domain Insights
                  </h4>
                  <div class="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 p-4 rounded-lg border border-yellow-200 dark:border-yellow-800">
                    <p class="text-gray-700 dark:text-gray-300 leading-relaxed">
                      {{ nodeData.domain_insights }}
                    </p>
                  </div>
                </div>

                <!-- Patterns Found -->
                <div v-if="nodeData?.patterns_found?.length">
                  <h4 class="text-lg font-semibold mb-3 flex items-center gap-2">
                    <i class="pi pi-chart-line text-orange-500"></i>
                    Data Patterns Identified
                  </h4>
                  <div class="grid gap-3">
                    <div 
                      v-for="(pattern, index) in nodeData.patterns_found" 
                      :key="index"
                      class="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm"
                    >
                      <div class="flex items-start gap-3">
                        <div class="w-8 h-8 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span class="text-orange-600 dark:text-orange-400 text-sm font-semibold">{{ index + 1 }}</span>
                        </div>
                        <p class="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{{ pattern }}</p>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </TabPanel>

            <!-- Query Analysis Tab -->
            <TabPanel header="Query Analysis">
              <div class="space-y-6 p-4">
                
                <!-- Query Groups by Table -->
                <div v-if="queryGroups.length">
                  <div class="space-y-4">
                    <div 
                      v-for="group in queryGroups" 
                      :key="group.table"
                      class="table-query-group"
                    >
                      <!-- Table Header -->
                      <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-t-lg border border-b-0 border-gray-200 dark:border-gray-700">
                        <div class="flex items-center gap-3">
                          <i class="pi pi-table text-blue-600"></i>
                          <h5 class="font-semibold text-gray-900 dark:text-white">{{ group.table }}</h5>
                        </div>
                        <div class="flex items-center gap-3">
                          <Tag :value="`${group.successCount}/${group.queries.length} successful`" 
                               :severity="group.successCount === group.queries.length ? 'success' : 'warning'" />
                          <Tag :value="`${group.totalRows} rows`" severity="info" />
                        </div>
                      </div>

                      <!-- Queries for this table -->
                      <div class="border border-t-0 border-gray-200 dark:border-gray-700 rounded-b-lg overflow-hidden">
                        <div 
                          v-for="query in group.queries" 
                          :key="query.index"
                          class="query-item  border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                        >
                          <div class="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                            <div class="flex items-start justify-between mb-2">
                              <div class="flex-1">
                                <h6 class="font-medium text-gray-800 dark:text-gray-200 text-sm">
                                  {{ query.objective || `Query ${query.index + 1}` }}
                                </h6>
                                <div class="flex items-center gap-2 mt-1">
                                  <Badge 
                                    :value="query.status === 'success' ? 'Success' : 'Failed'" 
                                    :severity="query.status === 'success' ? 'success' : 'danger'" 
                                  />
                                  <span v-if="query.rowCount !== undefined" class="text-xs text-gray-500">
                                    {{ query.rowCount }} rows returned
                                  </span>
                                </div>
                              </div>
                            </div>
                            
                            <!-- SQL Query -->
                            <div class="bg-gray-900 dark:bg-black p-3 rounded-md font-mono text-sm text-green-400 overflow-x-auto">
                              {{ query.query }}
                            </div>
                            
                            <!-- Results -->
                            <div v-if="query.results && query.results.length > 0" class="mt-3">
                              <h6 class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Results ({{ query.results.length }} {{ query.results.length === 1 ? 'row' : 'rows' }}):
                              </h6>
                              <div class="border border-gray-200 dark:border-gray-700 rounded-lg max-w-[60vw]">
                                <div class="results-table-container">
                                  <DataTable 
                                    :value="query.results" 
                                    size="small"
                                    :scrollable="true"
                                    scrollHeight="200px"
                                    tableStyle="max-width: 60vw; width: 40vw;"
                                    class="text-xs compact-table"
                                    columnResizeMode="fit"
                                    :paginator="query.results.length > 5"
                                    :rows="5"
                                    :showGridlines="true"
                                    responsiveLayout="scroll"
                                  >
                                    <Column 
                                      v-for="column in Object.keys(query.results[0] || {})" 
                                      :key="column"
                                      :field="column" 
                                      :header="column"
                                      :style="{ 
                                        minWidth: '120px', 
                                        maxWidth: '200px',
                                        width: 'auto'
                                      }"
                                    >
                                      <template #body="{ data }">
                                        <span 
                                          :title="String(data[column])"
                                          class="text-gray-700 dark:text-gray-300 truncate-cell"
                                        >
                                          {{ formatCellValue(data[column]) }}
                                        </span>
                                      </template>
                                    </Column>
                                  </DataTable>
                                </div>
                              </div>
                            </div>
                            
                            <!-- Fallback explanation if no results -->
                            <div v-else-if="query.explanation" class="mt-2 text-xs text-gray-600 dark:text-gray-400 italic">
                              {{ query.explanation }}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="text-center py-8">
                  <i class="pi pi-info-circle text-4xl text-gray-400 mb-4"></i>
                  <p class="text-gray-500">No exploration queries available</p>
                </div>

              </div>
            </TabPanel>

            <!-- Summary Report Tab -->
            <TabPanel header="Summary Report">
              <div class="p-4">
                
                <!-- Exploration Summary -->
                <div v-if="nodeData?.findings">
                  <div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-6 rounded-lg border border-blue-200 dark:border-blue-800">
                    <h4 class="text-lg font-semibold mb-4 flex items-center gap-2 text-blue-800 dark:text-blue-200">
                      <i class="pi pi-file-text"></i>
                      Exploration Summary
                    </h4>
                    <div class="prose prose-sm max-w-none text-gray-700 dark:text-gray-300">
                      <pre class="whitespace-pre-wrap font-sans leading-relaxed">{{ nodeData.findings }}</pre>
                    </div>
                  </div>
                </div>

                <div v-else class="text-center py-8">
                  <i class="pi pi-info-circle text-4xl text-gray-400 mb-4"></i>
                  <p class="text-gray-500">No detailed findings available</p>
                </div>

              </div>
            </TabPanel>

          </TabView>
        </template>
      </Card>

      <!-- Completion Status -->
      <div v-if="isComplete" class="completion-banner">
        <Card class="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800">
          <template #content>
            <div class="flex items-center gap-4 p-4">
              <div class="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center">
                <i class="pi pi-check text-white text-xl"></i>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-semibold text-green-800 dark:text-green-200">Exploration Complete</h4>
                <p class="text-green-700 dark:text-green-300 mt-1">
                  Database structure successfully analyzed. Ready to generate optimized queries based on discovered patterns and relationships.
                </p>
              </div>
              <Badge value="Ready" severity="success" size="large" />
            </div>
          </template>
        </Card>
      </div>

    </div>
  </div>
</template>

<style scoped>
.exploration-dashboard {
  max-width: 100%;
  margin: 0 auto;
}

.stat-card {
  transition: all 0.2s ease;
  border: 1px solid rgb(229 231 235);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.priority-tables-card .p-card-header {
  padding: 0;
}

.details-card .p-tabview .p-tabview-panels {
  padding: 0;
}

.table-query-group {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.query-item:hover {
  background: rgba(59, 130, 246, 0.02);
}

.completion-banner .p-card {
  border-width: 1px;
}

.dark .stat-card {
  border-color: rgb(55 65 81);
}

.dark .table-query-group {
  background: rgb(31 41 55);
}

/* Custom tab styling */
.exploration-tabs .p-tabview-nav li .p-tabview-nav-link {
  padding: 1rem 1.5rem;
  font-weight: 500;
}

.exploration-tabs .p-tabview-nav li.p-highlight .p-tabview-nav-link {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  border-radius: 6px 6px 0 0;
}

/* Loading animation */
.loading-state {
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* DataTable responsive container */
.results-table-container {
  max-width: 100%;
  overflow-x: auto;
}

.compact-table {
  font-size: 0.75rem;
}

.compact-table :deep(.p-datatable-table) {
  table-layout: fixed;
  width: 100%;
  max-width: 100%;
}

.compact-table :deep(.p-datatable-thead > tr > th) {
  padding: 0.5rem 0.75rem;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.compact-table :deep(.p-datatable-tbody > tr > td) {
  padding: 0.5rem 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.compact-table :deep(.p-datatable-scrollable-wrapper) {
  overflow-x: auto;
}

.truncate-cell {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .exploration-dashboard {
    padding: 1rem;
  }
  
  .grid.grid-cols-2.md\\:grid-cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .completion-banner .flex {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }
  
  .results-table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  
  .compact-table :deep(.p-datatable-thead > tr > th),
  .compact-table :deep(.p-datatable-tbody > tr > td) {
    min-width: 100px;
    max-width: 150px;
  }
}
</style> 