import { computed } from 'vue'
import type { 
    Thread, 
    ThreadMessage, 
    ThreadListResponse, 
    ThreadMessagesResponse,
    ThreadSummaryResponse,
    CreateThreadRequest,
    UpdateThreadRequest 
} from '~/types/threads'
import { getAPIServerURL } from '~/composables/server'

export const useThreadStorage = () => {
    // Use Nuxt's useState for SSR-friendly shared context
    const threads = useState<Thread[]>('threads', () => [])
    const isLoading = useState<boolean>('threadsLoading', () => false)
    const error = useState<string | null>('threadsError', () => null)
    
    // Use the global current thread context
    const { currentThread, setCurrentThread, getCurrentThreadId, isCurrentThread } = useCurrentThread()

    // API Base URL
    const apiUrl = getAPIServerURL() + '/api/v1/threads'

    // Create new thread
    const createThread = async (request?: CreateThreadRequest): Promise<Thread> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<{ thread: Thread }>(apiUrl, {
                method: 'POST',
                body: request || {}
            })
            
            const thread = response.thread
            threads.value.unshift(thread) // Add to beginning of list
            setCurrentThread(thread)
            
            return thread
        } catch (err: any) {
            error.value = err.message || 'Failed to create thread'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Load thread list with pagination
    const loadThreads = async (page: number = 1, size: number = 20): Promise<ThreadListResponse> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<ThreadListResponse>(apiUrl, {
                method: 'GET',
                query: { page, size }
            })
            
            if (page === 1) {
                threads.value = response.threads
            } else {
                threads.value.push(...response.threads)
            }
            
            return response
        } catch (err: any) {
            error.value = err.message || 'Failed to load threads'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Get specific thread
    const getThread = async (threadId: string, setAsCurrent: boolean = true): Promise<Thread> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<Thread>(`${apiUrl}/${threadId}`)
            
            // Update in local list if exists
            const index = threads.value.findIndex(t => t.id === threadId)
            if (index >= 0) {
                threads.value[index] = response
            } else {
                threads.value.unshift(response)
            }
            
            // Set as current thread if requested
            if (setAsCurrent) {
                setCurrentThread(response)
            }
            
            return response
        } catch (err: any) {
            error.value = err.message || 'Failed to get thread'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Update thread metadata
    const updateThread = async (threadId: string, request: UpdateThreadRequest): Promise<Thread> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<Thread>(`${apiUrl}/${threadId}`, {
                method: 'PUT',
                body: request
            })
            
            // Update in local list
            const index = threads.value.findIndex(t => t.id === threadId)
            if (index >= 0) {
                threads.value[index] = response
            }
            
            if (getCurrentThreadId() === threadId) {
                setCurrentThread(response)
            }
            
            return response
        } catch (err: any) {
            error.value = err.message || 'Failed to update thread'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Delete thread
    const deleteThread = async (threadId: string): Promise<void> => {
        isLoading.value = true
        error.value = null
        
        try {
            await $fetch(`${apiUrl}/${threadId}`, {
                method: 'DELETE'
            })
            
            // Remove from local list
            threads.value = threads.value.filter(t => t.id !== threadId)
            
            if (getCurrentThreadId() === threadId) {
                setCurrentThread(null)
            }
            
        } catch (err: any) {
            error.value = err.message || 'Failed to delete thread'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Get thread messages
    const getThreadMessages = async (
        threadId: string, 
        page: number = 1, 
        size: number = 50
    ): Promise<ThreadMessagesResponse> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<ThreadMessagesResponse>(`${apiUrl}/${threadId}/messages`, {
                query: { page, size }
            })
            
            return response
        } catch (err: any) {
            error.value = err.message || 'Failed to get thread messages'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Get thread summary (thread + recent messages)
    const getThreadSummary = async (threadId: string): Promise<ThreadSummaryResponse> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<ThreadSummaryResponse>(`${apiUrl}/${threadId}/summary`)
            return response
        } catch (err: any) {
            error.value = err.message || 'Failed to get thread summary'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Get node events for an assistant message
    const getMessageNodeEvents = async (messageId: string): Promise<any> => {
        isLoading.value = true
        error.value = null
        
        try {
            const response = await $fetch<any>(`${getAPIServerURL()}/api/v1/messages/${messageId}/node-events`)
            return response
        } catch (err: any) {
            error.value = err.message || 'Failed to get node events'
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Helper functions
    const getThreadTitle = (thread: Thread): string => {
        return thread.metadata?.title || 
               thread.metadata?.first_question || 
               `Thread ${thread.id.slice(0, 8)}...`
    }

    const formatThreadDate = (dateString: string): string => {
        const date = new Date(dateString)
        const now = new Date()
        const diff = now.getTime() - date.getTime()
        const days = Math.floor(diff / (1000 * 60 * 60 * 24))
        
        if (days === 0) return 'Today'
        if (days === 1) return 'Yesterday'
        if (days < 7) return `${days} days ago`
        return date.toLocaleDateString()
    }



    // Load current thread from localStorage on initialization
    const initializeCurrentThread = async () => {
        // Only run on client side
        if (!process.client) return
        
        const savedThreadId = localStorage.getItem('current-thread-id')
        if (savedThreadId) {
            try {
                const thread = await getThread(savedThreadId, false) // Don't set as current, just load data
                setCurrentThread(thread)
            } catch (error) {
                console.warn('Failed to load saved thread:', error)
                localStorage.removeItem('current-thread-id')
            }
        }
    }

    return {
        // State
        threads,
        isLoading,
        error,
        
        // Actions
        createThread,
        loadThreads,
        getThread,
        updateThread,
        deleteThread,
        getThreadMessages,
        getThreadSummary,
        getMessageNodeEvents,
        setCurrentThread,
        initializeCurrentThread,
        
        // Helpers
        getThreadTitle,
        formatThreadDate
    }
} 