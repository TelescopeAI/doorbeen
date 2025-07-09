import { StreamingService } from "~/core/streaming/service";
import { FetchError } from 'ofetch';

export class SSEService extends StreamingService {
    private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    private abortController: AbortController | null = null;

    constructor(private url: string, private token:string, private options?: RequestInit) {
        super();
    }

    async connect(): Promise<void> {
        this.abortController = new AbortController();
        const { signal } = this.abortController;

        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            
            // Only add Authorization header if token is provided
            if (this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const response = await $fetch<ReadableStream>(this.url, {
                method: 'POST',
                body: JSON.stringify(this.options?.body),
                responseType: 'stream',
                headers,
                signal,
                // credentials: 'include',

            });

            if (response) {
                this.reader = response.getReader();
                console.log('SSE connected');
                this.readChunks();
            }
        } catch (error) {
            if (error instanceof FetchError && error.name !== 'AbortError') {
                console.error('SSE connection error:', error);
            }
        }
    }

    disconnect(): void {
        this.abortController?.abort();
        this.reader?.cancel();
        this.abortController = null;
        this.reader = null;
        console.log('SSE disconnected');
    }

    async send(message: any): Promise<void> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        
        // Only add Authorization header if token is provided
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        await $fetch(this.url, {
            method: 'POST',
            body: message,
            headers,
            // credentials: 'include',

        });
    }

    onMessage(callback: (data: any) => void): void {
        this.messageCallback = callback;
    }

    private messageCallback: ((data: any) => void) | null = null;

    private async readChunks(): Promise<void> {
        if (!this.reader) return;

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { value, done } = await this.reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';  // Keep the last incomplete line in the buffer

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            // Trim the line and remove the 'data: ' prefix if it exists
                            const trimmedLine = line.trim();
                            console.log('📡 SSE raw line:', trimmedLine);
                            const dataString = trimmedLine.startsWith('data: ') ? trimmedLine.substring(6) : trimmedLine;
                            console.log('📡 SSE parsed data string:', dataString);
                            const parsedData = JSON.parse(dataString);
                            console.log('📡 SSE parsed event:', parsedData.type, parsedData);
                            console.log('📡 SSE messageCallback exists:', !!this.messageCallback);
                            if (this.messageCallback) {
                                console.log('📡 SSE calling messageCallback for:', parsedData.type);
                                this.messageCallback(parsedData);
                                console.log('📡 SSE messageCallback called successfully');
                            } else {
                                console.error('📡 SSE messageCallback is null!');
                            }
                        } catch (error) {
                            console.error('📡 SSE parse error:', error, 'for line:', line);
                        }
                    }
                }
            }

            // Handle any remaining data in the buffer
            if (buffer.trim()) {
                try {
                    const eventWrapper = JSON.parse(buffer.trim());
                     if (eventWrapper && typeof eventWrapper.data === 'string') {
                        const jsonEvent = JSON.parse(eventWrapper.data);
                        console.log("Received SSE Event (buffer):", jsonEvent);
                    if (this.messageCallback) {
                        this.messageCallback(jsonEvent);
                        }
                    }
                } catch (error) {
                    console.error('Error parsing nested JSON from buffer:', error, 'Original buffer:', buffer);
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name !== 'AbortError') {
                console.error('Error reading SSE stream:', error);
            }
        }
    }
}