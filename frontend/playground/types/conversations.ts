import type {StreamResponse} from "~/types/streaming";

export enum ConversationState {
    INITIATED = 'INITIATED',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    RESPONSE = 'RESPONSE',
    ERROR = 'ERROR',
    // New states for enhanced backend features
    EXPLORING = 'EXPLORING',
    CIRCUIT_BREAKER = 'CIRCUIT_BREAKER',
    ALTERNATIVE_SUGGESTIONS = 'ALTERNATIVE_SUGGESTIONS'
}

export type MessageAttempt = {
    count: number,
    result: ConversationState
    response: string
}

export type MessageTools = {
    count: number,
    result: ConversationState
    response: string
}

export type MessageStats = {
    total_tokens: number,
    prompt_tokens: number,
    completion_tokens: number,
    total_cost: number,
}

// Enhanced conversation message with new backend features
export type ConversationMessage = {
    id: string,
    isAgent: boolean,
    message: string,
    time: Date,
    state: ConversationState
    error?: string,
    stats?: MessageStats
    attempts?: Array<MessageAttempt>
    stream?: StreamResponse
    
    // New fields for enhanced backend features
    circuit_breaker_status?: {
        triggered: boolean;
        retry_count: number;
        max_retries: number;
        last_error?: string;
    };
    
    exploration_status?: {
        complete: boolean;
        findings?: string;
        tables_explored?: string[];
        current_phase?: string;
    };
    
    result_analysis?: {
        objectives_met: boolean;
        some_objectives_met: boolean;
        insights: string[];
        alternatives?: string[];
        next_steps?: string;
        unmet_objectives?: string[];
    };
    
    // UI context management
    show_alternatives?: boolean;
    show_exploration_details?: boolean;
    processing_phase?: string;
}