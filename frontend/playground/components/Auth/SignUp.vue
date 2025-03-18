<script setup lang="ts">
import {SignUp} from 'vue-clerk'
</script>

<template>
  <div class="h-full flex flex-col gap-y-6 items-center justify-center">
    <SignUp forceRedirectUrl="/" fallbackRedirectUrl="/auth/login"/>
  </div>
</template>

<style scoped>

</style>