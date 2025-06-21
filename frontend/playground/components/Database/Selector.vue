<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { getDefaultConfig } from "~/composables/default_config";
import { get_sample_data } from "~/composables/sample_data";
import { toast } from 'vue-sonner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Eye, EyeOff } from 'lucide-vue-next'

type DatabaseOption = {
  label: string;
  value: string;
  icon: string;
}

const databases = reactive<DatabaseOption[]>([
  { label: 'PostgreSQL', value: 'postgresql', icon: 'devicon:postgresql' },
  { label: 'MySQL', value: 'mysql', icon: 'devicon:mysql' },
]);

const isLoadingSampleData = ref(false)
const showPassword = ref(false)

const props = defineProps({
  sample_mode: {
    type: Boolean,
    default: false
  },
})

const emit = defineEmits(['DBConfigUpdated', 'sampleModeUpdated', 'dbConfigAvailableInStorage', 'configSaved'])
const use_sample_data = ref(false)

let sample_data: any = ref({})
watch(use_sample_data, async (value) => {
  emit('sampleModeUpdated', value)
  if (value === true && Object.keys(sample_data.value).length === 0) {
    await load_sample_data()
  }
})

interface DbCredentials {
  db_type?: string;
  host?: string;
  port?: string | number;
  username?: string;
  password?: string;
  database?: string;
}

const stored_db_credentials = useStorage<DbCredentials>('db-config', {});

if (Object.keys(stored_db_credentials.value).length > 0) {
  emit('dbConfigAvailableInStorage', true)
}

const selected_db_type = ref(stored_db_credentials.value.db_type || 'postgresql')
const db_defaults = getDefaultConfig(selected_db_type.value)

// Form data
const formData = reactive({
  db_type: selected_db_type.value,
  host: stored_db_credentials.value.host || db_defaults?.host || 'localhost',
  port: String(stored_db_credentials.value.port || db_defaults?.port || 5432),
  username: stored_db_credentials.value.username || db_defaults?.username || 'root',
  password: stored_db_credentials.value.password || db_defaults?.password || '',
  database: stored_db_credentials.value.database || db_defaults?.database || 'smclean'
})

// Watch for database type changes
watch(selected_db_type, (newValue) => {
  const default_config = getDefaultConfig(newValue);
  if (default_config) {
    formData.db_type = newValue
    formData.host = default_config.host || 'localhost'
    formData.port = String(default_config.port || (newValue === 'postgresql' ? 5432 : 3306))
    formData.username = default_config.username || 'root'
    formData.password = default_config.password || ''
    formData.database = default_config.database || 'smclean'
  }
});

const save_db_credentials = async () => {
  try {
    // Validate required fields
    if (!formData.host || !formData.username || !formData.database) {
      toast.error('Validation Error', {
        description: 'Please fill in all required fields (Host, Username, Database Name).',
      })
      return
    }

    // Update stored credentials
    stored_db_credentials.value = { ...formData }
    emit('DBConfigUpdated', formData)
    
    // Get the database type name for display
    const dbName = databases.find(db => db.value === formData.db_type)?.label || formData.db_type
    
    // Show success toast
    toast.success('Database Configuration Updated', {
      description: `Your ${dbName} database connection has been configured successfully.`,
    })
    
    // Emit configSaved event to trigger dialog close
    emit('configSaved')
  } catch (error) {
    console.error('Error saving database credentials:', error)
    toast.error('Error', {
      description: 'Failed to save database configuration. Please try again.',
    })
  }
}

async function load_sample_data() {
  isLoadingSampleData.value = true
  try {
    sample_data.value = await get_sample_data()
  } catch (error) {
    console.error('Error loading sample data:', error)
    toast.error('Error', {
      description: 'Failed to load sample data.',
    })
  } finally {
    isLoadingSampleData.value = false
  }
}

const getIconForDatabase = (value: string) => {
  return databases.find(db => db.value === value)?.icon || 'devicon:postgresql'
}
</script>

<template>
  <div class="w-full space-y-6">
    <!-- Sample Data Toggle (Hidden for now) -->
    <div class="flex gap-x-4 items-center hidden">
      <p class="select-none font-semibold tracking-wide text-gray-600">Sample Data</p>
      <InputSwitch v-model="use_sample_data" />
    </div>

    <!-- Main Configuration -->
    <div v-if="!use_sample_data" class="w-full">
      <Tabs :default-value="selected_db_type" @update:model-value="selected_db_type = $event">
        <!-- Database Type Selector -->
        <TabsList class="grid w-full grid-cols-2 mb-6">
          <TabsTrigger 
            v-for="db in databases" 
            :key="db.value" 
            :value="db.value"
            class="tab-trigger-custom"
          >
            <div class="flex items-center justify-center gap-2 w-full">
              <Icon :name="db.icon" size="20" />
              <span>{{ db.label }}</span>
            </div>
          </TabsTrigger>
        </TabsList>

        <!-- Database Configuration Forms -->
        <TabsContent 
          v-for="db in databases" 
          :key="db.value" 
          :value="db.value"
          class="space-y-0"
        >
          <Card>
            <CardHeader>
              <CardTitle class="flex items-center gap-2">
                <Icon :name="getIconForDatabase(db.value)" size="24" />
                {{ db.label }} Configuration
              </CardTitle>
              <CardDescription>
                Configure your {{ db.label }} database connection settings.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <!-- 2x3 Grid Layout for Form Fields -->
              <div class="grid grid-cols-2 gap-4">
                <!-- Host -->
                <div class="space-y-2">
                  <Label for="host">Host</Label>
                  <Input
                    id="host"
                    v-model="formData.host"
                    placeholder="localhost"
                    class="w-full"
                  />
                  <p class="text-xs text-muted-foreground">Where is the database located?</p>
                </div>

                                 <!-- Port -->
                 <div class="space-y-2">
                   <Label for="port">Port</Label>
                   <Input
                     id="port"
                     v-model="formData.port"
                     type="number"
                     :placeholder="db.value === 'postgresql' ? '5432' : '3306'"
                     class="w-full"
                   />
                   <p class="text-xs text-muted-foreground">
                     Default: {{ db.value === 'postgresql' ? '5432' : '3306' }} for {{ db.label }}
                   </p>
                 </div>

                <!-- Username -->
                <div class="space-y-2">
                  <Label for="username">Username</Label>
                  <Input
                    id="username"
                    v-model="formData.username"
                    placeholder="root"
                    class="w-full"
                  />
                  <p class="text-xs text-muted-foreground">Database username</p>
                </div>

                <!-- Password -->
                <div class="space-y-2">
                  <Label for="password">Password</Label>
                  <div class="relative">
                    <Input
                      id="password"
                      v-model="formData.password"
                      :type="showPassword ? 'text' : 'password'"
                      placeholder="Enter password"
                      class="w-full pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      @click="showPassword = !showPassword"
                    >
                      <Eye v-if="!showPassword" class="h-4 w-4" />
                      <EyeOff v-else class="h-4 w-4" />
                    </Button>
                  </div>
                  <p class="text-xs text-muted-foreground">Database password</p>
                </div>

                <!-- Database Name -->
                <div class="space-y-2 col-span-2">
                  <Label for="database">Database Name</Label>
                  <Input
                    id="database"
                    v-model="formData.database"
                    placeholder="smclean"
                    class="w-full"
                  />
                  <p class="text-xs text-muted-foreground">Name of the database to connect to</p>
                </div>
              </div>

              <!-- Save Button -->
              <div class="flex justify-end pt-6">
                <Button @click="save_db_credentials" class="min-w-24">
                  Update Configuration
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>

    <!-- Sample Data Section -->
    <div v-else>
      <SampleDatabaseContainer :data="sample_data" :loading="isLoadingSampleData" />
    </div>
  </div>
</template>

<style scoped>
/* Clean styling - no density overrides needed */

/* Custom tab trigger styling for perfect alignment */
:deep(.tab-trigger-custom) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0.375rem 0.75rem !important;
}

/* Override the default span wrapper to not interfere with flex layout */
:deep(.tab-trigger-custom span.truncate) {
  display: contents !important;
}

/* Ensure the inner div takes full width and centers content */
:deep(.tab-trigger-custom .flex) {
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
}
</style>