<script setup lang="ts">
import Accordion from 'primevue/accordion';
import AccordionPanel from 'primevue/accordionpanel';
import AccordionHeader from 'primevue/accordionheader';
import AccordionContent from 'primevue/accordioncontent';
import Card from 'primevue/card';
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



const props = defineProps({
  node: {
    type: Object,
    default: () => ({})
  }
})
const node_obj = ref(props.node)
const tool_name = ref(props.node.name)
const tool_input = ref('')
const tool_output = ref(null)

watchEffect(() => {
  const node_obj = props.node
  tool_name.value = node_obj.name
  tool_output.value = node_obj.data
  console.log("ToolDisplay: ", node_obj.value)
})

const isResultNull = computed(() => {
  return tool_output.value === null || tool_output.value === undefined
})

const toolInputString = computed(() => {
  return JSON.stringify(tool_input.value)
})

const toolOutputString = computed(() => {
  if (tool_output.value === null) {
    return 'No output'
  }
  else{
    // Add an indentation of 4 spaces to the parsed JSON

    let parsed = tool_output.value
    console.log(JSON.stringify(parsed, null, 4))
    // let parsed = JSON.stringify(tool_output.value, null, 4)
    return parsed
  //   Remove the quotes from the first and last character
  //   Replace /n, /t, /r with respective new line, tab, and carriage return
  //   return parsed.substring(1, parsed.length - 1)
  //                .replace(/\\n/g, '\n')
  //                .replace(/\\t/g, '\t')
  //                .replace(/\\r/g, '\r')
  }
})

const tool_purpose = (tool_name: string) => {
  if (tool_name === 'init_assistant') {
    return 'Collecting details about the database'
  }
  else if(tool_name === 'qa_grade_node'){
    return 'Checking if I have all I need to answer your question'
  }
  else if(tool_name === 'interpret_input_node'){
    return 'Thinking about how to fetch the data'
  }
  else if(tool_name === 'enrich_input_node'){
    return 'Reframing your question to get better results'
  }
  else if(tool_name === 'generate_sql_query_node'){
    return 'Generating Query to fetch relevant results'
  }
  else if(tool_name === 'execute_sql_query_node'){
    return 'Executing the SQL query'
  }
  else if(tool_name === 'handle_execution_failure_node'){
    return 'Ran into an error. Trying to fix the generated query'
  }
  else if(tool_name === 'process_results_node'){
    return 'Analysing the data to find insights'
  }else if(tool_name === 'final_answer_node'){
    return 'Generating Final Answer'
  }
  else {
    return 'Unknown tool'
  }
}

const getNodeComponent = computed(() => {
  const toolName = props.node.name;

  // Logic to map tool_name to component name
  if (toolName === 'init_assistant') {
    return NewOrFollowup;
  } else if (toolName === 'qa_grade_node') {
    return QAGrading;
  }
  else if (toolName === 'enrich_input_node') {
    return EnrichInput;
  }
  else if (toolName === 'interpret_input_node') {
    return InterpretInput;
  }
  else if (toolName === 'execute_sql_query_node') {
    return ExecuteSQL;
  }
  else if(toolName === 'generate_sql_query_node'){
    return GenerateQuery;
  }
  else if (toolName === 'handle_execution_failure_node') {
    return SQLExecutionFailure;
  }
  else if (toolName === 'process_results_node') {
    return AnalyseExecutionResults;
  }
  else if (toolName === 'final_answer_node') {
    return GenerateFinalAnswer;
  }
  console.warn(`No specific component found for ${toolName}, using Fallback`);
  return Fallback;
});
</script>


<template>
  <div class="card max-w-lg md:max-w-screen-lg lg:max-w-screen-2xl">
    <Accordion :activeIndex="0" expandIcon="pi pi-angle-down" collapseIcon="pi pi-angle-up"
               multiple :pt="{root: {class: 'flex flex-col gap-y-2 w-full'}}"
               :pt-options="{mergeProps: true, mergeSections:true}"

    >
      <AccordionPanel :pt="{root: {class: 'border-b-0 bg-[#f7f7f7] rounded'}}"
                      :pt-options="{mergeProps: true, mergeSections:true}">
        <AccordionHeader :pt="{root: {class: 'p-3 flex items-center bg-indigo-50 text-black border-b-0 w-full rounded'}}"
                         :pt-options="{mergeProps: true, mergeSections:true}"

        >
          <span class="w-full grow flex justify-between items-center">
            <span class="text-md font-medium text-gray-600 tracking-wide">
              {{ tool_purpose(tool_name)}}
            </span>
            <Icon :name="isResultNull ? 'svg-spinners:90-ring-with-bg' : 'material-symbols:check-circle'"
                  :class="{'text-green-500' : !isResultNull, 'text-slate-500' : isResultNull}"
                  class="mr-4"
                  size="24"/>
          </span>

        </AccordionHeader>
        <AccordionContent>
        <div class="content p-4 flex flex-col gap-y-6">
          <div class="text-sm font-semibold">
            <div>
              <Card pt:root:class="border border-white bg-white drop-shadow-none max-w-[80vw]"
                    :pt-options="{mergeProps: true, mergeSections:true}">
                <template #content>
                  <p>
                    <component :is="getNodeComponent" :node="toolOutputString" />
                  </p>
                </template>
              </Card>
              {{ tools_obj}}
            </div>
          </div>
        </div>
        </AccordionContent>
      </AccordionPanel>
    </Accordion>
  </div>
</template>

<style scoped>
</style>