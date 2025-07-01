import type { Thread } from '~/types/threads'

export const useCurrentThread = () => {
  // Global context for current thread
  const currentThread = useState<Thread | null>('app.currentThread', () => null)
  
  const setCurrentThread = (thread: Thread | null) => {
    currentThread.value = thread
    
    // Save to localStorage on client side only
    if (process.client) {
      if (thread) {
        localStorage.setItem('current-thread-id', thread.id)
      } else {
        localStorage.removeItem('current-thread-id')
      }
    }
  }
  
  const getCurrentThreadId = (): string | null => {
    return currentThread.value?.id || null
  }
  
  const isCurrentThread = (threadId: string): boolean => {
    return currentThread.value?.id === threadId
  }
  
  // Initialize from localStorage on client side
  const initializeFromStorage = async () => {
    if (!process.client) return
    
    const savedThreadId = localStorage.getItem('current-thread-id')
    if (savedThreadId && !currentThread.value) {
      // Only initialize if we don't already have a current thread
      // This prevents overriding when navigating directly to a chat URL
      try {
        const { useThreadStorage } = await import('~/composables/useThreadStorage')
        const threadStorage = useThreadStorage()
        const thread = await threadStorage.getThread(savedThreadId, false)
        currentThread.value = thread
      } catch (error) {
        console.warn('Failed to load saved thread:', error)
        localStorage.removeItem('current-thread-id')
      }
    }
  }
  
  return {
    currentThread: readonly(currentThread),
    setCurrentThread,
    getCurrentThreadId,
    isCurrentThread,
    initializeFromStorage
  }
} 