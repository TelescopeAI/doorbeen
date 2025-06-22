import {getAPIServerURL} from "~/composables/server";
import type {MODEL_CONFIG} from "~/types/models";
import {useGenerateUUID4} from "~/composables/uuid";
import {ConversationState} from "~/types/conversations";
import type {FetchContext} from "ofetch";
import {parseDBConfig} from "~/composables/parsing";


async function createSSEConnection(url: string, data: any, onChunk: (chunk: string) => void) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        onChunk(chunk);
    }
}



export const sql_agent_request = async (sample_mode: boolean) => {

    const ask = async (question: string, connection: any, model: MODEL_CONFIG) => {
        let message = {
            isAgent: false,
            message: question,
            time: new Date()
        };
        const parsedConnection = parseDBConfig(connection)
        console.log("Parsed Connection: ", parsedConnection)

        const request_body = {
            question: question,
            model: model,
            connection: parsedConnection,
        }
        console.log("Request Body: ", request_body)
        // Assuming `messages` is managed where this function is called
        // messages.push(message)
        const url = getAPIServerURL() + "/api/v1/assistants";
        let agent_message = {
            id: useGenerateUUID4(),
            isAgent: true,
            state: ConversationState.RESPONSE
        };

        // Adjust the request as necessary, possibly including connection details
        const { data, error } = await useFetch(url, {
            key: url,
            method: "POST",
            body: JSON.stringify(request_body),
            onRequestError({request, options, error}) {
                console.log("Error: ", error);
            }
        });
        if (error.value) {
            console.log("Error: ", error.value)
            agent_message = null
        }
        else {
            agent_message.message = data.value?.output
            agent_message.time = new Date()
        }
        return { agent_message: agent_message, error };
    };

    const ask_sample_db = async (question: string) => {
        let message = {
            isAgent: false,
            message: question,
            time: new Date()
        };
        const url = getAPIServerURL() + "/api/v1/sandbox/agents/sql";
        // Adjust the request as necessary, possibly including connection details
        const { data, error } = await useFetch(url, {
            key: url,
            method: "GET",
            params: {question: question},
            onRequestError(context: FetchContext & { error: Error }): Promise<void> | void {
                console.log("Error: ", context.error);
                return;
            }
        });
        if (error.value) {
            console.log("Error: ", error);
        }
        let agent_message = {
            isAgent: true,
            message: data.value?.output,
            time: new Date(),
            stats: data.value?.stats,
        };
        agent_message.stats.name = "gpt-4o-mini"
        // messages.push(agent_message)

        return { agent_message: agent_message, error };

    }
    return { ask, ask_sample_db };
}

// Enhanced network functions with thread support
export const useThreadAwareAssistant = async (sample_mode: boolean) => {
    const { ask, ask_sample_db } = await sql_agent_request(sample_mode)
    
    // Enhanced ask function with thread support
    const askWithThread = async (
        question: string, 
        connection: any, 
        model: MODEL_CONFIG,
        thread_id?: string,
        message_metadata?: Record<string, any>
    ) => {
        const parsedConnection = parseDBConfig(connection)
        console.log("Parsed Connection: ", parsedConnection)

        const request_body = {
            question: question,
            model: model,
            connection: parsedConnection,
            ...(thread_id && { thread_id }),
            ...(message_metadata && { message_metadata })
        }
        
        console.log("Request Body with Thread: ", request_body)
        
        const url = getAPIServerURL() + "/api/v1/assistants";
        let agent_message: any = {
            id: useGenerateUUID4(),
            isAgent: true,
            state: ConversationState.RESPONSE,
            thread_id: thread_id,
            message: '',
            time: new Date()
        };

        const { data, error } = await useFetch(url, {
            key: `${url}-${thread_id || 'no-thread'}`,
            method: "POST",
            body: JSON.stringify(request_body),
            onRequestError({request, options, error}) {
                console.log("Error: ", error);
            }
        });
        
        if (error.value) {
            console.log("Error: ", error.value)
            agent_message = null
        } else {
            const responseData = data.value as any
            agent_message.message = responseData?.output || ''
            agent_message.time = new Date()
            agent_message.thread_id = responseData?.thread_id || thread_id
            if (responseData?.stats) {
                agent_message.stats = responseData.stats
            }
        }
        
        return { 
            agent_message: agent_message, 
            error, 
            thread_id: (data.value as any)?.thread_id || thread_id 
        };
    };

    // Enhanced streaming with thread support
    const streamWithThread = async (
        question: string, 
        connection: any, 
        model: MODEL_CONFIG,
        thread_id?: string,
        message_metadata?: Record<string, any>,
        onChunk?: (chunk: string) => void
    ) => {
        const parsedConnection = parseDBConfig(connection)
        
        const request_body = {
            question: question,
            model: model,
            connection: parsedConnection,
            ...(thread_id && { thread_id }),
            ...(message_metadata && { message_metadata })
        }
        
        const url = getAPIServerURL() + "/api/v1/assistants";
        
        // Use the existing SSE connection helper
        return createSSEConnection(url, request_body, onChunk || (() => {}));
    };

    // Backward compatibility - use existing functions if no thread needed
    return {
        // Original functions
        ask,
        ask_sample_db,
        
        // Enhanced functions
        askWithThread,
        streamWithThread
    }
}
