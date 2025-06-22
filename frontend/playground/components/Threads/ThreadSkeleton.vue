<script setup lang="ts">
import { Skeleton } from '~/components/ui/skeleton'
import {
  SidebarMenuItem,
  SidebarMenuButton,
} from '~/components/ui/sidebar'

interface Props {
  count?: number
}

const props = withDefaults(defineProps<Props>(), {
  count: 3
})
</script>

<template>
  <div class="space-y-1">
    <SidebarMenuItem v-for="i in count" :key="i">
      <SidebarMenuButton class="w-full justify-start h-auto min-h-[3rem] px-3 py-2.5 gap-3 cursor-default">
        <Skeleton class="h-4 w-4 flex-shrink-0" />
        <div class="flex-1 min-w-0 space-y-1.5">
          <Skeleton class="h-4 w-full" />
          <Skeleton class="h-3 w-16" />
        </div>
      </SidebarMenuButton>
    </SidebarMenuItem>
  </div>
</template> 