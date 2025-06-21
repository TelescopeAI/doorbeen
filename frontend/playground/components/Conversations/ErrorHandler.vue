<script setup lang="ts">
import { Button } from '~/components/ui/button'
import { RefreshCw } from 'lucide-vue-next'
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
  <Button variant="destructive" @click="retry">
    <RefreshCw class="w-4 h-4 mr-2" />
    Retry
  </Button>
</div>
</template>

<style scoped>

</style>