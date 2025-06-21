<script setup lang="ts">
const props = defineProps({
  node: {
    type: [Object, String],
    required: true
  }
})
</script>

<template>
<div>
  {{ node }}
</div>
</template>

<style scoped>

</style>