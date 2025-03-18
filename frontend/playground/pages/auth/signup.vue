<script setup lang="ts">
definePageMeta({
  layout: 'auth',
})

</script>

<template>
  <ClientOnly>
    <AuthLogoBanner />
    <AuthSignUp/>
  </ClientOnly>
</template>

<style>
#__nuxt {
  width: 100vw;
  height: 100vh;
}
</style>