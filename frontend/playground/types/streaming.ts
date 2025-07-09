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

// EXTENDED: Agent-specific event types for multi-agent coordination
export interface AgentExecutionData extends NodeExecutionData {
    // Agent identification
    agent_name?: string;
    agent_role?: string;
    agent_context?: string;
    
    // Supervisor coordination data
    supervisor_decision?: {
        decision_type: 'route' | 'evaluate' | 'terminate' | 'retry';
        target_agent?: string;
        reasoning: string;
        confidence: number;
        iteration: number;
    };
    
    // Agent handoff information
    handoff_info?: {
        source_agent: string;
        target_agent: string;
        reason: string;
        context: Record<string, any>;
        timestamp: string;
    };
    
    // Agent retry tracking
    agent_retry_count?: number;
    agent_max_retries?: number;
    agent_retry_strategy?: string;
    
    // Enhanced objective tracking
    objectives_status?: {
        identified: string[];
        completed: string[];
        remaining: string[];
        completion_confidence: number;
        overall_status: 'complete' | 'partial' | 'incomplete';
    };
    
    // Agent-specific progress
    agent_progress?: {
        agent_name: string;
        status: 'working' | 'complete' | 'error' | 'handoff';
        progress_percentage: number;
        current_task?: string;
    };
}

// All possible event types from the stream
export type StreamEvent = 
    | NodeExecutionOutput
    | AgentCoordinationOutput
    | AgentToolInvoke
    | AgentStreamOutput
    | AgentStart
    | AgentEnd;

// Generic SSE event structure based on what we receive from the backend
export interface SSEEvent {
    type?: string;
    event?: string;
    name?: string;
    data?: any;
    occurred_at?: string;
    [key: string]: any;
}

// Type definition for a tool invocation event
export type AgentToolInvoke = {
    type: 'agent:tool:invoke';
    name: string;
    data: {
        tool_call_id: string;
        [key: string]: any; // Langchain tool_call format
    };
    occurred_at: string;
};

// Type definition for a streaming text output event
export type AgentStreamOutput = {
    type: 'agent:stream:output';
    name: string;
    data: {
        content: string;
    };
    occurred_at: string;
};

// Type definition for an agent start event
export type AgentStart = {
    type: 'agent:start';
    name: string;
    data: {
        description: string;
        [key: string]: any;
    };
    occurred_at: string;
};

// Type definition for an agent end event
export type AgentEnd = {
    type: 'agent:end';
    name: string;
    data: {
        description: string;
        [key: string]: any;
    };
    occurred_at: string;
};

export type NodeExecutionOutput = {
    type: string;
    name: string;
    data: NodeExecutionData | AgentExecutionData | Record<string, any> | string; // Support a wide range of data
    occurred_at: string;
};

// NEW: Agent coordination event types
export type AgentCoordinationOutput = {
    type: 'assistant:agent:output' | 'supervisor:decision' | 'agent:handoff';
    name: string;
    data: AgentExecutionData;
    occurred_at: string;
    // Backward compatibility mapping
    node_equivalent?: string;
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

// ENHANCED: StreamResponse with agent coordination support
export class StreamResponse {
    nodeOutputs: Array<NodeExecutionOutput> = [];
    
    // NEW: Agent coordination tracking
    agentOutputs: Array<AgentCoordinationOutput> = [];
    supervisorDecisions: Array<any> = [];
    agentHandoffs: Array<any> = [];
    
    // NEW: Agent coordination status
    currentAgent?: string;
    agentProgress?: {
        agent_name: string;
        progress_percentage: number;
        status: 'working' | 'complete' | 'error' | 'handoff';
        familiar_node_name: string;
    };
    
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
            
            // NEW: Initialize agent coordination data
            this.agentOutputs = response.agentOutputs as Array<AgentCoordinationOutput> || [];
            this.supervisorDecisions = response.supervisorDecisions as Array<any> || [];
            this.agentHandoffs = response.agentHandoffs as Array<any> || [];
            this.currentAgent = response.currentAgent as string;
            this.agentProgress = response.agentProgress as any;
            
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
            this.agentOutputs = [];
            this.supervisorDecisions = [];
            this.agentHandoffs = [];
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
    
    // NEW: Agent coordination helper methods
    getCurrentAgent(): string | undefined {
        return this.currentAgent;
    }
    
    getAgentProgress(): any {
        return this.agentProgress;
    }
    
    getSupervisorDecisions(): Array<any> {
        return this.supervisorDecisions;
    }
    
    getAgentHandoffs(): Array<any> {
        return this.agentHandoffs;
    }
    
    // NEW: Backward compatibility mapping
    getFamiliarNodeName(agentName: string): string {
        const agentToNodeMapping = {
            'data_analysis_agent': 'data_exploration_node',
            'query_generation_agent': 'generate_sql_query_node', 
            'result_processing_agent': 'process_results_node',
            'objective_evaluation_agent': 'evaluate_objectives_node',
            'finalization_agent': 'final_answer_node'
        };
        return agentToNodeMapping[agentName] || agentName;
    }
}

