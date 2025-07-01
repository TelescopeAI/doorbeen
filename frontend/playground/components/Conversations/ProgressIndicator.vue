<template>
    <div class="execution-progress">
        <!-- NEW: Supervisor Decision Display -->
        <Card v-if="supervisorDecision" class="mb-4 supervisor-card">
            <CardHeader>
                <div class="flex items-center gap-2">
                    <Brain class="h-5 w-5 text-purple-600" />
                    <Badge variant="secondary" class="bg-purple-100 text-purple-800">
                        Supervisor Decision
                    </Badge>
                    <span class="text-sm font-medium">{{ supervisorDecision.reasoning }}</span>
                </div>
            </CardHeader>
            <CardContent v-if="supervisorDecision.target_agent">
                <div class="flex items-center gap-2">
                    <ArrowRight class="h-4 w-4 text-purple-600" />
                    <span class="text-sm">Routing to: <strong>{{ getAgentDisplayName(supervisorDecision.target_agent) }}</strong></span>
                    <Badge variant="outline" class="text-xs">
                        Confidence: {{ Math.round(supervisorDecision.confidence * 100) }}%
                    </Badge>
                    <Badge variant="outline" class="text-xs">
                        Iteration: {{ supervisorDecision.iteration }}
                    </Badge>
                </div>
            </CardContent>
        </Card>

        <!-- NEW: Agent Handoff Visualization -->
        <Card v-if="currentHandoff" class="mb-4 handoff-card">
            <CardContent class="pt-4">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <Users class="h-4 w-4 text-blue-600" />
                        <span class="text-sm">{{ getAgentDisplayName(currentHandoff.source_agent) }}</span>
                    </div>
                    <ArrowRight class="h-4 w-4 text-gray-400" />
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-medium">{{ getAgentDisplayName(currentHandoff.target_agent) }}</span>
                        <Badge variant="outline" class="text-xs">{{ currentHandoff.reason }}</Badge>
                    </div>
                </div>
            </CardContent>
        </Card>

        <!-- ENHANCED: Agent Progress Display -->
        <Card v-if="agentProgress" class="mb-4 agent-progress-card">
            <CardHeader>
                <div class="flex items-center gap-2">
                    <component :is="getAgentIcon(agentProgress.agent_name)" class="h-5 w-5" />
                    <Badge :variant="getProgressVariant(agentProgress.status)">
                        {{ getAgentDisplayName(agentProgress.agent_name) }}
                    </Badge>
                    <span class="text-sm">{{ getProgressMessage(agentProgress) }}</span>
                </div>
                <!-- Familiar Node Progress Bar for User Recognition -->
                <div class="mt-2">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-xs text-muted-foreground">
                            Progress: {{ agentProgress.familiar_node_name }}
                        </span>
                        <span class="text-xs font-medium">{{ agentProgress.progress_percentage }}%</span>
                    </div>
                    <Progress :model-value="agentProgress.progress_percentage" class="h-2" />
                </div>
            </CardHeader>
        </Card>

        <!-- NEW: Enhanced Objective Tracking -->
        <Card v-if="objectiveStatus" class="mb-4 objectives-card">
            <CardHeader>
                <div class="flex items-center gap-2">
                    <Target class="h-5 w-5 text-green-600" />
                    <span class="text-sm font-medium">Objective Progress</span>
                    <Badge variant="outline">
                        {{ objectiveStatus.completed.length }}/{{ objectiveStatus.identified.length }} Complete
                    </Badge>
                    <Badge :variant="getObjectiveVariant(objectiveStatus.overall_status)">
                        {{ objectiveStatus.overall_status }}
                    </Badge>
                </div>
            </CardHeader>
            <CardContent>
                <div class="space-y-2">
                    <!-- Completed Objectives -->
                    <div v-for="objective in objectiveStatus.completed" :key="objective" 
                         class="flex items-center gap-2">
                        <CheckCircle class="h-4 w-4 text-green-600" />
                        <span class="text-sm">{{ objective }}</span>
                    </div>
                    <!-- Remaining Objectives -->
                    <div v-for="objective in objectiveStatus.remaining" :key="objective" 
                         class="flex items-center gap-2">
                        <Clock class="h-4 w-4 text-yellow-600" />
                        <span class="text-sm text-muted-foreground">{{ objective }}</span>
                    </div>
                </div>
                <div class="mt-3">
                    <Progress :model-value="(objectiveStatus.completed.length / objectiveStatus.identified.length) * 100" 
                              class="h-2" />
                    <div class="text-xs text-center mt-1 text-muted-foreground">
                        Confidence: {{ Math.round(objectiveStatus.completion_confidence * 100) }}%
                    </div>
                </div>
            </CardContent>
        </Card>

        <!-- NEW: Agent Retry Information -->
        <Alert v-if="agentRetryInfo" class="mb-4" :variant="getRetryAlertVariant(agentRetryInfo)">
            <RefreshCw class="h-4 w-4" />
            <AlertDescription>
                <div class="flex items-center justify-between">
                    <span>
                        {{ getAgentDisplayName(agentRetryInfo.agent_name) }} 
                        retrying ({{ agentRetryInfo.retry_count }}/{{ agentRetryInfo.max_retries }})
                        {{ agentRetryInfo.strategy ? `using ${agentRetryInfo.strategy}` : '' }}
                    </span>
                    <Badge variant="outline" class="text-xs">
                        {{ agentRetryInfo.reason }}
                    </Badge>
                </div>
            </AlertDescription>
        </Alert>

        <!-- EXISTING: Data Exploration with Agent Context Enhancement -->
        <Card v-if="explorationInProgress" class="mb-4 exploration-card">
            <CardHeader>
                <div class="flex items-center gap-2">
                    <Loader2 class="h-5 w-5 animate-spin" />
                    <Badge variant="secondary">Data Analysis Agent</Badge>
                    <span class="text-sm font-medium">Exploring database to understand available data</span>
                </div>
                <!-- NEW: Agent Context Display -->
                <div v-if="currentAgentContext" class="mt-2 p-2 bg-muted rounded-md">
                    <div class="text-xs text-muted-foreground mb-1">Agent Context:</div>
                    <div class="text-xs">{{ currentAgentContext }}</div>
                </div>
            </CardHeader>
            <CardContent>
                <div class="space-y-3">
                    <!-- Exploration Queries Display -->
                    <div v-if="explorationQueries && explorationQueries.length" class="exploration-queries">
                        <Collapsible class="w-full">
                            <CollapsibleTrigger class="flex items-center justify-between w-full p-3 text-left hover:bg-accent rounded-md">
                                <span class="font-medium">📋 Exploration Queries</span>
                                <ChevronDown class="h-4 w-4" />
                            </CollapsibleTrigger>
                            <CollapsibleContent class="px-3 pb-3">
                            <div class="space-y-3">
                                <div 
                                    v-for="(queryInfo, index) in explorationQueries" 
                                    :key="index"
                                    class="query-item"
                                >
                                    <div class="flex items-start gap-2 mb-2">
                                            <Badge variant="outline" class="text-xs">
                                                {{ index + 1 }}
                                            </Badge>
                                        <div class="flex-1">
                                            <div class="text-sm font-medium mb-1">
                                                {{ queryInfo.objective || 'Database Exploration' }}
                                            </div>
                                            <div class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs font-mono overflow-x-auto mb-2">
                                                {{ queryInfo.query }}
                                            </div>
                                            <div class="flex items-center gap-2">
                                                    <Badge 
                                                    v-if="queryInfo.status === 'success'"
                                                        variant="default" 
                                                    class="bg-green-100 text-green-800 text-xs"
                                                    >
                                                        ✅ {{ queryInfo.rowCount || 0 }} rows
                                                    </Badge>
                                                    <Badge 
                                                    v-else-if="queryInfo.status === 'failed'"
                                                        variant="destructive" 
                                                        class="text-xs"
                                                    >
                                                        ❌ Failed
                                                    </Badge>
                                                    <Badge 
                                                    v-else
                                                        variant="secondary" 
                                                        class="text-xs"
                                                    >
                                                        ⏳ Running
                                                    </Badge>
                                                <span v-if="queryInfo.explanation" class="text-xs text-gray-500">
                                                    {{ queryInfo.explanation }}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            </CollapsibleContent>
                        </Collapsible>
                    </div>

                    <div v-if="explorationFindings" class="findings-preview">
                        <Collapsible class="w-full">
                            <CollapsibleTrigger class="flex items-center justify-between w-full p-3 text-left hover:bg-accent rounded-md">
                                <span class="font-medium">Discovery Progress</span>
                                <ChevronDown class="h-4 w-4" />
                            </CollapsibleTrigger>
                            <CollapsibleContent class="px-3 pb-3">
                            <div class="text-sm text-gray-700 dark:text-gray-300">
                                {{ explorationFindings.substring(0, 200) }}
                                <span v-if="explorationFindings.length > 200">...</span>
                            </div>
                            </CollapsibleContent>
                        </Collapsible>
                    </div>
                    
                    <div v-if="tablesExplored && tablesExplored.length" class="tables-explored">
                        <div class="flex flex-wrap gap-1">
                            <Badge 
                                v-for="table in tablesExplored" 
                                :key="table" 
                                variant="outline" 
                                class="text-xs"
                            >
                                {{ table }}
                            </Badge>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>

        <!-- Circuit Breaker Warning -->
        <Alert 
            v-if="circuitBreakerStatus?.triggered" 
            :variant="getSeverityVariant"
            class="mb-4"
        >
            <AlertTriangle class="h-4 w-4" />
            <AlertDescription>
            <div class="flex items-center justify-between w-full">
                    <span>{{ getRetryMessage }}</span>
                    <div class="flex gap-2 ml-4">
                    <Button 
                        v-if="shouldShowRetryOption" 
                            size="sm" 
                            variant="outline"
                        @click="handleRetry"
                        >
                            <RefreshCw class="h-4 w-4 mr-1" />
                            Retry
                        </Button>
                    <Button 
                        v-if="shouldShowAlternatives" 
                            size="sm" 
                            variant="outline"
                        @click="showAlternatives"
                        >
                            <Lightbulb class="h-4 w-4 mr-1" />
                            Show Alternatives
                        </Button>
                    </div>
                </div>
            </AlertDescription>
        </Alert>

        <!-- Processing Phase Indicator -->
        <div v-if="currentProcessingPhase && !explorationInProgress && !circuitBreakerStatus?.triggered" 
             class="processing-phase mb-4">
            <div class="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <Loader2 class="h-4 w-4 animate-spin" />
                <span class="text-sm text-blue-700 dark:text-blue-300">{{ currentProcessingPhase }}</span>
            </div>
        </div>

        <!-- Query Execution Status -->
        <div v-if="queryExecutionStatus" class="query-status mb-4">
            <Collapsible class="w-full border rounded-lg">
                <CollapsibleTrigger class="flex items-center justify-between w-full p-3 text-left hover:bg-accent">
                    <span class="font-medium">{{ queryExecutionStatus.title }}</span>
                    <ChevronDown class="h-4 w-4" />
                </CollapsibleTrigger>
                <CollapsibleContent class="px-3 pb-3">
                <div class="space-y-2">
                    <div v-if="queryExecutionStatus.query" class="query-display">
                        <div class="text-xs text-gray-500 mb-1">SQL Query:</div>
                        <div class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-sm font-mono overflow-x-auto">
                            {{ queryExecutionStatus.query }}
                        </div>
                    </div>
                    <div v-if="queryExecutionStatus.resultsCount !== undefined" class="results-info">
                            <Badge 
                                :variant="queryExecutionStatus.resultsCount > 0 ? 'default' : 'secondary'"
                            :class="queryExecutionStatus.resultsCount > 0 ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'"
                            >
                                {{ queryExecutionStatus.resultsCount }} records found
                            </Badge>
                    </div>
                    <div v-if="queryExecutionStatus.error" class="error-info">
                            <Alert variant="destructive">
                                <AlertDescription>
                            {{ queryExecutionStatus.error }}
                                </AlertDescription>
                            </Alert>
                        </div>
                    </div>
                </CollapsibleContent>
            </Collapsible>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { 
    Collapsible, 
    CollapsibleContent, 
    CollapsibleTrigger 
} from '@/components/ui/collapsible'
import { 
    Loader2, 
    AlertTriangle, 
    RefreshCw, 
    Lightbulb, 
    ChevronDown,
    Brain,
    Users,
    Target,
    CheckCircle,
    Clock,
    ArrowRight,
    Database,
    Code,
    BarChart,
    FileText,
    Bot 
} from 'lucide-vue-next'

interface Props {
    explorationInProgress?: boolean
    explorationFindings?: string
    tablesExplored?: string[]
    circuitBreakerStatus?: {
        triggered: boolean
        retry_count: number
        max_retries: number
        last_error?: string
    }
    currentProcessingPhase?: string
    queryExecutionStatus?: {
        title: string
        query?: string
        resultsCount?: number
        error?: string
    }
    explorationQueries?: {
        objective?: string
        query: string
        status: string
        rowCount?: number
        explanation?: string
    }[]
    
    supervisorDecision?: {
        decision_type: string
        target_agent?: string
        reasoning: string
        confidence: number
        iteration: number
    }
    currentHandoff?: {
        source_agent: string
        target_agent: string
        reason: string
        context?: Record<string, any>
        timestamp?: string
    }
    agentProgress?: {
        agent_name: string
        progress_percentage: number
        status: 'working' | 'complete' | 'error' | 'handoff'
        familiar_node_name: string
        current_task?: string
    }
    objectiveStatus?: {
        identified: string[]
        completed: string[]
        remaining: string[]
        completion_confidence: number
        overall_status: 'complete' | 'partial' | 'incomplete'
    }
    agentRetryInfo?: {
        agent_name: string
        retry_count: number
        max_retries: number
        reason: string
        strategy?: string
    }
    currentAgentContext?: string
}

const props = withDefaults(defineProps<Props>(), {
    explorationInProgress: false,
    explorationFindings: '',
    tablesExplored: () => [],
    currentProcessingPhase: '',
    explorationQueries: () => []
})

const emit = defineEmits<{
    retry: []
    showAlternatives: []
}>()

const shouldShowRetryOption = computed(() => {
    return props.circuitBreakerStatus?.triggered && 
           props.circuitBreakerStatus.retry_count < props.circuitBreakerStatus.max_retries
})

const shouldShowAlternatives = computed(() => {
    return props.circuitBreakerStatus?.triggered && 
           props.circuitBreakerStatus.retry_count >= props.circuitBreakerStatus.max_retries
})

const getRetryMessage = computed(() => {
    if (!props.circuitBreakerStatus?.triggered) return ''
    
    const { retry_count, max_retries } = props.circuitBreakerStatus
    const remaining = max_retries - retry_count
    return remaining > 0 
        ? `Query failed after ${retry_count} attempt${retry_count > 1 ? 's' : ''}. ${remaining} attempt${remaining > 1 ? 's' : ''} remaining.`
        : `Maximum retry attempts (${max_retries}) reached. Consider alternative approaches.`
})

const getSeverityVariant = computed(() => {
    if (!props.circuitBreakerStatus?.triggered) return 'default'
    
    const { retry_count, max_retries } = props.circuitBreakerStatus
    if (retry_count < max_retries / 2) return 'default'
    if (retry_count < max_retries) return 'destructive'
    return 'destructive'
})

const getAgentDisplayName = (agentName: string): string => {
    const displayNames = {
        'data_analysis_agent': 'Data Analysis',
        'query_generation_agent': 'Query Generation',
        'result_processing_agent': 'Result Processing',
        'objective_evaluation_agent': 'Objective Evaluation',
        'finalization_agent': 'Answer Formatting'
    }
    return displayNames[agentName] || agentName
}

const getAgentIcon = (agentName: string) => {
    const icons = {
        'data_analysis_agent': Database,
        'query_generation_agent': Code,
        'result_processing_agent': BarChart,
        'objective_evaluation_agent': Target,
        'finalization_agent': FileText
    }
    return icons[agentName] || Bot
}

const getProgressVariant = (status: string) => {
    return {
        'working': 'default',
        'complete': 'secondary',
        'error': 'destructive',
        'handoff': 'outline'
    }[status] || 'default'
}

const getObjectiveVariant = (status: string) => {
    return {
        'complete': 'default',
        'partial': 'secondary',
        'incomplete': 'outline'
    }[status] || 'outline'
}

const getProgressMessage = (progress: any): string => {
    const messages = {
        'working': 'Processing...',
        'complete': 'Completed',
        'error': 'Error occurred',
        'handoff': 'Handing off to next agent'
    }
    return messages[progress?.status] || 'Working...'
}

const getRetryAlertVariant = (retryInfo: any) => {
    if (retryInfo.retry_count >= retryInfo.max_retries) {
        return 'destructive'
    }
    return retryInfo.retry_count > retryInfo.max_retries / 2 ? 'default' : 'default'
}

const handleRetry = () => {
    emit('retry')
}

const showAlternatives = () => {
    emit('showAlternatives')
}
</script>

<style scoped>
.supervisor-card {
    border-left: 4px solid rgb(147 51 234); /* purple-600 */
    background: rgb(250 245 255); /* purple-50 */
}

.handoff-card {
    border-left: 4px solid rgb(59 130 246); /* blue-500 */
    background: rgb(239 246 255); /* blue-50 */
}

.objectives-card {
    border-left: 4px solid rgb(34 197 94); /* green-500 */
    background: rgb(240 253 244); /* green-50 */
}

.agent-progress-card {
    background: linear-gradient(to right, rgb(249 250 251), rgb(243 244 246));
}

.exploration-card {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    border: 1px solid #cbd5e1;
}

.dark .exploration-card {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border: 1px solid #475569;
}

.findings-preview {
    max-height: 150px;
    overflow-y: auto;
}

.query-display {
    max-width: 100%;
}

.query-display code {
    word-break: break-all;
}
</style> 