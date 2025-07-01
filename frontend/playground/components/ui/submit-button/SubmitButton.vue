<template>
  <div 
    ref="buttonRef"
    class="relative inline-flex items-center justify-center"
  >
    <Button
      :size="size"
      :variant="variant"
      :disabled="disabled"
      :class="cn(
        'transition-all duration-200 ease-in-out',
        'hover:scale-105 active:scale-95',
        isProcessing && 'cursor-pointer',
        buttonClass
      )"
      @click="handleClick"
    >
      <!-- Loading Spinner - shown when processing -->
      <Loader2 
        v-if="isProcessing && !isHovered" 
        :class="cn('animate-spin', iconSize)"
      />
      
      <!-- Stop Icon - shown when processing and hovered -->
      <StopCircle 
        v-else-if="isProcessing && isHovered" 
        :class="cn('text-red-500 hover:text-red-600', iconSize)"
      />
      
      <!-- Default Icon - shown when not processing -->
      <ArrowUp 
        v-else 
        :class="iconSize"
      />
      
      <!-- Label (optional) -->
      <span v-if="label" class="ml-2">{{ label }}</span>
    </Button>
    
    <!-- Tooltip for abort functionality -->
    <Tooltip v-if="isProcessing && isHovered">
      <TooltipTrigger asChild>
        <div class="absolute inset-0" />
      </TooltipTrigger>
      <TooltipContent>
        <p>Stop processing</p>
      </TooltipContent>
    </Tooltip>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useElementHover } from '@vueuse/core'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Loader2, StopCircle, ArrowUp } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

interface Props {
  isProcessing?: boolean
  disabled?: boolean
  size?: 'default' | 'sm' | 'lg' | 'icon'
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  label?: string
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  isProcessing: false,
  disabled: false,
  size: 'default',
  variant: 'default',
  label: '',
  class: ''
})

const emit = defineEmits<{
  click: []
  abort: []
}>()

const buttonRef = ref<HTMLElement>()
const isHovered = useElementHover(buttonRef)

const buttonClass = computed(() => props.class)

const iconSize = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-4 w-4'
    case 'lg':
      return 'h-6 w-6'
    case 'icon':
      return 'h-4 w-4'
    default:
      return 'h-5 w-5'
  }
})

const handleClick = () => {
  if (props.isProcessing && isHovered.value) {
    // If processing and hovered, this is an abort action
    emit('abort')
  } else if (!props.isProcessing) {
    // If not processing, this is a normal submit action
    emit('click')
  }
  // If processing but not hovered, do nothing (spinner context)
}
</script> 