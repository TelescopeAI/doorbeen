<script setup lang="ts">
import { ref } from 'vue'
import { Settings, Home, Briefcase, MessageSquare } from "lucide-vue-next"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import Logo from "@/components/Logo.vue"
import AuthManageUser from "@/components/Auth/ManageUser.vue"
import ThreadList from "@/components/Threads/ThreadList.vue"
import type { Thread } from "~/types/threads"

const emit = defineEmits<{
    'thread-selected': [thread: Thread]
    'new-thread': [thread?: Thread]
    'thread-deleted': [deletedThreadId: string]
}>()

// Reference to ThreadList component for refreshing
const threadListRef = ref<InstanceType<typeof ThreadList> | null>(null)

// Handle thread events from ThreadList component
const handleThreadSelected = (thread: Thread) => {
    emit('thread-selected', thread)
}

const handleNewThread = (newThread?: Thread) => {
    emit('new-thread', newThread)
}

const handleThreadDeleted = (deletedThreadId: string) => {
    emit('thread-deleted', deletedThreadId)
}

// Expose refresh function for external components
const refreshThreads = async () => {
    if (threadListRef.value) {
        await threadListRef.value.refreshThreads()
    }
}

defineExpose({
    refreshThreads
})

// Menu items
const items = [
  {
    title: "Playground",
    url: "/",
    icon: Home,
  },
  {
    title: "Settings",
    url: "/settings",
    icon: Settings,
  },
  
]
</script>

<template>
  <Sidebar>
    <!-- Sidebar Header with Logo -->
    <SidebarHeader>
      <div class="px-2 py-2">
        <Logo />
      </div>
    </SidebarHeader>

    <!-- Sidebar Content with Navigation -->
    <SidebarContent>
      <!-- Navigation Menu -->
      <SidebarGroup>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="item in items" :key="item.title">
              <SidebarMenuButton asChild>
                <NuxtLink :to="item.url">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </NuxtLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <!-- Recent Conversations -->
      <SidebarGroup>
        <SidebarGroupLabel class="flex items-center gap-2">
          <MessageSquare class="h-4 w-4" />
          Recent Conversations
        </SidebarGroupLabel>
        <SidebarGroupContent class="space-y-2">
          <SidebarMenu>
            <ThreadList 
              ref="threadListRef"
              @thread-selected="handleThreadSelected"
              @new-thread="handleNewThread"
              @thread-deleted="handleThreadDeleted"
            />
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <!-- Sidebar Footer with User Authentication -->
    <SidebarFooter>
      <div class="px-2 py-2">
        <ClientOnly>
          <AuthManageUser />
        </ClientOnly>
      </div>
    </SidebarFooter>
  </Sidebar>
</template> 