export type ToolCallResponse = {
    name: string,
    input: object
}

export type NodeExecutionOutput = {
    type: string;
    name: string;
    data: string;
    occurred_at: string;
};

export class ToolCallInvoke  {
    call: ToolCallResponse
    result: any
    invocation_completed: boolean = false

    constructor(invoke: Object) {
        this.call = invoke.call as ToolCallResponse
        this.result = invoke.result ? invoke.result : null
        this.invocation_completed = invoke.invocation_completed ? invoke.invocation_completed : false
    }
}

export class StreamOutput {
    output: string | null
    streaming_complete: boolean = false

    constructor(output: Object | null) {
        if(output) {
            this.output = output.output as string
            this.streaming_complete = output.streaming_complete as boolean
        }
        else {
            this.output = null
            this.streaming_complete = false
        }
    }
}

// Update the StreamResponse type to only include NodeOutput
export class StreamResponse {
    nodeOutputs: Array<NodeExecutionOutput> = [];

    constructor(response: Object | null) {
        if (response) {
            this.nodeOutputs = response.nodeOutputs as Array<NodeExecutionOutput> || [];
        }
        else {
            this.nodeOutputs = [];
        }
    }
}

