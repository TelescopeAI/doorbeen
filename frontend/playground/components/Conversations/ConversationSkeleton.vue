<script setup lang="ts">
import { Skeleton } from '~/components/ui/skeleton'

interface Props {
  count?: number
}

const props = withDefaults(defineProps<Props>(), {
  count: 3
})
</script>

<template>
  <div class="space-y-6">
    <div v-for="i in count" :key="i" class="space-y-4">
      <!-- User Message Skeleton -->
      <div class="flex justify-end">
        <div class="max-w-[80%] space-y-2">
          <Skeleton class="h-4 w-20" />
          <div class="bg-primary/10 rounded-lg p-4 space-y-2">
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-3/4" />
          </div>
        </div>
      </div>

      <!-- Assistant Message Skeleton -->
      <div class="flex justify-start">
        <div class="max-w-[80%] w-full space-y-3">
          <Skeleton class="h-4 w-24" />
          
          <!-- Analysis Steps Card -->
          <div class="border rounded-lg p-4 space-y-4">
            <div class="flex items-center gap-2">
              <Skeleton class="h-4 w-4" />
              <Skeleton class="h-4 w-32" />
            </div>
            
            <!-- Multiple analysis step skeletons -->
            <div class="space-y-3">
              <div v-for="j in 3" :key="j" class="space-y-2">
                <Skeleton class="h-4 w-48" />
                <div class="pl-4 space-y-2">
                  <Skeleton class="h-3 w-full" />
                  <Skeleton class="h-3 w-5/6" />
                  <Skeleton class="h-3 w-4/6" />
                </div>
              </div>
            </div>
            
            <!-- Results section -->
            <div class="space-y-2">
              <Skeleton class="h-4 w-36" />
              <div class="bg-muted/50 rounded p-3 space-y-2">
                <Skeleton class="h-3 w-full" />
                <Skeleton class="h-3 w-4/5" />
                <Skeleton class="h-3 w-3/5" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template> 