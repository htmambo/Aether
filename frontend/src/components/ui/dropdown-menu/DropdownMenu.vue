<script setup lang="ts">
import { DropdownMenuRoot } from 'radix-vue'

interface Props {
  defaultOpen?: boolean
  open?: boolean
  modal?: boolean
}

withDefaults(defineProps<Props>(), {
  modal: true
})

defineEmits<{
  'update:open': [value: boolean]
}>()
</script>

<template>
  <DropdownMenuRoot
    :default-open="defaultOpen"
    :open="open"
    :modal="modal"
    @update:open="$emit('update:open', $event)"
  >
    <slot />
  </DropdownMenuRoot>
</template>
