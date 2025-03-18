<script setup lang="ts">
</script>

<template>
  <div class="navbar w-full place-self-center flex gap-x-4 items-center justify-between">
    <Logo/>
    <ClientOnly>
      <AuthManageUser/>
    </ClientOnly>
  </div>

</template>

<style scoped>

</style>