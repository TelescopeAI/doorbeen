<script setup lang="ts">
const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})
</script>

<template>
<div>
  {{node}}
</div>
</template>

<style scoped>

</style>