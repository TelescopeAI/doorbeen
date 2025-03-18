<script setup lang="ts">
const props = defineProps({
  raw: {
    type: String,
  }
})

const query = ref(props.raw)
watch(() => props.raw, (newQuery) => {
  query.value = newQuery
}, { deep: true })

</script>

<template>
<div>
  {{ raw}}
</div>
</template>

<style scoped>

</style>