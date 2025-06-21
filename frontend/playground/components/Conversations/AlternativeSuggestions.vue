<template>
    <Card v-if="alternatives?.length || insights?.length" class="alternatives-panel">
        <template #header>
            <div class="flex items-center gap-2 p-3">
                <Lightbulb class="w-4 h-4 text-yellow-500" />
                <h4 class="m-0 font-semibold">{{ title }}</h4>
                <Badge :value="alternatives?.length || 0" variant="secondary" />
            </div>
        </template>
        
        <template #content>
            <div class="space-y-4">
                <!-- Insights Section -->
                <div v-if="insights?.length" class="insights-section">
                    <div class="flex items-center gap-2 mb-3">
                        <Info class="w-4 h-4 text-blue-500" />
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Analysis Insights</span>
                    </div>
                    <div class="space-y-2">
                        <Alert 
                            v-for="(insight, index) in insights" 
                            :key="index"
                            class="mb-2"
                        >
                            <Info class="h-4 w-4" />
                            <AlertDescription class="text-sm">{{ insight }}</AlertDescription>
                        </Alert>
                    </div>
                </div>

                <!-- Alternative Suggestions -->
                <div v-if="alternatives?.length" class="alternatives-section">
                    <div class="flex items-center gap-2 mb-3">
                        <ArrowRight class="w-4 h-4 text-green-500" />
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Suggested Alternatives</span>
                    </div>
                    
                    <div class="space-y-3">
                        <Card 
                            v-for="(suggestion, index) in alternatives" 
                            :key="index"
                            class="suggestion-item border border-gray-200 dark:border-gray-700"
                        >
                            <template #content>
                                <div class="flex items-start justify-between gap-3">
                                    <div class="flex-1">
                                        <div class="flex items-start gap-2">
                                            <ChevronRight class="w-3 h-3 text-gray-400 mt-1" />
                                            <span class="text-sm text-gray-700 dark:text-gray-300">{{ suggestion }}</span>
                                        </div>
                                    </div>
                                    <div class="flex gap-2">
                                        <Button 
                                            variant="outline"
                                            size="sm"
                                            @click="tryAlternative(suggestion, index)"
                                        >
                                            <Play class="w-4 h-4 mr-2" />
                                            Try This
                                        </Button>
                                        <Button 
                                            variant="outline"
                                            size="sm"
                                            @click="copySuggestion(suggestion)"
                                        >
                                            <Copy class="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </template>
                        </Card>
                    </div>
                </div>

                <!-- Next Steps -->
                <div v-if="nextSteps" class="next-steps-section">
                    <div class="flex items-center gap-2 mb-3">
                        <ArrowRight class="w-4 h-4 text-purple-500" />
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Recommended Next Steps</span>
                    </div>
                    <Alert variant="default">
                        <Info class="h-4 w-4" />
                        <AlertDescription class="text-sm">{{ nextSteps }}</AlertDescription>
                    </Alert>
                </div>

                <!-- Unmet Objectives -->
                <div v-if="unmetObjectives?.length" class="unmet-objectives-section">
                    <div class="flex items-center gap-2 mb-3">
                        <AlertCircle class="w-4 h-4 text-orange-500" />
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Unmet Objectives</span>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <Badge 
                            v-for="objective in unmetObjectives" 
                            :key="objective" 
                            variant="destructive"
                            class="text-xs"
                        >
                            {{ objective }}
                        </Badge>
                    </div>
                </div>

                <!-- Action Buttons -->
                <Separator />
                <div class="flex gap-2 justify-end">
                    <Button 
                        variant="outline"
                        @click="startFresh"
                    >
                        <RefreshCw class="w-4 h-4 mr-2" />
                        Start Fresh
                    </Button>
                    <Button 
                        variant="outline"
                        @click="modifyQuery"
                    >
                        <Pencil class="w-4 h-4 mr-2" />
                        Modify Query
                    </Button>
                    <Button 
                        v-if="!hasTriedDataExploration" 
                        @click="exploreData"
                    >
                        <Search class="w-4 h-4 mr-2" />
                        Explore Data
                    </Button>
                </div>
            </div>
        </template>
    </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useClipboard } from '@vueuse/core'
import { useToast } from '~/components/ui/toast/use-toast'
import { Card, CardContent, CardHeader } from '~/components/ui/card'
import { Badge } from '~/components/ui/badge'
import { Alert, AlertDescription } from '~/components/ui/alert'
import { Button } from '~/components/ui/button'
import { Separator } from '~/components/ui/separator'
import { 
    Lightbulb, 
    Info, 
    ArrowRight, 
    ChevronRight, 
    Play, 
    Copy, 
    AlertCircle, 
    RefreshCw, 
    Pencil, 
    Search 
} from 'lucide-vue-next'

interface Props {
    alternatives?: string[]
    insights?: string[]
    nextSteps?: string
    unmetObjectives?: string[]
    hasTriedDataExploration?: boolean
    title?: string
}

const props = withDefaults(defineProps<Props>(), {
    alternatives: () => [],
    insights: () => [],
    nextSteps: '',
    unmetObjectives: () => [],
    hasTriedDataExploration: false,
    title: 'Alternative Approaches'
})

const emit = defineEmits<{
    tryAlternative: [suggestion: string, index: number]
    startFresh: []
    modifyQuery: []
    exploreData: []
}>()

const { toast } = useToast()
const { copy } = useClipboard()

const tryAlternative = (suggestion: string, index: number) => {
    emit('tryAlternative', suggestion, index)
    toast({
        title: 'Trying Alternative',
        description: 'Attempting the suggested approach...',
    })
}

const copySuggestion = async (suggestion: string) => {
    try {
        await copy(suggestion)
        toast({
            title: 'Copied',
            description: 'Suggestion copied to clipboard',
        })
    } catch (error) {
        toast({
            title: 'Copy Failed',
            description: 'Could not copy to clipboard',
            variant: 'destructive',
        })
    }
}

const startFresh = () => {
    emit('startFresh')
}

const modifyQuery = () => {
    emit('modifyQuery')
}

const exploreData = () => {
    emit('exploreData')
}
</script>

<style scoped>
.alternatives-panel {
    background: linear-gradient(135deg, #fefefe 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
}

.dark .alternatives-panel {
    background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
    border: 1px solid #4a5568;
}

.suggestion-item {
    transition: all 0.2s ease;
}

.suggestion-item:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.dark .suggestion-item:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.insights-section,
.alternatives-section,
.next-steps-section,
.unmet-objectives-section {
    border-left: 3px solid transparent;
    padding-left: 12px;
}

.insights-section {
    border-left-color: #3b82f6;
}

.alternatives-section {
    border-left-color: #10b981;
}

.next-steps-section {
    border-left-color: #8b5cf6;
}

.unmet-objectives-section {
    border-left-color: #f59e0b;
}
</style> 