<template>
  <Dialog
    :model-value="internalOpen"
    :title="`配置 Headers - ${endpoint?.api_format || ''}`"
    :description="`为 ${endpoint?.base_url || ''} 配置请求 Headers 规则`"
    size="xl"
    :z-index="70"
    @update:model-value="handleDialogUpdate"
  >
    <div class="space-y-4">
      <!-- 规则编辑器 -->
      <HeadersRulesEditor v-model="localRules" />

      <!-- 说明文本 -->
      <div class="text-sm text-muted-foreground">
        <p class="mb-2">
          <strong>提示：</strong>
        </p>
        <ul class="list-disc list-inside space-y-1 text-xs">
          <li><strong>新增</strong>：添加新的请求头（如果已存在则不会覆盖）</li>
          <li><strong>删除</strong>：移除指定的请求头</li>
          <li><strong>重命名</strong>：将请求头名称从旧值改为新值</li>
          <li><strong>替换值</strong>：搜索并替换请求头的值（支持正则表达式）</li>
        </ul>
      </div>
    </div>

    <template #footer>
      <Button variant="outline" @click="handleClose">
        取消
      </Button>
      <Button @click="handleSave" :disabled="saving">
        {{ saving ? '保存中...' : '保存' }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Dialog, Button } from '@/components/ui'
import HeadersRulesEditor from './HeadersRulesEditor.vue'
import { useToast } from '@/composables/useToast'
import { updateEndpoint } from '@/api/endpoints'
import type { ProviderEndpoint } from '@/api/endpoints'

// Headers 规则类型定义
type HeaderRules = {
  add?: Record<string, string>
  remove?: string[]
  replace_name?: Record<string, string>
  replace_value?: Record<string, {
    search: string
    replace: string
    regex: boolean
    case_sensitive?: boolean
  }>
}

const props = defineProps<{
  modelValue: boolean
  endpoint: ProviderEndpoint | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'saved': []
}>()

const { success, error: showError } = useToast()

const saving = ref(false)
const localRules = ref<HeaderRules | null>(null)

const internalOpen = computed(() => props.modelValue)

// 转换 endpoint.headers 到 headers_rules
function convertHeadersToRules(headers: Record<string, string> | any): HeaderRules | null {
  if (!headers) return null

  // 检查是否已经是新格式（包含规则键）
  const ruleKeys = ['add', 'remove', 'replace_name', 'replace_value']
  if (typeof headers === 'object' && Object.keys(headers).some(key => ruleKeys.includes(key))) {
    // 已经是新格式，直接返回
    return headers as unknown as HeaderRules
  }

  // 旧格式：直接的 headers 字典，转换为 add 规则
  return {
    add: { ...headers }
  }
}

// 监听 endpoint 变化，加载 headers
watch(() => props.endpoint, (endpoint) => {
  if (endpoint) {
    localRules.value = convertHeadersToRules(endpoint.headers as any)
  }
}, { immediate: true })

// 保存
async function handleSave() {
  if (!props.endpoint) return

  saving.value = true
  try {
    // 使用 ?? 确保 null 会变成空对象，但空对象 {} 会被保留
    // 这样清空规则时可以正确保存空对象到后端
    await updateEndpoint(props.endpoint.id, {
      headers: localRules.value ?? {},
    })
    success('Headers 配置已保存')
    emit('saved')
    handleClose()
  } catch (error: any) {
    const message =
      error.response?.data?.detail[0]?.msg ||
      error.response?.data?.detail ||
      error.message ||
      "保存失败";
    showError(message, "错误");
  } finally {
    saving.value = false
  }
}

function handleDialogUpdate(value: boolean) {
  emit('update:modelValue', value)
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>
