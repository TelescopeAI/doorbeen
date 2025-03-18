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
            const response = await $fetch<ReadableStream>(this.url, {
                method: 'POST',
                body: JSON.stringify(this.options?.body),
                responseType: 'stream',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                },
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
        await $fetch(this.url, {
            method: 'POST',
            body: message,
            headers: {
                'Authorization': `Bearer ${this.token}`,
            },
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
                            const jsonEvent = JSON.parse(line);
                            if (this.messageCallback) {
                                this.messageCallback(jsonEvent);
                            }
                        } catch (error) {
                            console.error('Error parsing JSON:', error);
                        }
                    }
                }
            }

            // Handle any remaining data in the buffer
            if (buffer.trim()) {
                try {
                    const jsonEvent = JSON.parse(buffer);
                    if (this.messageCallback) {
                        this.messageCallback(jsonEvent);
                    }
                } catch (error) {
                    console.error('Error parsing JSON:', error);
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name !== 'AbortError') {
                console.error('Error reading SSE stream:', error);
            }
        }
    }
}