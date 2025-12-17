<template>
  <SelectPortal>
    <SelectContentPrimitive
      v-bind="$attrs"
      :class="contentClass"
      :position="position"
      :side="side"
      :side-offset="sideOffset"
      :align="align"
      :align-offset="alignOffset"
    >
      <SelectViewport :class="viewportClass">
        <slot />
      </SelectViewport>
    </SelectContentPrimitive>
  </SelectPortal>
</template>

<script setup lang="ts">
import {
  SelectContent as SelectContentPrimitive,
  SelectPortal,
  SelectViewport,
} from 'radix-vue'
import { cn } from '@/lib/utils'
import { computed } from 'vue'

interface Props {
  class?: string
  position?: 'item-aligned' | 'popper'
  side?: 'top' | 'right' | 'bottom' | 'left'
  sideOffset?: number
  align?: 'start' | 'center' | 'end'
  alignOffset?: number
}

const props = withDefaults(defineProps<Props>(), {
  class: undefined,
  position: 'popper',
  side: undefined,
  sideOffset: 4,
  align: undefined,
  alignOffset: undefined,
})

const contentClass = computed(() =>
  cn(
    'z-[200] max-h-96 min-w-[8rem] overflow-hidden rounded-2xl border border-border bg-card text-foreground shadow-2xl backdrop-blur-xl pointer-events-auto',
    'data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
    'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
    props.class
  )
)

const viewportClass = 'p-1 max-h-[var(--radix-select-content-available-height)]'
</script>
