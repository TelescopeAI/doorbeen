<script setup lang="ts" xmlns="http://www.w3.org/1999/html">

</script>

<template>
  <NuxtLoadingIndicator />
  <Html class="h-screen w-screen">
  <Body class="h-screen w-screen bg-gray-300 dark:bg-slate-700 bg-logo bg-cover">
  <slot/>
  </Body>
  </Html>
</template>

<style scoped>

</style>