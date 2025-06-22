<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Button } from '~/components/ui/button'
import { Badge } from '~/components/ui/badge'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '~/components/ui/alert-dialog'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuAction,
} from '~/components/ui/sidebar'
import { useThreadStorage } from '~/composables/useThreadStorage'
import { toast } from 'vue-sonner'
import { 
    MessageSquare, 
    Plus, 
    Trash2
} from 'lucide-vue-next'
import type { Thread } from '~/types/threads'
import ThreadSkeleton from './ThreadSkeleton.vue'

const emit = defineEmits<{
    'thread-selected': [thread: Thread]
    'new-thread': [thread?: Thread]
    'thread-deleted': [deletedThreadId: string]
}>()

const {
    threads,
    isLoading,
    error,
    loadThreads,
    createThread,
    deleteThread,
    getThreadTitle,
    formatThreadDate
} = useThreadStorage()

// Use the global current thread state
const { currentThread, setCurrentThread } = useCurrentThread()

const isDeleteDialogOpen = ref(false)
const threadToDelete = ref<Thread | null>(null)

// Load threads on mount and setup refresh mechanism
onMounted(async () => {
    try {
        await loadThreads()
    } catch (error) {
        console.error('Failed to load threads:', error)
        toast.error('Failed to Load Threads', {
            description: 'Could not load conversation history'
        })
    }
})

// Refresh threads function
const refreshThreads = async () => {
    try {
        await loadThreads()
    } catch (error) {
        console.error('Failed to refresh threads:', error)
    }
}

// Expose refresh function to parent components
defineExpose({
    refreshThreads
})

// Handle thread selection
const selectThread = (thread: Thread) => {
    setCurrentThread(thread)
    emit('thread-selected', thread)
}

// Handle new thread creation - redirect to index instead
const handleNewThread = async () => {
    // Navigate to index route for new conversation
    await navigateTo('/')
}

// Handle thread deletion
const confirmDeleteThread = (thread: Thread) => {
    threadToDelete.value = thread
    isDeleteDialogOpen.value = true
}

const executeDeleteThread = async () => {
    if (!threadToDelete.value) return
    
    try {
        await deleteThread(threadToDelete.value.id)
        
        toast.success('Thread Deleted', {
            description: 'Conversation has been deleted'
        })
        
        // Emit thread deleted event for navigation handling
        emit('thread-deleted', threadToDelete.value.id)
        
    } catch (error) {
        console.error('Failed to delete thread:', error)
        toast.error('Deletion Failed', {
            description: 'Could not delete conversation'
        })
    } finally {
        isDeleteDialogOpen.value = false
        threadToDelete.value = null
    }
}

// Recent threads for quick access (last 5)
const recentThreads = computed(() => {
    return threads.value.slice(0, 5)
})
</script>

<template>
    <div class="space-y-2">
        <!-- New Thread Button -->
        <SidebarMenuItem>
            <SidebarMenuButton
                @click="handleNewThread"
                :disabled="isLoading"
                :class="[
                    'w-full h-auto min-h-[2.75rem] px-3 py-2.5 gap-3',
                    'bg-accent text-accent-foreground hover:bg-accent/80',
                    'border border-border hover:border-accent-foreground/20',
                    'transition-colors duration-200 font-medium',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                ]"
            >
                <Plus class="h-4 w-4 flex-shrink-0" />
                <span>New Conversation</span>
            </SidebarMenuButton>
        </SidebarMenuItem>

        <!-- Recent Threads Section -->
        <div v-if="recentThreads.length > 0" class="space-y-1">
            <SidebarMenuItem v-for="thread in recentThreads" :key="thread.id" class="group">
                <SidebarMenuButton
                    @click="selectThread(thread)"
                    :class="[
                        'w-full justify-start h-auto min-h-[3rem] px-3 py-2.5 gap-3',
                        'hover:bg-accent/50 transition-colors duration-200',
                        currentThread?.id === thread.id ? 
                            'bg-accent/70 text-accent-foreground border-l drop-shadow border-black' : 
                            'hover:border-l-2 hover:border-transparent'
                    ]"
                >
                    <MessageSquare :class="[
                        'h-4 w-4 flex-shrink-0 transition-colors',
                        currentThread?.id === thread.id ? 
                            'text-accent-foreground' : 
                            'text-muted-foreground group-hover:text-foreground'
                    ]" />
                    <div class="flex-1 min-w-0 space-y-1.5">
                        <div class="truncate text-sm font-medium leading-tight">
                            {{ getThreadTitle(thread) }}
                        </div>
                        <div class="text-xs text-muted-foreground leading-tight">
                            {{ formatThreadDate(thread.updated_at) }}
                        </div>
                    </div>
                </SidebarMenuButton>
                <SidebarMenuAction
                    @click="confirmDeleteThread(thread)"
                    :class="[
                        'opacity-0 group-hover:opacity-100 transition-opacity duration-200',
                        'hover:bg-destructive hover:text-destructive-foreground',
                        'w-8 h-8 flex items-center justify-center rounded-md'
                    ]"
                >
                    <Trash2 class="h-3.5 w-3.5" />
                </SidebarMenuAction>
            </SidebarMenuItem>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading && threads.length === 0">
            <ThreadSkeleton :count="3" />
        </div>
        
        <!-- Empty State -->
        <div v-else-if="threads.length === 0" class="text-xs text-muted-foreground p-2">
            No conversations yet
        </div>
        
        <!-- Error Display -->
        <div v-if="error" class="text-xs text-destructive p-2">
            {{ error }}
        </div>
    </div>
    
    <!-- Delete Confirmation Dialog -->
    <AlertDialog :open="isDeleteDialogOpen" @update:open="isDeleteDialogOpen = $event">
        <AlertDialogContent>
            <AlertDialogHeader>
                <AlertDialogTitle>Delete Conversation</AlertDialogTitle>
                <AlertDialogDescription>
                    Are you sure you want to delete "{{ getThreadTitle(threadToDelete!) }}"? 
                    This action cannot be undone and will permanently remove all messages in this conversation.
                </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction @click="executeDeleteThread" class="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                    Delete
                </AlertDialogAction>
            </AlertDialogFooter>
        </AlertDialogContent>
    </AlertDialog>
</template> 