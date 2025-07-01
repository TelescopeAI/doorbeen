<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '~/components/ui/button';
import { List, ChevronUp, ChevronDown, CheckCircle } from 'lucide-vue-next';
import { StreamResponse } from "~/types/streaming";
import NodeOutputDisplay from '~/components/Reasoning/NodeOutputDisplay.vue';

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['start-new-question']);

const stream = computed(() => props.message?.stream || new StreamResponse(null))

// Accordion control context - use array for multiple panels
const allExpanded = ref(false);
const openPanels = ref<string[]>([]); // Array of open panel values

// Initialize accordion states when stream changes
watchEffect(() => {
  if (stream.value?.nodeOutputs) {
    // Initialize with all panels open by default
    if (allExpanded.value) {
      openPanels.value = stream.value.nodeOutputs.map((_: any, index: number) => index.toString());
    } else {
      openPanels.value = [];
    }
  }
});

// Toggle all accordions
const toggleAllAccordions = () => {
  allExpanded.value = !allExpanded.value;
  
  // Update all accordion states
  if (stream.value?.nodeOutputs) {
    if (allExpanded.value) {
      // Open all panels
      openPanels.value = stream.value.nodeOutputs.map((_: any, index: number) => index.toString());
    } else {
      // Close all panels
      openPanels.value = [];
    }
  }
};

// Helper function to get step title from node name
const getStepTitle = (nodeName: string) => {
  if(nodeName === 'init_assistant'){
    return 'Determining if this is a new question or a followup'
  }
  else if(nodeName === 'qa_grade_node'){
    return 'Grading the quality of the question'
  }
  // NEW: Supervisor-specific event titles
  else if(nodeName === 'supervisor_node'){
    return 'Multi-agent supervisor coordinating analysis'
  }
  else if(nodeName === 'supervisor_initialized'){
    return 'Supervisor initialized - Multi-agent coordination starting'
  }
  else if(nodeName === 'agent_handoff'){
    return 'Supervisor delegating task to specialized agent'
  }
  else if(nodeName === 'agent_completed'){
    return 'Agent completed task - returning to supervisor'
  }
  else if(nodeName === 'agent_failed'){
    return 'Agent encountered error - supervisor handling retry'
  }
  else if(nodeName === 'agent_retry'){
    return 'Supervisor retrying failed agent with different strategy'
  }
  else if(nodeName === 'supervisor_completed'){
    return 'Multi-agent coordination completed successfully'
  }
  // Agent-specific titles
  else if(nodeName === 'data_analysis'){
    return 'Data Analysis Agent exploring database structure'
  }
  else if(nodeName === 'query_generation'){
    return 'Query Generation Agent creating SQL queries'
  }
  else if(nodeName === 'result_processing'){
    return 'Result Processing Agent analyzing query results'
  }
  else if(nodeName === 'objective_evaluation'){
    return 'Objective Evaluation Agent checking if goals are met'
  }
  else if(nodeName === 'finalization'){
    return 'Finalization Agent preparing final response'
  }
  // Linear node titles
  else if(nodeName === 'enrich_input_node'){
    return 'Enriching the question with more context'
  }
  else if(nodeName === 'input_followup_node'){
    return 'Processing followup question based on the previous conversation'
  }
  else if(nodeName === 'interpret_input_node'){
    return 'Understanding the question and forming the objective'
  }
  else if(nodeName === 'data_exploration_node'){
    return 'Exploring the database to understand the available data'
  }
  else if(nodeName === 'determine_input_objectives'){
    return 'Clarifying the input objectives and determining what data to gather'
  }
  else if(nodeName === 'generate_sql_query_node'){
    return 'Generating the SQL Query to fetch the data'
  }
  else if(nodeName === 'execute_sql_query_node'){
    return 'Executing the SQL Query'
  }
  else if(nodeName === 'handle_execution_failure_node'){
    return 'Trying to fix the generated query'
  }
  else if(nodeName === 'process_results_node'){
    return 'Analysing the data to find insights'
  }
  else if(nodeName === 'query_visualization_node'){
    return 'Planning data visualization and charts'
  }
  else if(nodeName === 'final_answer_node'){
    return 'Generating Final Answer'
  }
  else if(nodeName === 'stream_termination'){
    return 'Analysis Stream Status'
  }
  else {
    return 'Unknown tool'
  }
};

const handleStartNewQuestion = (question: string) => {
  console.log('Reasoning Container received start-new-question:', question);
  emit('start-new-question', question);
};

// Helper functions for formatting
const formatNodeData = (data: any) => {
  if (typeof data === 'string') {
    return data;
  }
  return JSON.stringify(data, null, 2);
};

const formatTimestamp = (timestamp: string) => {
  return new Date(timestamp).toLocaleString();
};
</script>

<template>
  <div class="flex flex-col gap-y-1 pb-8" v-if="stream && stream.nodeOutputs?.length > 0">
    <!-- Collapse/Expand All Control -->
    <div class="flex justify-between items-center mb-3 px-2">
      <div class="flex items-center gap-2">
        <List class="w-4 h-4 text-gray-600 dark:text-gray-400" />
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
          Analysis Steps ({{ stream.nodeOutputs.length }})
        </span>
      </div>
      
      <Button
        variant="outline"
        size="sm"
        @click="toggleAllAccordions"
        class="text-xs"
      >
        <ChevronUp v-if="allExpanded" class="w-4 h-4 mr-2" />
        <ChevronDown v-else class="w-4 h-4 mr-2" />
        {{ allExpanded ? 'Collapse All' : 'Expand All' }}
      </Button>
    </div>

    <!-- Master Accordion Container -->
    <Accordion type="multiple" v-model="openPanels" class="analysis-steps-accordion">
      <AccordionItem 
        v-for="(item, index) in stream.nodeOutputs" 
        :key="item.id || item.name + '-' + index" 
        :value="index.toString()"
      >
        <AccordionTrigger class="step-header">
          <div class="flex items-center justify-between w-full pr-3">
            <div class="flex items-center gap-3">
              <span class="font-medium text-sm underline-none">{{ getStepTitle(item.name) }}</span>
            </div>
            <CheckCircle class="w-4 h-4 text-green-500" />
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <Card class="step-content-card">
            <CardContent class="p-4">
              <div class="space-y-3">
                <!-- Node Output Display -->
                <NodeOutputDisplay 
                  :node="item" 
                  :hide-accordion="true"
                  @start-new-question="handleStartNewQuestion"
                />
                
                <!-- Timestamp -->
                <div class="timestamp text-xs text-gray-400">
                  {{ new Date(item.occurred_at).toLocaleString() }}
                </div>
              </div>
            </CardContent>
          </Card>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  </div>
</template>

<style scoped>
/* Master Accordion Styles */
.analysis-steps-accordion {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.analysis-steps-accordion :deep(.p-accordion-panel) {
  border: none;
  margin-bottom: 1px;
}

.step-header {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid #e2e8f0;
  padding: 0.75rem 1rem;
}

.dark .step-header {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-bottom: 1px solid #475569;
}

.dark .step-header span {
  color: #e2e8f0;
}

.step-header :deep(.p-accordion-header-link) {
  padding: 0;
  width: 100%;
}

.step-header :deep(.p-accordion-toggle-icon) {
  margin-left: 0.5rem;
}

.step-content-card {
  margin: 0;
  border: none;
  box-shadow: none;
  background: transparent;
}

.step-content-card :deep(.p-card-content) {
  padding: 1rem;
}

/* Styling for the control header */
.expand-collapse-control {
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.dark .expand-collapse-control {
  border-bottom: 1px solid #4b5563;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
}

/* Fix any potential overflow issues */
.analysis-steps-accordion :deep(.p-accordion-header) {
  border: none;
  border-radius: 8px 8px 0 0;
}

.analysis-steps-accordion :deep(.p-accordion-content) {
  border: none;
  padding: 0;
}
</style>