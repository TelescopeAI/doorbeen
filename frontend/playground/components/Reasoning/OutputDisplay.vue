<script setup lang="ts">
import { computed } from 'vue'
import { StreamOutput } from "~/types/streaming";

const props = defineProps({
  result: {
    type: Object,
    default: () => new StreamOutput()
  }
})

const content = computed(() => {
  let output: string | null = props.result?.output ?? null
  if(output !== null && output !== undefined && output !== '') {
    return output.replace(/\\n/g, '\n').replace(/\n\n/g, '\n')
  }
  return null
})
</script>

<template>
  <div>
    <div class="p-4 rounded-lg" v-if="content !== null">
      <div class="text-sm font-semibold text-gray-500">Result</div>
      <div class="text-sm text-gray-700">
        <MDRenderer :md="content" cid="reasoning" class="p-4 w-full"/>
      </div>
  </div>
  </div>
</template>

<style scoped>

</style>