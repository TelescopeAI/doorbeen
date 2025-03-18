import type {StreamResponse} from "~/types/streaming";

export enum ConversationState {
    INITIATED = 'INITIATED',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    RESPONSE = 'RESPONSE',
    ERROR = 'ERROR'
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

export type ConversationMessage = {
    id: string,
    isAgent: boolean,
    message: string,
    time: Date,
    state: ConversationState
    error?: string,
    stats?: MessageStats
    attempts?: Array[MessageAttempt]
    stream?: StreamResponse
}