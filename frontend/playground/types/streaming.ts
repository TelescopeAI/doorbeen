export type ToolCallResponse = {
    name: string,
    input: object
}

export interface NodeExecutionData {
    // Basic node output
    content?: string;
    
    // Circuit breaker status
    circuit_breaker_triggered?: boolean;
    retry_count?: number;
    max_retries?: number;
    last_error?: string;
    
    // Data exploration
    exploration_complete?: boolean;
    exploration_findings?: string;
    tables_explored?: string[];
    priority_tables?: string[];
    exploration_queries?: {
        objective?: string;
        query: string;
        status: string;
        rowCount?: number;
        results?: any[];
        explanation?: string;
    }[];
    
    // Additional exploration fields
    findings?: string;
    error?: string;
    domain_insights?: string;
    patterns_found?: string[];
    
    // Result processing
    all_objectives_met?: boolean;
    some_objectives_met?: boolean;
    insights?: string[];
    unmet_objectives?: string[];
    next_step?: string;
    alternative_suggestions?: string[];
    
    // Query execution status
    query_executed?: string;
    results_count?: number;
    execution_error?: string;
}

export type NodeExecutionOutput = {
    type: string;
    name: string;
    data: NodeExecutionData | string; // Support both structured and simple data
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

// Enhanced StreamResponse with better node tracking
export class StreamResponse {
    nodeOutputs: Array<NodeExecutionOutput> = [];
    
    // Enhanced status tracking
    currentPhase?: string;
    explorationStatus?: {
        complete: boolean;
        findings?: string;
        tablesExplored?: string[];
    };
    circuitBreakerStatus?: {
        triggered: boolean;
        retryCount: number;
        maxRetries: number;
        lastError?: string;
    };
    resultAnalysis?: {
        objectivesMet: boolean;
        insights: string[];
        alternatives?: string[];
        nextSteps?: string;
    };

    constructor(response: Object | null) {
        if (response) {
            this.nodeOutputs = response.nodeOutputs as Array<NodeExecutionOutput> || [];
            // Initialize enhanced status from response if available
            if (response.explorationStatus) {
                this.explorationStatus = response.explorationStatus as any;
            }
            if (response.circuitBreakerStatus) {
                this.circuitBreakerStatus = response.circuitBreakerStatus as any;
            }
            if (response.resultAnalysis) {
                this.resultAnalysis = response.resultAnalysis as any;
            }
        }
        else {
            this.nodeOutputs = [];
        }
    }
    
    // Helper methods for enhanced functionality
    getLatestNodeByType(nodeType: string): NodeExecutionOutput | undefined {
        return this.nodeOutputs
            .filter(node => node.name.includes(nodeType))
            .pop();
    }
    
    hasCircuitBreakerTriggered(): boolean {
        return this.circuitBreakerStatus?.triggered || false;
    }
    
    isExplorationComplete(): boolean {
        return this.explorationStatus?.complete || false;
    }
    
    getInsights(): string[] {
        return this.resultAnalysis?.insights || [];
    }
    
    getAlternatives(): string[] {
        return this.resultAnalysis?.alternatives || [];
    }
}

