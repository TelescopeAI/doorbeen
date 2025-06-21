<script setup lang="ts">
import { useAuth } from '@clerk/vue';
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import AppSidebar from '@/components/AppSidebar.vue'
import { Toaster } from '@/components/ui/sonner'
import 'vue-sonner/style.css' 

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
    <SidebarProvider>
      <AppSidebar />
      <main class="flex-1 overflow-auto">
        <header class="flex items-center gap-2 p-4 border-b">
          <SidebarTrigger />
        </header>
        <div class="p-4">
  <slot/>
        </div>
      </main>
    </SidebarProvider>
    <Toaster />
  </Body>
  </Html>
</template>

<style scoped>

</style>