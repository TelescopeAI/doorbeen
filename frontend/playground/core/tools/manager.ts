class ToolCall{
    tool: string;
    input: object = {};
}

enum ResponseState {
    TOOL_CALL="tool_call",
    TOOL_RESULT="tool_result",
    OUTPUT="output"
}

class ToolInvocation {
    call: ToolCall;
    result: any;
}


class ToolManagerState {
    messages?: Array<string> = []
    current_action?: ResponseState = null;
    last_action?: ResponseState = null;
    last_invoke?: ToolInvocation = null;
    invocation_completed?: boolean = false;
    invocations?: Array<ToolInvocation> = [];
}




export class ToolManager {
    state: ToolManagerState = new ToolManagerState();
    parsedStream: Array<any> = [];
    async getMessageMode(tool_obj: object){
        if(tool_obj.hasOwnProperty("tool_call")){
            return ResponseState.TOOL_CALL;
        }
        else if (tool_obj.hasOwnProperty("tool_result")){
            return ResponseState.TOOL_RESULT;
        }
        else if (tool_obj.hasOwnProperty("output")){
            return ResponseState.OUTPUT;
        }
    };

    async parse(value: object){
        // Check if value can be converted to an object otherwise ignore the value
        let message_obj;
        console.log("Parsing Val: ", value)
        try {
            if (value.snapshot === null) return;
            message_obj = JSON.parse(value.snapshot);
        } catch (e) {
            // console.error("Invalid JSON string:", value);
            return; // Ignore the value if it cannot be converted to an object
        }
        console.log("Message Object: ", message_obj)
        let message_mode = await this.getMessageMode(message_obj);
        console.log("Message Mode: ", message_mode)
        let isLastActionCall = this.state.last_action === "tool_call";
        console.log("Is Last Action Call: ", isLastActionCall)
        let isLastActionResult = this.state.last_action === "tool_result";
        let isLastActionOutput = this.state.last_action === "output";
        let flushResult = message_mode === "tool_result" && isLastActionCall;
        const updateOutput = message_mode === "output" && isLastActionOutput;
        console.log("Flush Result: ", flushResult)
        let tool_invoke = new ToolInvocation()
        this.state.current_action = message_mode;
        console.log("State: ", this.state)

        if(message_mode === "tool_call"){
            tool_invoke.call = message_obj;
            this.state.invocations.push(tool_invoke);
            this.parsedStream.push(tool_invoke);
            this.state.invocation_completed = false;
        }
        else if(flushResult){
            const first_invocation = this.state.invocations.length === 1
            const flush_index = first_invocation ? 0 : this.state.invocations.length - 1;
            this.state.invocations[flush_index].result = message_obj;
            this.parsedStream[flush_index] = this.state.invocations[flush_index];
            this.state.invocation_completed = true;
        }
        else if(isLastActionResult && message_mode === "output"){
            this.parsedStream.push(message_obj)
        }
        else if(updateOutput){
            const last_index = this.parsedStream.length - 1;
            this.parsedStream[last_index] = message_obj;
        }
        this.state.last_action = message_mode;
        this.state.last_invoke = tool_invoke;
    }

    async process(messages: Array<string>){
        for(let message of messages){
            console.log("Processing Message: ", message)
            await this.parse(message);
        }
    }

    async clear(){
        this.state = new ToolManagerState();
        this.parsedStream = [];
    }
}