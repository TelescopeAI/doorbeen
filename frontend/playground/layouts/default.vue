<script setup lang="ts">
import {useAuth} from "vue-clerk";
const router = useRouter()
const { isLoaded, isSignedIn } = useAuth()
watch(isLoaded, (val) => {
  if (val) {
    if (!isSignedIn.value) {
      router.push('/auth/login')
    }
  }
})

</script>

<template>
  <NuxtLoadingIndicator />
  <Html class="h-screen w-screen">
  <Body class="h-screen w-screen">
  <slot/>
  </Body>
  </Html>
</template>

<style scoped>

</style>