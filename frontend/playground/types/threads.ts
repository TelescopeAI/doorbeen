import type { ConversationMessage } from '~/types/conversations'

// Types matching our backend API implementation
export interface Thread {
    id: string;
    created_at: string;
    updated_at: string;
    metadata: Record<string, any>;
    message_count?: number;
}

export interface ThreadMessage {
    id: string;
    thread_id: string;
    content: string;
    role: 'user' | 'assistant' | 'system' | 'tool';
    created_at: string;
    metadata: Record<string, any>;
}

export interface ThreadListResponse {
    threads: Thread[];
    total: number;
    page: number;
    size: number;
    has_more: boolean;
}

export interface ThreadMessagesResponse {
    messages: ThreadMessage[];
    total: number;
    page: number;
    size: number;
    has_more: boolean;
}

export interface ThreadSummaryResponse {
    thread: Thread;
    messages: ThreadMessage[];
    total_messages: number;
    has_more: boolean;
}

// Request types for API calls
export interface CreateThreadRequest {
    metadata?: Record<string, any>;
}

export interface UpdateThreadRequest {
    metadata: Record<string, any>;
}

// Enhanced conversation types
export interface EnhancedConversationMessage extends ConversationMessage {
    thread_id?: string;
    message_metadata?: Record<string, any>;
} 