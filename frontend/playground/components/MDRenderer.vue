<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
// import markdownParser from '@nuxt/content/transformers/markdown'

const props = defineProps({
  md: {
    type: String,
    default: '',
  },
  cid: {
    type: String,
    default: '<some-id>',
  },
})

const mk_content = ref(props.md)
const mk_cid = ref(props.cid)
const parsedMarkdown = ref('')

// const parseMarkdown = async () => {
//   parsedMarkdown.value = await markdownParser.parse(mk_cid.value, mk_content.value)
//   await nextTick()
// }

// await parseMarkdown()

watch(() => props.md, async (newMd) => {
  mk_content.value = newMd
  // await parseMarkdown()
}, { deep: true })
</script>

<template>
<!--  <ContentRenderer :value="parsedMarkdown" class="p-3 prose">-->
<!--    <ContentRendererMarkdown :value="parsedMarkdown" tag="article"-->
<!--                             class="flex flex-col gap-y-2 prose whitespace-pre-line-->
<!--                             !prose-table:border-separate !prose-table:border-spacing-8"/>-->
<!--  </ContentRenderer>-->
  <MDC :value="mk_content" tag="article" />

</template>

<style scoped>

</style>