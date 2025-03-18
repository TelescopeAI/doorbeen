<script setup lang="ts">
definePageMeta({
  layout: 'auth',
})

</script>

<template>
    <div class="h-full flex flex-col items-center">
      <AuthLogoBanner />
      <ClientOnly>
        <AuthSignIn/>
      </ClientOnly>
    </div>
</template>

<style>
#__nuxt {
  width: 100vw;
  height: 100vh;
}
</style>