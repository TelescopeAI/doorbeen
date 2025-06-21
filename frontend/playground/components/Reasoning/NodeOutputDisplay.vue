<script setup lang="ts">
import { watch } from 'vue';
import { 
  Accordion, 
  AccordionContent, 
  AccordionItem, 
  AccordionTrigger 
} from '~/components/ui/accordion';
import { Card, CardContent } from '~/components/ui/card';
import { Settings, CheckCircle, Clock, Loader2 } from 'lucide-vue-next';
import InterpretInput from "~/components/Node/InterpretInput.vue";
import QAGrading from "~/components/Node/QAGrading.vue";
import EnrichInput from "~/components/Node/EnrichInput.vue";
import GenerateQuery from "~/components/Node/GenerateQuery.vue";
import ExecuteSQL from "~/components/Node/ExecuteSQL.vue";
import SQLExecutionFailure from "~/components/Node/SQLExecutionFailure.vue";
import AnalyseExecutionResults from "~/components/Node/AnalyseExecutionResults.vue";
import GenerateFinalAnswer from "~/components/Node/GenerateFinalAnswer.vue";
import Fallback from "~/components/Node/Fallback.vue";
import NewOrFollowup from "~/components/Node/NewOrFollowup.vue";
import DataExploration from "~/components/Node/DataExploration.vue";
import InputFollowup from "~/components/Node/InputFollowup.vue";
import QueryVisualization from "~/components/Node/QueryVisualization.vue";
import DetermineInputObjectives from "~/components/Node/DetermineInputObjectives.vue";
import StreamTermination from "~/components/Node/StreamTermination.vue";

const props = defineProps({
  node: {
    type: Object,
    default: () => ({})
  },
  forceExpanded: {
    type: Boolean,
    default: undefined
  },
  hideAccordion: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['start-new-question']);

const node_obj = ref(props.node)
const tool_name = ref(props.node.name)
const tool_input = ref('')
const tool_output = ref(null)

// Accordion state management
const localExpandedState = ref(true); // Default to expanded
const accordionValue = computed(() => {
  // If forceExpanded is explicitly set, use it; otherwise use local state
  if (props.forceExpanded !== undefined) {
    return props.forceExpanded ? "item-1" : "";
  }
  return localExpandedState.value ? "item-1" : "";
});

// Watch for forceExpanded changes to update local state
watch(() => props.forceExpanded, (newValue) => {
  if (newValue !== undefined) {
    localExpandedState.value = newValue;
  }
});

watchEffect(() => {
  const node_obj = props.node
  tool_name.value = node_obj.name
  tool_output.value = node_obj.data
  console.log("ToolDisplay Debug - Full node:", node_obj)
  console.log("ToolDisplay Debug - node.data:", node_obj.data)
  console.log("ToolDisplay Debug - node.value:", node_obj.value)
  console.log("ToolDisplay Debug - tool_name:", tool_name.value)
})

const isResultNull = computed(() => {
  return tool_output.value === null || tool_output.value === undefined
})

const toolInputString = computed(() => {
  return JSON.stringify(tool_input.value)
})

const handleStartNewQuestion = (question: string) => {
  console.log('NodeOutputDisplay received start-new-question:', question);
  emit('start-new-question', question);
};

function getTitle() {
  const tool_name = props.node.name
  // console.log(tool_name)
  if(tool_name === 'init_assistant'){
    return 'Determining if this is a new question or a followup'
  }
  else if(tool_name === 'qa_grade_node'){
    return 'Grading the quality of the question'
  }
  else if(tool_name === 'enrich_input_node'){
    return 'Enriching the question with more context'
  }
  else if(tool_name === 'input_followup_node'){
    return 'Processing followup question based on the previous conversation'
  }
  else if(tool_name === 'interpret_input_node'){
    return 'Understanding the question and forming the objective'
  }
  else if(tool_name === 'data_exploration_node'){
    return 'Exploring the database to understand the available data'
  }
  else if(tool_name === 'determine_input_objectives'){
    return 'Clarifying the input objectives and determining what data to gather'
  }
  else if(tool_name === 'generate_sql_query_node'){
    return 'Generating the SQL Query to fetch the data'
  }
  else if(tool_name === 'execute_sql_query_node'){
    return 'Executing the SQL Query'
  }
  else if(tool_name === 'handle_execution_failure_node'){
    return 'Trying to fix the generated query'
  }
  else if(tool_name === 'process_results_node'){
    return 'Analysing the data to find insights'
  }
  else if(tool_name === 'query_visualization_node'){
    return 'Planning data visualization and charts'
  }
  else if(tool_name === 'final_answer_node'){
    return 'Generating Final Answer'
  }
  else if(tool_name === 'stream_termination'){
    return 'Analysis Stream Status'
  }
  else {
    return 'Unknown tool'
  }
}
</script>

<template>
  <div class="w-full">
    <!-- Direct content rendering when used inside master accordion -->
    <div v-if="hideAccordion && tool_output && !isResultNull">
      <!-- Explicit component rendering based on tool name -->
      <NewOrFollowup 
        v-if="tool_name === 'init_assistant'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <QAGrading 
        v-else-if="tool_name === 'qa_grade_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <EnrichInput 
        v-else-if="tool_name === 'enrich_input_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <InterpretInput 
        v-else-if="tool_name === 'interpret_input_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <DataExploration 
        v-else-if="tool_name === 'data_exploration_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <InputFollowup 
        v-else-if="tool_name === 'input_followup_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <DetermineInputObjectives 
        v-else-if="tool_name === 'determine_input_objectives'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <ExecuteSQL 
        v-else-if="tool_name === 'execute_sql_query_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <GenerateQuery 
        v-else-if="tool_name === 'generate_sql_query_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <SQLExecutionFailure 
        v-else-if="tool_name === 'handle_execution_failure_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <AnalyseExecutionResults 
        v-else-if="tool_name === 'process_results_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <QueryVisualization 
        v-else-if="tool_name === 'query_visualization_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <GenerateFinalAnswer 
        v-else-if="tool_name === 'final_answer_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <StreamTermination 
        v-else-if="tool_name === 'stream_termination'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <Fallback 
        v-else
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
    </div>

    <!-- Accordion for Reasoning (when not inside master accordion) -->
    <Accordion 
      v-else-if="tool_output && !isResultNull" 
      type="single"
      :default-value="accordionValue"
      collapsible
      class="tool-display-accordion"
    >
      <AccordionItem value="item-1">
        <AccordionTrigger class="tool-header">
          <div class="flex items-center justify-between w-full pr-3">
            <div class="flex items-center gap-3">
              <Settings class="w-5 h-5 text-blue-600" />
              <span class="text-sm font-medium text-gray-700">{{ getTitle() }}</span>
            </div>
            <CheckCircle class="w-5 h-5 text-green-500" />
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <Card class="tool-content-card">
            <CardContent>
              <!-- Explicit component rendering based on tool name -->
              <NewOrFollowup 
                v-if="tool_name === 'init_assistant'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <QAGrading 
                v-else-if="tool_name === 'qa_grade_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <EnrichInput 
                v-else-if="tool_name === 'enrich_input_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <InterpretInput 
                v-else-if="tool_name === 'interpret_input_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <DataExploration 
                v-else-if="tool_name === 'data_exploration_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <InputFollowup 
                v-else-if="tool_name === 'input_followup_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <DetermineInputObjectives 
                v-else-if="tool_name === 'determine_input_objectives'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <ExecuteSQL 
                v-else-if="tool_name === 'execute_sql_query_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <GenerateQuery 
                v-else-if="tool_name === 'generate_sql_query_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <SQLExecutionFailure 
                v-else-if="tool_name === 'handle_execution_failure_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <AnalyseExecutionResults 
                v-else-if="tool_name === 'process_results_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <QueryVisualization 
                v-else-if="tool_name === 'query_visualization_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <GenerateFinalAnswer 
                v-else-if="tool_name === 'final_answer_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <StreamTermination 
                v-else-if="tool_name === 'stream_termination'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <Fallback 
                v-else
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
            </CardContent>
          </Card>
        </AccordionContent>
      </AccordionItem>
    </Accordion>

    <!-- If no output, show minimal status -->
    <div v-else class="tool-placeholder">
      <Card>
        <CardContent>
          <div class="flex items-center justify-between p-4">
            <div class="flex items-center gap-3">
              <Clock class="w-5 h-5 text-yellow-500" />
              <span class="text-sm text-gray-600">{{ getTitle() }}</span>
            </div>
            <div>
              <Loader2 class="w-5 h-5 text-blue-500 animate-spin" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.tool-display-accordion {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tool-header {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid #e2e8f0;
  padding: 0.75rem 1rem;
}

.tool-content-card {
  margin: 0;
  border: none;
  box-shadow: none;
}

.tool-placeholder {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* Dark mode adjustments */
.dark .tool-header {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-bottom: 1px solid #475569;
}

.dark .tool-header span {
  color: #e2e8f0;
}
</style>