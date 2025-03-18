<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { getDefaultConfig } from "~/composables/default_config";
import {get_sample_data} from "~/composables/sample_data";

type databaseOption = {
  label: string;
  value: string;
  icon: string;
}
const databases = reactive([
  // {label: 'BigQuery', value: 'bigquery', icon: 'devicon:googlecloud'},
  {label: 'PostgreSQL', value: 'postgresql', icon: 'devicon:postgresql'},
  {label: 'MySQL', value: 'mysql', icon: "devicon:mysql"},
  // {label: 'Oracle', value: 'oracle', icon: 'devicon:oracle'},
  // {label: 'SQL Server', value: 'sqlserver', icon: 'devicon:microsoftsqlserver'},
]);
const isLoadingSampleData = ref(false)

const props = defineProps({
  sample_mode: {
    type: Boolean,
    default: false
  },
})
const emit = defineEmits(['DBConfigUpdated', 'sampleModeUpdated', 'dbConfigAvailableInStorage'])
const use_sample_data = ref(false)


const db_toggle = ref(null)
const { width } = useElementSize(db_toggle)
const isMobileMode = computed(() => width.value < 650)

let sample_data: any = ref({})
watch(use_sample_data, async (value) => {
  emit('sampleModeUpdated', value)
  if (value === true && Object.keys(sample_data.value).length === 0) {
    await load_sample_data()
  }
})




const db_options = databases.map(db => { return {label: db.label, value: db.value} })

const getIconForDatabase = (label: string) => {
  return databases.find(db => db.label === label).icon
}

const stored_db_credentials = useStorage('db-config', {});

if (Object.keys(stored_db_credentials.value).length > 0) {
  emit('dbConfigAvailableInStorage', true)
}

const selected_db_type = ref(stored_db_credentials.value.db_type)
const db_defaults = getDefaultConfig(selected_db_type.value)

// Initialize db_creds from localStorage or set to default for selected_db_type

let db_creds = reactive(stored_db_credentials.value || db_defaults);
emit('DBConfigUpdated', db_creds)

selected_db_type.value = db_creds.db_type
// Watch for changes in selected_db_type to update db_creds with default credentials
watch(selected_db_type, (newValue) => {
  const default_config = getDefaultConfig(newValue);
  db_creds = default_config
  console.log("Stored DB Creds: ", stored_db_credentials.value)
  console.log("DB Creds: ", db_creds)
});

const isBigQuery = computed(() => selected_db_type.value === 'bigquery')
const db_form = ref(null)
const save_db_credentials = () => {
  const node = db_form?.value.node
  node.submit()
}
const db_form_submit_handler = async (formData: Object) => {
  emit('DBConfigUpdated', formData)
  stored_db_credentials.value = formData
  console.log("Form Submitted ", formData)
}

async function load_sample_data(){
  isLoadingSampleData.value = true
  console.log("Is SMP Data Loading: ", isLoadingSampleData.value)
  sample_data.value = await get_sample_data()
  isLoadingSampleData.value = false
  console.log("Is SMP Data Loading Post Request: ", isLoadingSampleData.value)
}

</script>

<template>
  <div class="w-full flex flex-col gap-y-6">
    <div class="flex gap-x-4 items-center hidden">
      <p class="select-none font-semibold tracking-wide text-gray-600">Sample Data</p>
      <InputSwitch v-model="use_sample_data" />
    </div>

    <div v-if="!use_sample_data" class="w-full">
      <FormKit
          id="db_config_form"
          type="form"
          ref="db_form"
          submit-label="Save"
          outer-class="flex"
          :submit-attrs="{
                      outerClass: 'flex flex-row',
                      wrapperClass: 'flex justify-center',
                      ignore: false
                }"
          @submit="db_form_submit_handler"
          :actions="false"
      >


        <FormKit
            type="togglebuttons"
            name="db_type"
            ref="db_toggle"
            :options="db_options"
            wrapper-class="w-full"
            outer-class="max-w-full"
            options-class="w-full wrap"
            singleToggle-class="bg-slate-50"
            :value="selected_db_type"
            v-model="selected_db_type"
            :vertical = "isMobileMode"
        >
          <template #default="context">
            <div class="flex gap-x-3 justify-center items-center w-full text-nowrap">
              <div class="p-2 rounded-full bg-white border shadow-sm">
                <Icon :name="getIconForDatabase(context.option.label)" size="24" />
              </div>
              {{ context.option.label }}
            </div>
          </template>
        </FormKit>
        <CredentialsBigQuery v-if="isBigQuery" />
        <CredentialsCommonSQL v-else :host="db_creds.host" :port="db_creds.port"
                                :username="db_creds.username" :password="db_creds.password"
                                :database="db_creds.database"
        />
      </FormKit>
      <FormKit type="button" @click="save_db_credentials">Update</FormKit>
    </div>
    <div v-else>
      <SampleDatabaseContainer :data="sample_data" :loading="isLoadingSampleData"/>
    </div>

  </div>

</template>

<style scoped>

</style>