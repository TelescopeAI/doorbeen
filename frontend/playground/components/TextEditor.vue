<script setup lang="ts">
import { Extension } from "@tiptap/core";
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { Placeholder } from "@tiptap/extension-placeholder";


const props = defineProps({
  initial_content: {
    type: String,
    default: ""
  },
  placeholder: {
    type: String,
    default: 'Ask away....'
  }
});

const emit = defineEmits(['contentUpdated', 'contentReady']);
const editor_content = ref(props.initial_content);

const CustomEnterOverride = Extension.create({
  addKeyboardShortcuts() {
    return {
      'Enter': ({ editor }) => {
        console.log("Enter Pressed");
        // Custom behavior for Enter key
        emit('contentReady', editor.getText());
        editor.commands.clearContent()
      },
    };
  },
});

const editor = useEditor({
  content: editor_content.value,
  extensions: [
    StarterKit,
    Placeholder.configure({
      placeholder: props.placeholder,
    }),
    CustomEnterOverride
  ],
  editorProps: {
    attributes: {
      class: 'focus:outline-none',
    },
  },
  onUpdate({ editor }) {
    emit('contentUpdated', editor.getText());
  }
});

// watch(() => props.initial_content, (newVal) => {
//   editor.commands.setContent(newVal);
// });

onBeforeUnmount(() => {
  editor.value?.destroy();
});
</script>

<template>
  <editor-content :editor="editor" class="h-full w-full p-2"/>
</template>

<style scoped>
p.is-editor-empty:first-child::before {
  color: var(--primary-500);
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}

.tiptap p.is-empty::before {
  color: #adb5bd;
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
</style>
