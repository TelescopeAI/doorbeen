<script setup lang="ts">
import { Database, Bot, Settings as SettingsIcon } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import DatabaseSelector from '@/components/Database/Selector.vue'
import ModelSelector from '@/components/Model/Selector.vue'

// Settings page setup
definePageMeta({
  title: 'Settings'
})

// Dialog states
const isDatabaseDialogOpen = ref(false)
const isModelDialogOpen = ref(false)

// Configuration states
const dbConfigAvailable = ref(false)
const modelConfigAvailable = ref(false)

// Check for existing configurations on mount
onMounted(() => {
  // Check for existing database configuration
  const storedDbConfig = localStorage.getItem('db-config')
  if (storedDbConfig) {
    try {
      const dbConfig = JSON.parse(storedDbConfig)
      if (dbConfig && Object.keys(dbConfig).length > 0) {
        dbConfigAvailable.value = true
      }
    } catch (error) {
      console.error('Error parsing stored database config:', error)
    }
  }

  // Check for existing model configuration
  const storedModelConfig = localStorage.getItem('model-config')
  if (storedModelConfig) {
    try {
      const modelConfig = JSON.parse(storedModelConfig)
      if (modelConfig && Object.keys(modelConfig).length > 0) {
        modelConfigAvailable.value = true
      }
    } catch (error) {
      console.error('Error parsing stored model config:', error)
    }
  }
})

// Event handlers for database configuration
const handleDBConfigUpdated = (config: any) => {
  console.log('Database config updated:', config)
  dbConfigAvailable.value = true
}

const handleDBConfigAvailableInStorage = (available: boolean) => {
  dbConfigAvailable.value = available
}

const handleSampleModeUpdated = (sampleMode: boolean) => {
  console.log('Sample mode updated:', sampleMode)
}

// Handler to close database dialog after config is saved
const handleDBConfigSaved = () => {
  // Add a small delay to sync with toast appearance
  setTimeout(() => {
    isDatabaseDialogOpen.value = false
  }, 500)
}

// Event handlers for model configuration
const handleModelConfigUpdated = (config: any) => {
  console.log('Model config updated:', config)
  modelConfigAvailable.value = true
}

const handleModelConfigAvailableInStorage = (available: boolean) => {
  modelConfigAvailable.value = available
}

// Handler to close model dialog after config is saved
const handleModelConfigSaved = () => {
  // Add a small delay to sync with toast appearance
  setTimeout(() => {
    isModelDialogOpen.value = false
  }, 500)
}
</script>

<template>
  <div class="max-w-4xl mx-auto py-6 px-4">
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">Settings</h1>
        <p class="text-gray-600 dark:text-gray-400">
          Manage your account settings and preferences.
        </p>
      </div>
      
      <div class="grid gap-6">

        <!-- Database Configuration Card -->
        <Card>
          <CardHeader>
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900">
                <Database class="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <CardTitle>Database Configuration</CardTitle>
                <CardDescription>
                  Configure your database connection settings and credentials.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="space-y-1 text-center flex gap-x-4 items-center justify-start">
                <p class="text-sm font-medium">Status</p>
                <p class="text-sm text-muted-foreground flex gap-x-4 text-center">
                  <span v-if="dbConfigAvailable" class="text-green-600 dark:text-green-400">
                    ✓ Database configured
                  </span>
                  <span v-else class="text-amber-600 dark:text-amber-400">
                    ⚠ Database not configured
                  </span>
                </p>
              </div>
              <Dialog v-model:open="isDatabaseDialogOpen">
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <SettingsIcon class="w-4 h-4 mr-2" />
                    Configure Database
                  </Button>
                </DialogTrigger>
                <DialogContent class="sm:max-w-[600px]">
                  <DialogHeader>
                    <DialogTitle>Database Configuration</DialogTitle>
                    <DialogDescription>
                      Select your database type and configure connection settings.
                    </DialogDescription>
                  </DialogHeader>
                  <div class="py-4">
                    <DatabaseSelector 
                      @DBConfigUpdated="handleDBConfigUpdated"
                      @dbConfigAvailableInStorage="handleDBConfigAvailableInStorage"
                      @sampleModeUpdated="handleSampleModeUpdated"
                      @configSaved="handleDBConfigSaved"
                    />
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </CardContent>
        </Card>

        <!-- Model Configuration Card -->
        <Card>
          <CardHeader>
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900">
                <Bot class="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <CardTitle>Model Configuration</CardTitle>
                <CardDescription>
                  Configure your LLM settings and API credentials.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="space-y-1">
                <p class="text-sm font-medium">Status</p>
                <p class="text-sm text-muted-foreground">
                  <span v-if="modelConfigAvailable" class="text-green-600 dark:text-green-400">
                    ✓ Model configured
                  </span>
                  <span v-else class="text-amber-600 dark:text-amber-400">
                    ⚠ Model not configured
                  </span>
                </p>
              </div>
              <Dialog v-model:open="isModelDialogOpen">
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <SettingsIcon class="w-4 h-4 mr-2" />
                    Configure Model
                  </Button>
                </DialogTrigger>
                <DialogContent class="sm:max-w-[600px]">
                  <DialogHeader>
                    <DialogTitle>AI Model Configuration</DialogTitle>
                    <DialogDescription>
                      Select your AI model provider and configure API settings.
                    </DialogDescription>
                  </DialogHeader>
                  <div class="py-4">
                    <ModelSelector 
                      @modelConfigUpdated="handleModelConfigUpdated"
                      @modelConfigAvailableInStorage="handleModelConfigAvailableInStorage"
                      @configSaved="handleModelConfigSaved"
                    />
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </CardContent>
        </Card>

        
        <!-- Preferences Card -->
        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>
              Configure your application preferences.
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <label class="text-sm font-medium">Dark Mode</label>
                <p class="text-sm text-muted-foreground">
                  Toggle dark mode theme
                </p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template> 