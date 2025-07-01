<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@clerk/vue';
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import { Toaster } from '@/components/ui/sonner'
import 'vue-sonner/style.css' 
import type { Thread } from '~/types/threads'

const router = useRouter()
const route = useRoute()
const { isLoaded, isSignedIn } = useAuth()

// Reference to AppSidebar for refreshing threads
const sidebarRef = ref<InstanceType<typeof AppSidebar> | null>(null)

watch(isLoaded, (val) => {
  if (val) {
    if (!isSignedIn.value) {
      router.push('/auth/login')
    }
  }
})

// Handle thread navigation events from sidebar
const handleThreadSelected = (thread: Thread) => {
  // Navigate to chat route with thread ID
  router.push(`/chat/${thread.id}`)
}

const handleNewThread = async (newThread?: Thread) => {
  // If a new thread was created, navigate to its chat route
  if (newThread) {
    router.push(`/chat/${newThread.id}`)
  } else {
    // Otherwise navigate to main page for new conversation
    router.push('/')
  }
}

const handleThreadDeleted = (deletedThreadId: string) => {
  // If we're currently viewing the deleted thread, navigate to index
  const currentThreadId = route.params.thread?.[0] as string
  if (currentThreadId === deletedThreadId) {
    router.push('/')
  }
}

// Global function to refresh sidebar threads (can be called from any page)
const refreshSidebarThreads = async () => {
  if (sidebarRef.value) {
    await sidebarRef.value.refreshThreads()
  }
}

// Make refresh function globally available
if (process.client) {
  (window as any).refreshSidebarThreads = refreshSidebarThreads
}

</script>

<template>
  <NuxtLoadingIndicator />
  <Html class="h-screen w-screen">
  <Body class="h-screen w-screen">
    <SidebarProvider>
      <AppSidebar 
        ref="sidebarRef"
        @thread-selected="handleThreadSelected"
        @new-thread="handleNewThread"
        @thread-deleted="handleThreadDeleted"
      />
      <main class="flex-1 overflow-auto">
        <AppHeader />
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