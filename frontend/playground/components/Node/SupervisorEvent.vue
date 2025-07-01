<script setup lang="ts">
import { computed } from 'vue';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { Bot, User } from 'lucide-vue-next';

const props = defineProps({
  node: {
    type: Object,
    default: () => ({})
  }
});

const eventData = computed(() => {
    if (typeof props.node === 'string') {
    try {
      // It might be a stringified JSON array of messages
      const parsed = JSON.parse(props.node);
      if (Array.isArray(parsed)) {
        return parsed;
    }
    } catch (e) {
      // Not a valid JSON string, treat as raw text
    }
    // If it's just a string, wrap it in a structure for display
    return [{ role: 'assistant', content: props.node }];
  }
  // If it's already an object/array
  return props.node;
});

const getRole = (message: any) => {
  if (!message || typeof message !== 'object') return 'assistant';
  const role = message.role || (message.message ? message.message.role : 'assistant');
  // Normalize roles
  if (role === 'developer' || role === 'supervisor') {
    return 'assistant';
  }
  return role;
}

const getContent = (message: any) => {
   if (!message) return '';
   if (typeof message === 'string') return message;
   return message.content || (message.message ? message.message.content : '');
}

</script>

<template>
  <Card class="bg-gray-50/50 border-gray-200 shadow-sm">
      <CardHeader>
      <CardTitle class="text-base text-gray-700">Supervisor Decision</CardTitle>
    </CardHeader>
    <CardContent class="space-y-4 text-sm">
      <div 
        v-for="(message, index) in eventData" 
        :key="index"
        class="flex items-start gap-3 p-3 rounded-lg"
        :class="{
          'bg-blue-50 border border-blue-100': getRole(message) === 'user',
          'bg-white': getRole(message) === 'assistant'
        }"
      >
        <div class="flex-shrink-0">
          <User v-if="getRole(message) === 'user'" class="w-5 h-5 text-blue-600" />
          <Bot v-else class="w-5 h-5 text-indigo-600" />
        </div>
        <div class="flex-grow">
          <p class="font-semibold text-gray-800 capitalize">{{ getRole(message) }}</p>
          <pre class="whitespace-pre-wrap font-sans text-gray-600">{{ getContent(message) }}</pre>
        </div>
        </div>
      </CardContent>
    </Card>
</template>