<script setup lang="ts">
import { SignIn } from "vue-clerk";
import { useAuth } from "vue-clerk";

const router = useRouter()
const {isLoaded, isSignedIn} = useAuth()
watch(isLoaded, (val) => {
  if (val) {
    if (!isSignedIn.value) {
      router.push('/')
    }
  }
})
</script>

<template>
  <div class="w-full  h-screen flex flex-col items-center justify-center">
    <SignIn forceRedirectUrl="/" fallbackRedirectUrl="/auth/signup"/>
  </div>
</template>

<style scoped>

</style>