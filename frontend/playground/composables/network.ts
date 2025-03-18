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
