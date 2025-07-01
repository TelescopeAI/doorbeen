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
import SupervisorEvent from '~/components/Node/SupervisorEvent.vue';

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

// Accordion context management
const localExpandedState = ref(true); // Default to expanded
const accordionValue = computed(() => {
  // If forceExpanded is explicitly set, use it; otherwise use local context
  if (props.forceExpanded !== undefined) {
    return props.forceExpanded ? "item-1" : "";
  }
  return localExpandedState.value ? "item-1" : "";
});

// Watch for forceExpanded changes to update local context
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
  // NEW: Supervisor-specific event titles
  else if(tool_name === 'supervisor_node'){
    return 'Multi-agent supervisor coordinating analysis'
  }
  else if(tool_name === 'supervisor_initialized'){
    return 'Supervisor initialized - Multi-agent coordination starting'
  }
  else if(tool_name === 'agent_handoff'){
    return 'Supervisor delegating task to specialized agent'
  }
  else if(tool_name === 'agent_completed'){
    return 'Agent completed task - returning to supervisor'
  }
  else if(tool_name === 'agent_failed'){
    return 'Agent encountered error - supervisor handling retry'
  }
  else if(tool_name === 'agent_retry'){
    return 'Supervisor retrying failed agent with different strategy'
  }
  else if(tool_name === 'supervisor_completed'){
    return 'Multi-agent coordination completed successfully'
  }
  // Agent-specific titles
  else if(tool_name === 'DataAnalysisAgent' || tool_name === 'data_analysis' || tool_name === 'DataAnalyst'){
    return 'Data Analysis Agent exploring database structure'
  }
  else if(tool_name === 'QueryGenerationAgent' || tool_name === 'query_generation' || tool_name === 'QueryGenerator'){
    return 'Query Generation Agent creating SQL queries'
  }
  else if(tool_name === 'ResultProcessingAgent' || tool_name === 'result_processing' || tool_name === 'ResultProcessor'){
    return 'Result Processing Agent analyzing query results'
  }
  else if(tool_name === 'ObjectiveEvaluationAgent' || tool_name === 'objective_evaluation' || tool_name === 'ObjectiveEvaluator'){
    return 'Objective Evaluation Agent checking if goals are met'
  }
  else if(tool_name === 'FinalizationAgent' || tool_name === 'finalization' || tool_name === 'Finalizer'){
    return 'Finalization Agent preparing final response'
  }
  else if(tool_name === 'sql_supervisor'){
    return 'Supervisor making a decision'
  }
  // Linear node titles
  else if(tool_name === 'enrich_input_node'){
    return 'Enriching the question with more context'
  }
  else if(tool_name === 'input_followup_node'){
    return 'Processing followup question based on the previous conversation'
  }
  else if(tool_name === 'interpret_input_node'){
    return 'Understanding the question and forming the objective'
  }
  else if(tool_name === 'data_exploration_node' || tool_name === 'DataAnalysisAgent'){
    return 'Exploring the database to understand the available data'
  }
  else if(tool_name === 'determine_input_objectives'){
    return 'Clarifying the input objectives and determining what data to gather'
  }
  else if(tool_name === 'generate_sql_query_node' || tool_name === 'QueryGenerationAgent'){
    return 'Generating the SQL Query to fetch the data'
  }
  else if(tool_name === 'execute_sql_query_node'){
    return 'Executing the SQL Query'
  }
  else if(tool_name === 'handle_execution_failure_node'){
    return 'Trying to fix the generated query'
  }
  else if(tool_name === 'process_results_node' || tool_name === 'ResultProcessingAgent'){
    return 'Analysing the data to find insights'
  }
  else if(tool_name === 'query_visualization_node'){
    return 'Planning data visualization and charts'
  }
  else if(tool_name === 'final_answer_node' || tool_name === 'FinalizationAgent' || tool_name === 'ObjectiveEvaluationAgent'){
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
        v-else-if="tool_name === 'data_exploration_node' || tool_name === 'DataAnalysisAgent'"
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
      <SupervisorEvent
        v-else-if="tool_name === 'sql_supervisor'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <ExecuteSQL 
        v-else-if="tool_name === 'execute_sql_query_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <GenerateQuery 
        v-else-if="tool_name === 'generate_sql_query_node' || tool_name === 'QueryGenerationAgent'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <SQLExecutionFailure 
        v-else-if="tool_name === 'handle_execution_failure_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <AnalyseExecutionResults 
        v-else-if="tool_name === 'process_results_node' || tool_name === 'ResultProcessingAgent'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <QueryVisualization 
        v-else-if="tool_name === 'query_visualization_node'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <GenerateFinalAnswer 
        v-else-if="tool_name === 'final_answer_node' || tool_name === 'FinalizationAgent' || tool_name === 'ObjectiveEvaluationAgent'"
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
      <StreamTermination 
        v-else-if="tool_name === 'stream_termination'"
        :node="tool_output" 
      />
      <Fallback 
        v-else
        :node="tool_output" 
        @start-new-question="handleStartNewQuestion"
      />
    </div>

    <!-- Accordion view for main display -->
    <Accordion v-else type="single" collapsible class="w-full" :value="accordionValue" @update:modelValue="localExpandedState = !!$event">
      <AccordionItem value="item-1">
        <AccordionTrigger>
          <div class="flex flex-row items-center justify-between text-gray-500 w-full">
            <div class="flex flex-row items-center space-x-2">
              <Settings v-if="tool_name === 'fallback_node' || tool_name === 'default_node' || getTitle() === 'Unknown tool'" class="h-4 w-4" />
              <CheckCircle v-else-if="tool_output && !isResultNull" class="h-4 w-4" />
              <Clock v-else class="h-4 w-4" />
              <span class="text-sm font-normal">{{ getTitle() }}</span>
            </div>
            <Loader2 
              v-if="!tool_output || isResultNull" 
              class="h-4 w-4 animate-spin text-gray-400" 
            />
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <Card>
            <CardContent v-if="tool_output && !isResultNull" class="p-4">
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
                v-else-if="tool_name === 'data_exploration_node' || tool_name === 'DataAnalysisAgent'"
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
              <SupervisorEvent
                v-else-if="tool_name === 'sql_supervisor'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <ExecuteSQL 
                v-else-if="tool_name === 'execute_sql_query_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <GenerateQuery 
                v-else-if="tool_name === 'generate_sql_query_node' || tool_name === 'QueryGenerationAgent'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <SQLExecutionFailure 
                v-else-if="tool_name === 'handle_execution_failure_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <AnalyseExecutionResults 
                v-else-if="tool_name === 'process_results_node' || tool_name === 'ResultProcessingAgent'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <QueryVisualization 
                v-else-if="tool_name === 'query_visualization_node'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <GenerateFinalAnswer 
                v-else-if="tool_name === 'final_answer_node' || tool_name === 'FinalizationAgent' || tool_name === 'ObjectiveEvaluationAgent'"
                :node="tool_output" 
                @start-new-question="handleStartNewQuestion"
              />
              <StreamTermination 
                v-else-if="tool_name === 'stream_termination'"
                :node="tool_output" 
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