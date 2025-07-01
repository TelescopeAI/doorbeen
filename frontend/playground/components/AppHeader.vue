<script setup lang="ts">
import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar'
import Logo from '@/components/Logo.vue'

// Get sidebar state to show logo when collapsed
const { state, isMobile, openMobile } = useSidebar()
</script>

<template>
  <header class="flex items-center justify-between gap-2 px-8 py-4 border-b">
    <SidebarTrigger />
    <!-- Show logo when sidebar is collapsed or mobile sidebar is closed -->
    <div 
      v-if="(isMobile && !openMobile) || (!isMobile && state === 'collapsed')"
      class="flex items-center gap-2"
    >
      <Logo/>
    </div>
  </header>
</template> 