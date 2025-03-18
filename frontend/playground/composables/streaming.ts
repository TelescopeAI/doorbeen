import { ref, onMounted, onUnmounted } from 'vue'
import { createStreamingService } from '~/core/streaming/factory'
import type { StreamingService } from '~/core/streaming/service'

export function useStreamingService(type: 'websocket' | 'sse', url: string, options?: any) {
    const messages = ref<any[]>([])
    const service = ref<StreamingService | null>(null)
    const isConnected = ref(false)

    const connect = async () => {
        if (!service.value) {
            service.value = createStreamingService(type, url, options)
        }
        
        if (service.value && !isConnected.value) {
            await service.value.connect()
            isConnected.value = true
            
            service.value.onMessage((data) => {
                messages.value.push(data)
            })
        }
    }

    const disconnect = () => {
        if (service.value && isConnected.value) {
            service.value.disconnect()
            isConnected.value = false
        }
    }

    const sendMessage = (message: any) => {
        if (service.value && isConnected.value) {
            service.value.send(message)
        }
    }

    if (process.client) {
        onMounted(connect)
        onUnmounted(disconnect)
    }

    return {
        messages,
        sendMessage,
        service,
        connect,
        disconnect,
        isConnected
    }
}