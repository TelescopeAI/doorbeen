<script setup lang="ts">
import { computed } from 'vue'
import { StreamResponse } from "~/types/streaming";

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const stream = computed(() => props.message?.stream || new StreamResponse())
</script>

<template>
  <div class="flex flex-col gap-y-1 pb-8" v-if="stream">
    <div v-for="item in stream.nodeOutputs" :key="item.id" class="bg-primary">
      <ReasoningNodeOutputDisplay :node="item" />
    </div>
<!--    <div v-if="result">-->
<!--      <ReasoningOutputDisplay :result="result" />-->
<!--    </div>-->
  </div>

</template>

<style scoped>

</style>