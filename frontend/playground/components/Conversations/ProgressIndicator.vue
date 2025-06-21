<template>
    <div class="execution-progress">
        <!-- Data Exploration Phase -->
        <Card v-if="explorationInProgress" class="mb-4 exploration-card">
            <CardHeader>
                <div class="flex items-center gap-2">
                    <Loader2 class="h-5 w-5 animate-spin" />
                    <Badge variant="secondary">Exploring</Badge>
                    <span class="text-sm font-medium">Exploring the database to understand the available data</span>
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
    ChevronDown 
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

const handleRetry = () => {
    emit('retry')
}

const showAlternatives = () => {
    emit('showAlternatives')
}
</script>

<style scoped>
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