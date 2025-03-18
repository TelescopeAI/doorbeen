<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Message from 'primevue/message';
import Badge from 'primevue/badge';
import MDRenderer from '../MDRenderer.vue';

const props = defineProps({
  node: {
    type: String,
    required: true
  }
});

const nodeData = ref<any>(null);
const results = ref([]);
const columns = ref([]);

const dataTable =ref(null);

const isSingleResult = computed(() => results.value.length === 1);

const processResults = () => {
  try {
    const parsedNode = JSON.parse(props.node);
    nodeData.value = parsedNode;

    if (parsedNode && parsedNode.results) {
      results.value = [...parsedNode.results];
      
      if (results.value.length > 0) {
        columns.value = Object.keys(results.value[0]).map(key => ({
          field: key,
          header: key
        }));
      }
    }
  } catch (error) {
    console.error('Error parsing node data:', error);
    nodeData.value = null;
    results.value = [];
    columns.value = [];
  }
};

onMounted(processResults);

// Watch for changes in the node prop
watch(() => props.node, processResults);

const exportCSV = () => {
  dataTable.value.exportCSV();
};
</script>

<template>
  <div class="p-4 flex flex-col gap-y-12">
    <div>
      <MDRenderer v-if="nodeData && nodeData.message" :md="nodeData.message" cid="final_message" severity="info" :closable="false" class="mb-10">
      </MDRenderer>
    </div>

    <div>
      <div v-if="isSingleResult" class="flex flex-col gap-4 p-4">
        <div v-for="(value, key) in results[0]" :key="key" class="flex items-center gap-2">
          <p class="font-semibold">{{ key }}:</p>
          <Badge :value="value.toString()" severity="info" />
        </div>
      </div>
      <div v-else-if="results.length > 1" class="max-w-[10vw] md:max-w-screen-lg lg:max-w-screen-xl
                                               xl:max-w-screen-2xl">
        <DataTable
            ref="dataTable"
            :value="results"
            :paginator="true"
            :rows="10"
            :rowsPerPageOptions="[10, 20, 50]"
            scrollable
            scrollHeight="700px"
            highlightOnSelect
            class="p-datatable-sm"
            rowHover
            showGridlines

        >
          <template #header>
            <div class="text-end pb-4">
              <Button icon="pi pi-external-link" label="Export" @click="exportCSV($event)" />
            </div>
          </template>
          <Column
              v-for="col in columns"
              :key="col.field"
              :field="col.field"
              :header="col.header"
              :sortable="true"
              style="min-width: 100px"
          />
        </DataTable>
      </div>
    </div>

  </div>
</template>

<style scoped>
@media screen and (max-width: 960px) {
  ::v-deep(.p-datatable-tbody > tr > td:nth-child(1)) {
    display: none;
  }
}
</style>