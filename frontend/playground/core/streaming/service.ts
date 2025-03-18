export abstract class StreamingService {
    abstract connect(): void;
    abstract disconnect(): void;
    abstract send(message: any): void;
    abstract onMessage(callback: (data: any) => void): void;
}

