<script setup lang="ts">
import type { ProxyNode } from '@/api/proxy-nodes'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui'
import { Cpu } from 'lucide-vue-next'

defineProps<{ node: ProxyNode }>()

function formatMemory(mb: number | null) {
  if (mb == null) return '-'
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
  return `${mb} MB`
}

function formatNumber(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}
</script>

<template>
  <TooltipProvider v-if="!node.is_manual && node.hardware_info">
    <Tooltip>
      <TooltipTrigger as-child>
        <Cpu class="h-3.5 w-3.5 text-muted-foreground cursor-default" />
      </TooltipTrigger>
      <TooltipContent
        side="right"
        class="text-xs space-y-0.5"
      >
        <div v-if="node.hardware_info.cpu_cores">
          CPU: {{ node.hardware_info.cpu_cores }} cores
        </div>
        <div v-if="node.hardware_info.total_memory_mb">
          RAM: {{ formatMemory(node.hardware_info.total_memory_mb) }}
        </div>
        <div v-if="node.hardware_info.os_info">
          OS: {{ node.hardware_info.os_info }}
        </div>
        <div v-if="node.estimated_max_concurrency">
          Max Concurrency: ~{{ formatNumber(node.estimated_max_concurrency) }}
        </div>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>
