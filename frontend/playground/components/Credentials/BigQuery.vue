<script setup lang="ts">

const props = defineProps({
  "project_id": {
    type: String,
    default: ""
  },
  "dataset_id": {
    type: String,
    default: ""
  },
  "service_account_json": {
    type: String,
    default: ""
  }
})
</script>

<template>
  <FormKit
      label="Project ID"
      type="text"
      help="What's the unique ID for the project?"
      :value="project_id"
  />
  <FormKit
      label="Dataset ID"
      type="text"
      help="Which dataset would you like to use by default?"
      :value="dataset_id"
  />

  <FormKit
      label="Service Account Details"
      type="textarea"
      help="Credentails JSON Config"
      :value="service_account_json"
  />

</template>

<style scoped>

</style>