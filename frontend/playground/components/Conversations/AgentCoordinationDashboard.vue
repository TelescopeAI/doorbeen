<template>
    <div class="agent-coordination-dashboard">
        <!-- Header -->
        <div class="dashboard-header mb-6">
            <h3 class="text-lg font-semibold mb-2">Agent Coordination Dashboard</h3>
            <div class="flex items-center gap-4">
                <Badge :variant="getModeVariant()" class="text-sm">
                    {{ useSupervisor ? 'Multi-Agent Mode' : 'Linear Mode' }}
                </Badge>
                <Badge variant="outline" v-if="currentIteration">
                    Iteration: {{ currentIteration }}
                </Badge>
                <Badge variant="outline" v-if="totalAgentsInvolved">
                    Agents: {{ totalAgentsInvolved }}
                </Badge>
            </div>
        </div>

        <!-- Agent Flow Visualization -->
        <Card class="mb-6">
            <CardHeader>
                <CardTitle class="flex items-center gap-2">
                    <GitBranch class="h-5 w-5" />
                    Agent Execution Flow
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div class="agent-flow">
                    <div v-for="(agent, index) in agentFlow" :key="index" 
                         class="flex items-center gap-2 mb-3">
                        <!-- Agent Icon -->
                        <div class="flex-shrink-0">
                            <div :class="getAgentStatusClass(agent)" class="agent-step">
                                <component :is="getAgentIcon(agent.name)" class="h-4 w-4" />
                            </div>
                        </div>
                        
                        <!-- Agent Info -->
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="font-medium">{{ getAgentDisplayName(agent.name) }}</span>
                                <Badge :variant="getAgentStatusVariant(agent.status)" class="text-xs">
                                    {{ agent.status }}
                                </Badge>
                                <span v-if="agent.duration" class="text-xs text-muted-foreground">
                                    {{ agent.duration }}ms
                                </span>
                            </div>
                            <div class="text-sm text-muted-foreground">
                                {{ agent.context || 'Processing...' }}
                            </div>
                        </div>
                        
                        <!-- Connection Arrow -->
                        <div v-if="index < agentFlow.length - 1" class="flex-shrink-0">
                            <ArrowDown class="h-4 w-4 text-muted-foreground" />
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>

        <!-- Supervisor Decisions Tab -->
        <Tabs default-value="decisions" class="mb-6">
            <TabsList class="grid w-full grid-cols-4">
                <TabsTrigger value="decisions">Supervisor Decisions</TabsTrigger>
                <TabsTrigger value="handoffs">Agent Handoffs</TabsTrigger>
                <TabsTrigger value="retries">Retry History</TabsTrigger>
                <TabsTrigger value="performance">Performance</TabsTrigger>
            </TabsList>

            <!-- Supervisor Decisions -->
            <TabsContent value="decisions">
                <Card>
                    <CardHeader>
                        <CardTitle class="text-base">Supervisor Decision History</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div v-if="!supervisorDecisions.length" class="text-center py-4 text-muted-foreground">
                            No supervisor decisions recorded yet
                        </div>
                        <div v-else class="space-y-3">
                            <div v-for="(decision, index) in supervisorDecisions" :key="index" 
                                 class="decision-item p-3 border rounded-lg">
                                <div class="flex items-start gap-3">
                                    <Brain class="h-5 w-5 text-purple-600 mt-0.5" />
                                    <div class="flex-1">
                                        <div class="flex items-center gap-2 mb-2">
                                            <Badge variant="outline" class="text-xs">
                                                {{ decision.decision_type }}
                                            </Badge>
                                            <Badge variant="outline" class="text-xs">
                                                Confidence: {{ Math.round(decision.confidence * 100) }}%
                                            </Badge>
                                            <span class="text-xs text-muted-foreground">
                                                {{ decision.timestamp }}
                                            </span>
                                        </div>
                                        <div class="text-sm mb-2">{{ decision.reasoning }}</div>
                                        <div v-if="decision.target_agent" class="text-sm text-muted-foreground">
                                            → Routing to: <strong>{{ getAgentDisplayName(decision.target_agent) }}</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>

            <!-- Agent Handoffs -->
            <TabsContent value="handoffs">
                <Card>
                    <CardHeader>
                        <CardTitle class="text-base">Agent Handoff Timeline</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div v-if="!agentHandoffs.length" class="text-center py-4 text-muted-foreground">
                            No agent handoffs recorded yet
                        </div>
                        <div v-else class="space-y-3">
                            <div v-for="(handoff, index) in agentHandoffs" :key="index" 
                                 class="handoff-item p-3 border rounded-lg">
                                <div class="flex items-center justify-between mb-2">
                                    <div class="flex items-center gap-2">
                                        <Users class="h-4 w-4 text-blue-600" />
                                        <span class="text-sm font-medium">
                                            {{ getAgentDisplayName(handoff.source_agent) }}
                                        </span>
                                        <ArrowRight class="h-3 w-3 text-muted-foreground" />
                                        <span class="text-sm font-medium">
                                            {{ getAgentDisplayName(handoff.target_agent) }}
                                        </span>
                                    </div>
                                    <span class="text-xs text-muted-foreground">
                                        {{ handoff.timestamp }}
                                    </span>
                                </div>
                                <div class="text-sm text-muted-foreground mb-2">
                                    Reason: {{ handoff.reason }}
                                </div>
                                <div v-if="handoff.context && Object.keys(handoff.context).length" 
                                     class="text-xs bg-muted p-2 rounded">
                                    <div class="font-medium mb-1">Context:</div>
                                    <pre class="text-xs">{{ JSON.stringify(handoff.context, null, 2) }}</pre>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>

            <!-- Retry History -->
            <TabsContent value="retries">
                <Card>
                    <CardHeader>
                        <CardTitle class="text-base">Agent Retry History</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div v-if="!retryHistory.length" class="text-center py-4 text-muted-foreground">
                            No retries recorded
                        </div>
                        <div v-else class="space-y-3">
                            <div v-for="(retry, index) in retryHistory" :key="index" 
                                 class="retry-item p-3 border rounded-lg">
                                <div class="flex items-center gap-2 mb-2">
                                    <RefreshCw class="h-4 w-4 text-orange-600" />
                                    <span class="font-medium">{{ getAgentDisplayName(retry.agent_name) }}</span>
                                    <Badge variant="outline" class="text-xs">
                                        Attempt {{ retry.attempt_number }}/{{ retry.max_retries }}
                                    </Badge>
                                    <Badge variant="outline" class="text-xs">
                                        {{ retry.strategy }}
                                    </Badge>
                                </div>
                                <div class="text-sm text-muted-foreground mb-1">
                                    Reason: {{ retry.reason }}
                                </div>
                                <div v-if="retry.error" class="text-sm text-red-600 bg-red-50 p-2 rounded">
                                    Error: {{ retry.error }}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>

            <!-- Performance Metrics -->
            <TabsContent value="performance">
                <Card>
                    <CardHeader>
                        <CardTitle class="text-base">Performance Metrics</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                            <div class="metric-card p-3 bg-muted rounded-lg text-center">
                                <div class="text-2xl font-bold">{{ totalExecutionTime }}ms</div>
                                <div class="text-xs text-muted-foreground">Total Time</div>
                            </div>
                            <div class="metric-card p-3 bg-muted rounded-lg text-center">
                                <div class="text-2xl font-bold">{{ averageAgentTime }}ms</div>
                                <div class="text-xs text-muted-foreground">Avg Agent Time</div>
                            </div>
                            <div class="metric-card p-3 bg-muted rounded-lg text-center">
                                <div class="text-2xl font-bold">{{ successRate }}%</div>
                                <div class="text-xs text-muted-foreground">Success Rate</div>
                            </div>
                            <div class="metric-card p-3 bg-muted rounded-lg text-center">
                                <div class="text-2xl font-bold">{{ coordinationEfficiency }}%</div>
                                <div class="text-xs text-muted-foreground">Efficiency</div>
                            </div>
                        </div>
                        
                        <!-- Agent Performance Breakdown -->
                        <div class="agent-performance">
                            <h4 class="font-medium mb-3">Agent Performance Breakdown</h4>
                            <div class="space-y-2">
                                <div v-for="agent in agentPerformance" :key="agent.name" 
                                     class="flex items-center gap-3 p-2 bg-muted rounded">
                                    <component :is="getAgentIcon(agent.name)" class="h-4 w-4" />
                                    <span class="flex-1 text-sm">{{ getAgentDisplayName(agent.name) }}</span>
                                    <div class="flex items-center gap-2">
                                        <span class="text-xs text-muted-foreground">{{ agent.avgTime }}ms</span>
                                        <Progress :model-value="agent.performance" class="w-16 h-2" />
                                        <span class="text-xs font-medium">{{ agent.performance }}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>
        </Tabs>

        <!-- Real-time Status -->
        <Card v-if="isExecuting">
            <CardContent class="pt-4">
                <div class="flex items-center gap-3">
                    <Loader2 class="h-5 w-5 animate-spin" />
                    <div class="flex-1">
                        <div class="font-medium">{{ currentAgentStatus }}</div>
                        <div class="text-sm text-muted-foreground">{{ currentAgentTask }}</div>
                    </div>
                    <Button variant="outline" size="sm" @click="showCoordinationLogs">
                        View Logs
                    </Button>
                </div>
            </CardContent>
        </Card>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
    Brain, 
    Users, 
    RefreshCw, 
    ArrowRight, 
    ArrowDown,
    GitBranch,
    Loader2,
    Database,
    Code,
    BarChart,
    Target,
    FileText,
    Bot 
} from 'lucide-vue-next'

interface AgentFlowItem {
    name: string
    status: 'pending' | 'active' | 'complete' | 'error' | 'skipped'
    context?: string
    duration?: number
    startTime?: string
    endTime?: string
}

interface SupervisorDecision {
    decision_type: string
    target_agent?: string
    reasoning: string
    confidence: number
    iteration: number
    timestamp: string
}

interface AgentHandoff {
    source_agent: string
    target_agent: string
    reason: string
    context?: Record<string, any>
    timestamp: string
}

interface RetryAttempt {
    agent_name: string
    attempt_number: number
    max_retries: number
    reason: string
    strategy: string
    error?: string
    timestamp: string
}

interface AgentPerformanceMetric {
    name: string
    avgTime: number
    performance: number
    successRate: number
}

interface Props {
    useSupervisor?: boolean
    currentIteration?: number
    agentFlow?: AgentFlowItem[]
    supervisorDecisions?: SupervisorDecision[]
    agentHandoffs?: AgentHandoff[]
    retryHistory?: RetryAttempt[]
    agentPerformance?: AgentPerformanceMetric[]
    isExecuting?: boolean
    currentAgentStatus?: string
    currentAgentTask?: string
    totalExecutionTime?: number
}

const props = withDefaults(defineProps<Props>(), {
    useSupervisor: true,
    agentFlow: () => [],
    supervisorDecisions: () => [],
    agentHandoffs: () => [],
    retryHistory: () => [],
    agentPerformance: () => [],
    isExecuting: false,
    totalExecutionTime: 0
})

const emit = defineEmits<{
    showLogs: []
}>()

// Computed properties
const totalAgentsInvolved = computed(() => {
    return new Set(props.agentFlow.map(agent => agent.name)).size
})

const averageAgentTime = computed(() => {
    const times = props.agentFlow.filter(a => a.duration).map(a => a.duration!)
    return times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0
})

const successRate = computed(() => {
    const total = props.agentFlow.length
    const successful = props.agentFlow.filter(a => a.status === 'complete').length
    return total ? Math.round((successful / total) * 100) : 0
})

const coordinationEfficiency = computed(() => {
    // Calculate based on handoffs vs direct routing
    const totalSteps = props.agentFlow.length
    const handoffs = props.agentHandoffs.length
    const efficiency = totalSteps > 0 ? Math.max(0, 100 - (handoffs / totalSteps * 50)) : 100
    return Math.round(efficiency)
})

// Helper functions with proper typing
const getModeVariant = (): "default" | "destructive" | "outline" | "secondary" => {
    return props.useSupervisor ? 'default' : 'secondary'
}

const getAgentDisplayName = (agentName: string): string => {
    const displayNames: Record<string, string> = {
        'data_analysis_agent': 'Data Analysis',
        'query_generation_agent': 'Query Generation',
        'result_processing_agent': 'Result Processing',
        'objective_evaluation_agent': 'Objective Evaluation',
        'finalization_agent': 'Answer Formatting'
    }
    return displayNames[agentName] || agentName
}

const getAgentIcon = (agentName: string) => {
    const icons: Record<string, any> = {
        'data_analysis_agent': Database,
        'query_generation_agent': Code,
        'result_processing_agent': BarChart,
        'objective_evaluation_agent': Target,
        'finalization_agent': FileText
    }
    return icons[agentName] || Bot
}

const getAgentStatusClass = (agent: AgentFlowItem): string => {
    const baseClass = 'w-8 h-8 rounded-full flex items-center justify-center'
    const statusClasses = {
        pending: 'bg-gray-200 text-gray-500',
        active: 'bg-blue-500 text-white animate-pulse',
        complete: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        skipped: 'bg-gray-300 text-gray-600'
    }
    return `${baseClass} ${statusClasses[agent.status] || statusClasses.pending}`
}

const getAgentStatusVariant = (status: string): "default" | "destructive" | "outline" | "secondary" => {
    const variants: Record<string, "default" | "destructive" | "outline" | "secondary"> = {
        pending: 'outline',
        active: 'default',
        complete: 'secondary',
        error: 'destructive',
        skipped: 'outline'
    }
    return variants[status] || 'outline'
}

const showCoordinationLogs = () => {
    emit('showLogs')
}
</script>

<style scoped>
.agent-coordination-dashboard {
    @apply space-y-4;
}

.agent-step {
    transition: all 0.3s ease;
}

.decision-item, .handoff-item, .retry-item {
    transition: all 0.2s ease;
}

.decision-item:hover, .handoff-item:hover, .retry-item:hover {
    @apply bg-muted/50;
}

.metric-card {
    transition: transform 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
}

.agent-flow {
    @apply relative;
}

.agent-flow::before {
    content: '';
    @apply absolute left-4 top-8 bottom-0 w-px bg-border;
}

.agent-performance .progress-container {
    @apply flex items-center gap-2;
}
</style> 