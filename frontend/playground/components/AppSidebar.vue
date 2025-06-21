<script setup lang="ts">
import { Settings, Home, Briefcase } from "lucide-vue-next"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import Logo from "@/components/Logo.vue"
import AuthManageUser from "@/components/Auth/ManageUser.vue"

// Menu items
const items = [
  {
    title: "Playground",
    url: "/",
    icon: Home,
  },
  {
    title: "Settings",
    url: "/settings",
    icon: Settings,
  },
  {
    title: "Enhanced Working",
    url: "/enhanced-working",
    icon: Briefcase,
  }
  
]
</script>

<template>
  <Sidebar>
    <!-- Sidebar Header with Logo -->
    <SidebarHeader>
      <div class="px-2 py-2">
        <Logo />
      </div>
    </SidebarHeader>

    <!-- Sidebar Content with Navigation -->
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="item in items" :key="item.title">
              <SidebarMenuButton asChild>
                <NuxtLink :to="item.url">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </NuxtLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <!-- Sidebar Footer with User Authentication -->
    <SidebarFooter>
      <div class="px-2 py-2">
        <ClientOnly>
          <AuthManageUser />
        </ClientOnly>
      </div>
    </SidebarFooter>
  </Sidebar>
</template> 