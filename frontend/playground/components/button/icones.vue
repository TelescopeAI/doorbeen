<script setup lang="ts">
const props = defineProps({
  icon: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: '24'
  },
  aria_label: {
    type: String,
    default: 'Submit'
  }
})

const emit = defineEmits(['click'])

function handleClick() {
  emit('click')
}
</script>

<template>
    <button :aria-label=aria_label @click="handleClick">
      <Icon :name="icon" :size="size"/>
  </button>
</template>

<style scoped>

</style>