<script setup lang="ts">
const props = defineProps({
  node: {
    type: [Object, String],
    required: true
  }
})
</script>

<template>
<pre class="whitespace-pre-wrap">
  {{ node }}
</pre>
</template>

<style scoped>

</style>