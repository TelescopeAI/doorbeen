import { ref, computed, readonly } from 'vue'
import type { ConversationMessage } from '~/types/conversations'

export interface CircuitBreakerStatus {
    triggered: boolean;
    retry_count: number;
    max_retries: number;
    last_error?: string;
}

export const useCircuitBreaker = () => {
    const circuitBreakerStatus = ref<CircuitBreakerStatus>({
        triggered: false,
        retry_count: 0,
        max_retries: 3,
        last_error: undefined
    });

    const updateCircuitBreakerStatus = (status: Partial<CircuitBreakerStatus>) => {
        circuitBreakerStatus.value = {
            ...circuitBreakerStatus.value,
            ...status
        };
    };

    const resetCircuitBreaker = () => {
        circuitBreakerStatus.value = {
            triggered: false,
            retry_count: 0,
            max_retries: 3,
            last_error: undefined
        };
    };

    const shouldShowRetryOption = computed(() => {
        return circuitBreakerStatus.value.triggered && 
               circuitBreakerStatus.value.retry_count < circuitBreakerStatus.value.max_retries;
    });

    const shouldShowAlternatives = computed(() => {
        return circuitBreakerStatus.value.triggered && 
               circuitBreakerStatus.value.retry_count >= circuitBreakerStatus.value.max_retries;
    });

    const getRetryMessage = computed(() => {
        const { retry_count, max_retries } = circuitBreakerStatus.value;
        const remaining = max_retries - retry_count;
        return remaining > 0 
            ? `Query failed. ${remaining} attempt${remaining > 1 ? 's' : ''} remaining.`
            : 'Maximum retry attempts reached. Consider alternative approaches.';
    });

    const getSeverityLevel = computed(() => {
        const { triggered, retry_count, max_retries } = circuitBreakerStatus.value;
        if (!triggered) return 'success';
        if (retry_count < max_retries / 2) return 'warn';
        if (retry_count < max_retries) return 'error';
        return 'contrast';
    });

    const updateFromMessage = (message: ConversationMessage) => {
        if (message.circuit_breaker_status) {
            updateCircuitBreakerStatus(message.circuit_breaker_status);
        }
    };

    return {
        circuitBreakerStatus: readonly(circuitBreakerStatus),
        updateCircuitBreakerStatus,
        resetCircuitBreaker,
        shouldShowRetryOption,
        shouldShowAlternatives,
        getRetryMessage,
        getSeverityLevel,
        updateFromMessage
    };
}; 