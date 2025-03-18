import {EventSourceOptions, WebSocketOptions} from "@vueuse/core";
import {WebSocketService} from "~/core/streaming/websockets";
import {SSEService} from "~/core/streaming/sse";



export function createStreamingService(type: 'websocket' | 'sse', url: string, options?: WebSocketOptions | EventSourceOptions): StreamingService {
    if (type === 'websocket') {
        return new WebSocketService(url, options as WebSocketOptions)
    } else {
        return new SSEService(url, options)
    }
}