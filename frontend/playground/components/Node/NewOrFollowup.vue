<script setup lang="ts">
import {onMounted} from "vue";

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

onMounted(() => {
  try {
    nodeData.value = typeof props.node === 'string' ? JSON.parse(props.node) : props.node;
  } catch (error) {
    console.error('Error parsing node data:', error);
  }
});
</script>

<template>
<div>
I've read through all the relevant database details
</div>
</template>

<style scoped>

</style>