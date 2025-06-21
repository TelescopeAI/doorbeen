<script setup lang="ts">

import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '~/components/ui/select';
import { Skeleton } from '~/components/ui/skeleton';
import { toValue } from '@vueuse/core'

const table = ref(null)
const table_columns = ref([])
const table_rows = ref([])
const expanded_table_mode = ref(false)
let tables = ref([])
const selected_table = ref("")
const data_table_ref = ref()




const props = defineProps({
  data: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

let sample_data: any = reactive(props.data)
const isLoadingData = ref(props.loading)


watch(() => props.loading, (val) => {
  isLoadingData.value = val
})

watch(() => props.data, (val) => {
  if(val !== null){
    sample_data = val
    const contains_data = Object.keys(sample_data).length > 0
    if (!props.loading && contains_data) {
      init_sample_data();
    }
  }
})

function init_sample_data() {
  tables.value = sample_data.tables.map((name: string) => ({ name, code: name }));
  selected_table.value = tables.value[0]?.name || "";
  if (selected_table.value) {
    update_table_data(selected_table.value);
  }
}

function update_table_data(table_name: string) {
  const dataset = toValue(sample_data.data)
  const table_data = dataset.find((table: any) => Object.keys(table).includes(table_name))
  table.value = table_data
  const table_obj: any = Object.values(table_data)[0]
  table_columns.value = table_obj.columns
  table_rows.value = table_obj.rows
}

const exportCSV = () => {
  data_table_ref.value.exportCSV();
};

const handleTableChange = (value: string) => {
  selected_table.value = value;
  update_table_data(value);
};

</script>

<template>
<div>
  <div v-if="isLoadingData"class="flex flex-col gap-y-4">
    <Skeleton class="h-20 w-full" />
    <div class="grid grid-rows-5 grid-cols-4 gap-x-4 gap-y-3">
      <Skeleton v-for="(n, i) in 20" :key="i" class="h-5 w-full" />
    </div>
  </div>
  <div v-else>
    <div class="flex flex-col gap-y-6">
      <div>
        <Select v-model="selected_table" @update:model-value="handleTableChange">
          <SelectTrigger class="w-full">
            <SelectValue placeholder="Select a table" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem 
              v-for="table in tables" 
              :key="table.name" 
              :value="table.name"
            >
              {{ table.name }}
            </SelectItem>
          </SelectContent>
        </Select>

      </div>
      <div class="card">
        <div>
          <Dialog v-model:visible="expanded_table_mode" modal :header="selected_table" :style="{ width: '90vw', height:'auto' }">
            <DataTable :value="table_rows" stripedRows paginator sortMode="multiple"
                       :rows="20" :rowsPerPageOptions="[5, 10, 20, 50]" showGridlines
                       tableStyle="min-width: 50rem">
              <Column v-for="column in table_columns" :field="column" :header="column" sortable></Column>
            </DataTable>
          </Dialog>
        </div>
        <DataTable :value="table_rows" ref="data_table_ref" stripedRows paginator sortMode="multiple" size="small"
                   :rows="5" showGridlines
                   tableStyle="min-width: 50rem">
          <template #header>
            <div class="flex justify-end">
              <Button icon="pi pi-download" label="Download" text aria-label="Download CSV"
                      severity="secondary" class="p-1"  @click="exportCSV($event)" />
              <Button @click="expanded_table_mode = true" icon="pi pi-window-maximize" label="Expand" text aria-label="Expand Table"
                      severity="secondary" class="p-1">
              </Button>
            </div>
          </template>

          <Column v-for="column in table_columns" :field="column" :header="column" sortable></Column>
        </DataTable>
      </div>
    </div>
  </div>
</div>
</template>

<style scoped>

</style>