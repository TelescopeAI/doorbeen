import { ref } from 'vue'
import { toast } from 'vue-sonner'

export function useAbortController() {
  const abortController = ref<AbortController | null>(null)
  const isAborting = ref(false)

  const createAbortController = () => {
    // Clean up existing controller
    if (abortController.value) {
      abortController.value.abort()
    }
    
    // Create new controller
    abortController.value = new AbortController()
    return abortController.value
  }

  const abortRequest = () => {
    if (isAborting.value) return
    
    isAborting.value = true
    
    try {
      // Abort the current fetch request if it exists
      if (abortController.value) {
        abortController.value.abort()
      }

      console.log('✅ Request aborted successfully')
      toast.info('Analysis Stopped', { 
        description: 'Processing has been cancelled' 
      })
      
    } catch (error) {
      console.error('❌ Error aborting request:', error)
    } finally {
      isAborting.value = false
    }
  }

  const cleanup = () => {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
  }

  return {
    abortController: readonly(abortController),
    isAborting: readonly(isAborting),
    createAbortController,
    abortRequest,
    cleanup
  }
} 