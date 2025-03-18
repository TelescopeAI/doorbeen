<script setup lang="ts">
import Button from 'primevue/button';
const emit = defineEmits(['retry']);

const retry = () => {
  console.log("Retrying... [ErrorHandler]");
  emit('retry');
}

</script>

<template>
<div class="flex gap-x-4 justify-center items-center">
  <div class="text-sm text-black font-semibold">
    <p>Looks like something went wrong. Ensure the database and model credentials are valid</p>
    <p></p>
  </div>
  <Button label="Retry" icon="pi pi-refresh" iconPos="right" raised severity="warning" @click="retry"/>
</div>
</template>

<style scoped>

</style>