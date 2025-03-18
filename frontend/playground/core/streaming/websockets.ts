import { useWebSocket, WebSocketOptions } from '@vueuse/core'
import { StreamingService } from "~/core/streaming/service"
import { Ref } from 'vue'

export class WebSocketService extends StreamingService {
    private socket: ReturnType<typeof useWebSocket>
    private messageCallback: ((data: any) => void) | null = null

    constructor(private url: string, private options?: WebSocketOptions) {
        super()
        this.socket = useWebSocket(url, {
            ...options,
            onMessage: (ws: WebSocket, event: MessageEvent) => {
                if (this.messageCallback) {
                    try {
                        const data = JSON.parse(event.data)
                        this.messageCallback(data)
                    } catch (error) {
                        if(event.data !== 'pong')
                        console.error('Error parsing WebSocket message:', error)
                    }
                }
            },
        })
    }

    connect(): void {
        console.log('WebSocket connected')
    }

    disconnect(): void {
        this.socket.close()
    }

    send(message: any): void {
        this.socket.send(message)
    }

    onMessage(callback: (data: any) => void): void {
        this.messageCallback = callback
    }

    // Expose some useful properties from useWebSocket
    get status(): Ref<WebSocket['readyState']> {
        return this.socket.status
    }

    get data(): Ref<string | null> {
        return this.socket.data
    }

    get isOpen(): Ref<boolean> {
        return this.socket.isOpen
    }

    get isClosed(): Ref<boolean> {
        return this.socket.isClosed
    }
}