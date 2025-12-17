<template>
  <Card class="overflow-hidden">
    <!-- 标题头部 -->
    <div class="p-4 border-b border-border/60">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold flex items-center gap-2">
          模型名称映射
        </h3>
        <Button
          variant="outline"
          size="sm"
          class="h-8"
          @click="openAddDialog"
        >
          <Plus class="w-3.5 h-3.5 mr-1.5" />
          添加映射
        </Button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>

    <!-- 分组映射列表 -->
    <div
      v-else-if="aliasGroups.length > 0"
      class="divide-y divide-border/40"
    >
      <div
        v-for="group in aliasGroups"
        :key="`${group.model.id}-${group.apiFormatsKey}`"
        class="transition-colors"
      >
        <!-- 分组头部（可点击展开） -->
        <div
          class="flex items-center justify-between px-4 py-3 hover:bg-muted/20 cursor-pointer"
          @click="toggleAliasGroupExpand(`${group.model.id}-${group.apiFormatsKey}`)"
        >
          <div class="flex items-center gap-2 flex-1 min-w-0">
            <!-- 展开/收起图标 -->
            <ChevronRight
              class="w-4 h-4 text-muted-foreground shrink-0 transition-transform"
              :class="{ 'rotate-90': expandedAliasGroups.has(`${group.model.id}-${group.apiFormatsKey}`) }"
            />
            <!-- 模型名称 -->
            <span class="font-semibold text-sm truncate">
              {{ group.model.global_model_display_name || group.model.provider_model_name }}
            </span>
            <!-- 作用域标签 -->
            <div class="flex items-center gap-1 shrink-0">
              <Badge
                v-if="group.apiFormats.length === 0"
                variant="outline"
                class="text-xs"
              >
                全部
              </Badge>
              <Badge
                v-for="format in group.apiFormats"
                v-else
                :key="format"
                variant="outline"
                class="text-xs"
              >
                {{ API_FORMAT_LABELS[format] || format }}
              </Badge>
            </div>
            <!-- 映射数量 -->
            <span class="text-xs text-muted-foreground shrink-0">
              ({{ group.aliases.length }} 个映射)
            </span>
          </div>
          <!-- 操作按钮 -->
          <div
            class="flex items-center gap-1.5 ml-4 shrink-0"
            @click.stop
          >
            <Button
              variant="ghost"
              size="icon"
              class="h-8 w-8"
              title="编辑映射组"
              @click="editGroup(group)"
            >
              <Edit class="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              class="h-8 w-8 text-destructive hover:text-destructive"
              title="删除映射组"
              @click="deleteGroup(group)"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        <!-- 展开的别名列表 -->
        <div
          v-show="expandedAliasGroups.has(`${group.model.id}-${group.apiFormatsKey}`)"
          class="bg-muted/30 border-t border-border/30"
        >
          <div class="px-4 py-2 space-y-1">
            <div
              v-for="alias in group.aliases"
              :key="alias.name"
              class="flex items-center gap-2 py-1"
            >
              <!-- 优先级标签 -->
              <span class="inline-flex items-center justify-center w-5 h-5 rounded bg-background border text-xs font-medium shrink-0">
                {{ alias.priority }}
              </span>
              <!-- 别名名称 -->
              <span class="font-mono text-sm truncate">
                {{ alias.name }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-else
      class="p-8 text-center text-muted-foreground"
    >
      <Tag class="w-12 h-12 mx-auto mb-3 opacity-50" />
      <p class="text-sm">
        暂无模型映射
      </p>
      <p class="text-xs mt-1">
        点击上方"添加映射"按钮为模型创建名称映射
      </p>
    </div>
  </Card>

  <!-- 添加/编辑映射对话框 -->
  <Dialog
    v-model="dialogOpen"
    :title="editingItem ? '编辑模型映射' : '添加模型映射'"
    :description="editingItem ? '修改映射配置' : '为模型添加新的名称映射'"
    :icon="Tag"
    size="xl"
  >
    <div class="space-y-3">
      <!-- 第一行：目标模型 | 作用域 -->
      <div class="flex gap-4">
        <!-- 目标模型 -->
        <div class="flex-1 space-y-1.5">
          <Label class="text-xs">目标模型</Label>
          <Select
            v-model:open="modelSelectOpen"
            :model-value="formData.modelId"
            :disabled="!!editingItem"
            @update:model-value="formData.modelId = $event"
          >
            <SelectTrigger class="h-9">
              <SelectValue placeholder="请选择模型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="model in models"
                :key="model.id"
                :value="model.id"
              >
                {{ model.global_model_display_name || model.provider_model_name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- 作用域 -->
        <div class="flex-1 space-y-1.5">
          <Label class="text-xs">作用域 <span class="text-muted-foreground font-normal">(不选则适用全部)</span></Label>
          <div
            v-if="providerApiFormats.length > 0"
            class="flex flex-wrap gap-1.5 p-2 rounded-md border bg-muted/30 min-h-[36px]"
          >
            <button
              v-for="format in providerApiFormats"
              :key="format"
              type="button"
              class="px-2.5 py-0.5 rounded text-xs font-medium transition-colors"
              :class="[
                formData.apiFormats.includes(format)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background border border-border hover:bg-muted'
              ]"
              @click="toggleApiFormat(format)"
            >
              {{ API_FORMAT_LABELS[format] || format }}
            </button>
          </div>
          <div
            v-else
            class="h-9 flex items-center text-xs text-muted-foreground"
          >
            无可用格式
          </div>
        </div>
      </div>

      <!-- 第二行：上游模型 | 映射名称 -->
      <div class="flex gap-4 h-[340px]">
        <!-- 左侧：上游模型列表 -->
        <div class="flex-1 flex flex-col border rounded-lg overflow-hidden">
          <!-- 左侧头部：标题 + 搜索 + 操作按钮 -->
          <div class="px-3 py-2 bg-muted/50 border-b flex items-center gap-2 shrink-0">
            <span class="text-xs font-medium shrink-0">上游模型</span>
            <!-- 搜索框 -->
            <div class="flex-1 relative">
              <Search class="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <Input
                v-model="upstreamModelSearch"
                placeholder="搜索模型..."
                class="pl-7 h-7 text-xs"
              />
            </div>
            <!-- 操作按钮 -->
            <button
              v-if="upstreamModelsLoaded"
              class="p-1.5 rounded hover:bg-muted transition-colors shrink-0"
              title="刷新列表"
              :disabled="refreshingUpstreamModels"
              @click="refreshUpstreamModels"
            >
              <RefreshCw
                class="w-3.5 h-3.5"
                :class="{ 'animate-spin': refreshingUpstreamModels }"
              />
            </button>
            <button
              v-else-if="!fetchingUpstreamModels"
              class="p-1.5 rounded hover:bg-muted transition-colors shrink-0"
              title="获取上游模型列表"
              @click="fetchUpstreamModels"
            >
              <Zap class="w-3.5 h-3.5" />
            </button>
            <Loader2
              v-else
              class="w-3.5 h-3.5 animate-spin text-muted-foreground shrink-0"
            />
          </div>

          <!-- 模型列表 -->
          <div class="flex-1 overflow-y-auto">
            <template v-if="upstreamModelsLoaded">
              <!-- 按分组显示（可折叠） -->
              <div
                v-for="group in groupedAvailableUpstreamModels"
                :key="group.api_format"
              >
                <div
                  class="sticky top-0 z-10 px-3 py-1.5 bg-muted/80 backdrop-blur-sm border-b flex items-center justify-between cursor-pointer hover:bg-muted/90 transition-colors"
                  @click="toggleGroupCollapse(group.api_format)"
                >
                  <div class="flex items-center gap-1.5">
                    <ChevronRight
                      class="w-3.5 h-3.5 transition-transform"
                      :class="{ 'rotate-90': !collapsedGroups.has(group.api_format) }"
                    />
                    <span class="text-xs font-medium">{{ API_FORMAT_LABELS[group.api_format] || group.api_format }}</span>
                    <span class="text-xs text-muted-foreground">({{ group.models.length }})</span>
                  </div>
                  <button
                    class="text-xs text-primary hover:underline"
                    @click.stop="addAllFromGroup(group.api_format)"
                  >
                    全部添加
                  </button>
                </div>
                <div v-show="!collapsedGroups.has(group.api_format)">
                  <div
                    v-for="model in group.models"
                    :key="model.id"
                    class="group flex items-center gap-2 px-3 py-1.5 hover:bg-muted/50 cursor-pointer transition-colors"
                    :title="model.id"
                    @click="addUpstreamModel(model.id)"
                  >
                    <div class="flex-1 min-w-0">
                      <div class="font-mono text-xs truncate">
                        {{ model.id }}
                      </div>
                      <div
                        v-if="model.owned_by"
                        class="text-xs text-muted-foreground truncate"
                      >
                        {{ model.owned_by }}
                      </div>
                    </div>
                    <Plus class="w-3.5 h-3.5 text-muted-foreground/50 group-hover:text-primary transition-colors shrink-0" />
                  </div>
                </div>
              </div>

              <!-- 空状态 -->
              <div
                v-if="groupedAvailableUpstreamModels.length === 0"
                class="flex items-center justify-center h-full text-muted-foreground text-xs p-4"
              >
                {{ upstreamModelSearch ? '没有匹配的模型' : '所有模型已添加' }}
              </div>
            </template>

            <!-- 未加载状态 -->
            <div
              v-else
              class="flex flex-col items-center justify-center h-full text-muted-foreground p-4"
            >
              <Zap class="w-8 h-8 mb-2 opacity-30" />
              <p class="text-xs text-center">
                点击右上角按钮<br>从上游获取可用模型
              </p>
            </div>
          </div>
        </div>

        <!-- 右侧：映射模型（编辑模式下全宽） -->
        <div class="flex-1 flex flex-col border rounded-lg overflow-hidden">
          <div class="px-3 py-2 bg-primary/5 border-b flex items-center justify-between shrink-0">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium">映射名称</span>
              <Badge
                v-if="formData.aliases.length > 0"
                variant="secondary"
                class="text-xs h-5"
              >
                {{ formData.aliases.length }}
              </Badge>
            </div>
            <div class="flex items-center gap-1">
              <button
                v-if="formData.aliases.length > 0"
                class="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-destructive transition-colors"
                title="清空"
                @click="formData.aliases = []"
              >
                <Eraser class="w-3.5 h-3.5" />
              </button>
              <button
                class="p-1.5 rounded hover:bg-muted transition-colors"
                title="手动添加"
                @click="addAliasItem"
              >
                <Plus class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- 已选列表 -->
          <div class="flex-1 overflow-y-auto">
            <div
              v-if="formData.aliases.length > 0"
              class="divide-y divide-border/30"
            >
              <div
                v-for="(alias, index) in formData.aliases"
                :key="`alias-${index}`"
                class="group flex items-center gap-1.5 px-2 py-1.5 hover:bg-muted/30 transition-colors"
                :class="[
                  draggedIndex === index ? 'bg-primary/5' : '',
                  dragOverIndex === index ? 'bg-primary/10' : ''
                ]"
                draggable="true"
                @dragstart="handleDragStart(index, $event)"
                @dragend="handleDragEnd"
                @dragover.prevent="handleDragOver(index)"
                @dragleave="handleDragLeave"
                @drop="handleDrop(index)"
              >
                <!-- 拖拽手柄 -->
                <div class="cursor-grab active:cursor-grabbing text-muted-foreground/30 group-hover:text-muted-foreground shrink-0">
                  <GripVertical class="w-3 h-3" />
                </div>

                <!-- 优先级 -->
                <div class="shrink-0">
                  <input
                    v-if="editingPriorityIndex === index"
                    type="number"
                    min="1"
                    :value="alias.priority"
                    class="w-6 h-5 rounded bg-background border border-primary text-xs text-center focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    autofocus
                    @blur="finishEditPriority(index, $event)"
                    @keydown.enter="($event.target as HTMLInputElement).blur()"
                    @keydown.escape="cancelEditPriority"
                  >
                  <div
                    v-else
                    class="w-5 h-5 rounded bg-muted/50 flex items-center justify-center text-xs text-muted-foreground cursor-pointer hover:bg-primary/10 hover:text-primary"
                    title="点击编辑优先级"
                    @click.stop="startEditPriority(index)"
                  >
                    {{ alias.priority }}
                  </div>
                </div>

                <!-- 名称输入 -->
                <Input
                  v-model="alias.name"
                  placeholder="映射名称"
                  class="flex-1 h-6 text-xs px-2"
                />

                <!-- 删除按钮 -->
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="shrink-0 text-muted-foreground hover:text-destructive h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                  @click="removeAliasItem(index)"
                >
                  <X class="w-3 h-3" />
                </Button>
              </div>
            </div>

            <!-- 空状态 -->
            <div
              v-else
              class="flex flex-col items-center justify-center h-full text-muted-foreground p-4"
            >
              <Tag class="w-8 h-8 mb-2 opacity-30" />
              <p class="text-xs text-center">
                从左侧选择模型<br>或手动添加映射
              </p>
            </div>
          </div>

          <!-- 拖拽提示 -->
          <div
            v-if="formData.aliases.length > 1"
            class="px-3 py-1.5 bg-muted/30 border-t text-xs text-muted-foreground text-center shrink-0"
          >
            拖拽调整优先级顺序
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <Button
        variant="outline"
        @click="dialogOpen = false"
      >
        取消
      </Button>
      <Button
        :disabled="submitting || !formData.modelId || formData.aliases.length === 0 || !hasValidAliases"
        @click="handleSubmit"
      >
        <Loader2
          v-if="submitting"
          class="w-4 h-4 mr-2 animate-spin"
        />
        {{ editingItem ? '保存' : '添加' }}
      </Button>
    </template>
  </Dialog>

  <!-- 删除确认对话框 -->
  <AlertDialog
    v-model="deleteConfirmOpen"
    title="删除映射组"
    :description="deleteConfirmDescription"
    confirm-text="删除"
    cancel-text="取消"
    type="danger"
    @confirm="confirmDelete"
    @cancel="deleteConfirmOpen = false"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Tag, Plus, Edit, Trash2, Loader2, GripVertical, X, Zap, Search, RefreshCw, ChevronRight, Eraser } from 'lucide-vue-next'
import {
  Card,
  Button,
  Badge,
  Input,
  Label,
  Dialog,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui'
import AlertDialog from '@/components/common/AlertDialog.vue'
import { useToast } from '@/composables/useToast'
import {
  getProviderModels,
  API_FORMAT_LABELS,
  type Model,
  type ProviderModelAlias
} from '@/api/endpoints'
import { updateModel } from '@/api/endpoints/models'
import { adminApi } from '@/api/admin'

interface AliasItem {
  model: Model
  alias: ProviderModelAlias
}

interface FormAlias {
  name: string
  priority: number
}

const props = defineProps<{
  provider: any
}>()

const emit = defineEmits<{
  'refresh': []
}>()

const { error: showError, success: showSuccess } = useToast()

// 状态
const loading = ref(false)
const models = ref<Model[]>([])
const dialogOpen = ref(false)
const deleteConfirmOpen = ref(false)
const submitting = ref(false)
const editingItem = ref<AliasItem | null>(null)
const deletingGroup = ref<AliasGroup | null>(null)
const modelSelectOpen = ref(false)

// 拖拽状态
const draggedIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// 优先级编辑状态
const editingPriorityIndex = ref<number | null>(null)

// 快速添加（上游模型）状态
const fetchingUpstreamModels = ref(false)
const refreshingUpstreamModels = ref(false)
const upstreamModelsLoaded = ref(false)
const upstreamModels = ref<Array<{ id: string; owned_by?: string; api_format?: string }>>([])
const upstreamModelSearch = ref('')

// 分组折叠状态（上游模型列表）
const collapsedGroups = ref<Set<string>>(new Set())

// 列表展开状态（映射组列表）
const expandedAliasGroups = ref<Set<string>>(new Set())

// 上游模型缓存（按 Provider ID）
const upstreamModelsCache = ref<Map<string, {
  models: Array<{ id: string; owned_by?: string; api_format?: string }>
  timestamp: number
}>>(new Map())
const CACHE_TTL = 5 * 60 * 1000 // 5 分钟缓存

// 过滤和排序后的上游模型列表
const filteredUpstreamModels = computed(() => {
  const searchText = upstreamModelSearch.value.toLowerCase().trim()
  let result = [...upstreamModels.value]

  // 按名称排序
  result.sort((a, b) => a.id.localeCompare(b.id))

  // 搜索过滤（支持空格分隔的多关键词 AND 搜索）
  if (searchText) {
    const keywords = searchText.split(/\s+/).filter(k => k.length > 0)
    result = result.filter(m => {
      const searchableText = `${m.id} ${m.owned_by || ''} ${m.api_format || ''}`.toLowerCase()
      return keywords.every(keyword => searchableText.includes(keyword))
    })
  }

  return result
})

// 按 API 格式分组的上游模型列表
interface UpstreamModelGroup {
  api_format: string
  models: Array<{ id: string; owned_by?: string; api_format?: string }>
}

// 可添加的上游模型（排除已添加的）按分组显示
const groupedAvailableUpstreamModels = computed<UpstreamModelGroup[]>(() => {
  // 获取已添加的映射名称集合
  const addedNames = new Set(formData.value.aliases.map(a => a.name.trim()))

  // 过滤掉已添加的模型
  const availableModels = filteredUpstreamModels.value.filter(m => !addedNames.has(m.id))

  // 按 API 格式分组
  const groups = new Map<string, UpstreamModelGroup>()

  for (const model of availableModels) {
    const format = model.api_format || 'UNKNOWN'
    if (!groups.has(format)) {
      groups.set(format, { api_format: format, models: [] })
    }
    groups.get(format)!.models.push(model)
  }

  // 按 API_FORMAT_LABELS 的键顺序排序
  const order = Object.keys(API_FORMAT_LABELS)
  return Array.from(groups.values()).sort((a, b) => {
    const aIndex = order.indexOf(a.api_format)
    const bIndex = order.indexOf(b.api_format)
    // 未知格式排最后
    if (aIndex === -1 && bIndex === -1) return a.api_format.localeCompare(b.api_format)
    if (aIndex === -1) return 1
    if (bIndex === -1) return -1
    return aIndex - bIndex
  })
})

// 表单数据
const formData = ref<{
  modelId: string
  apiFormats: string[]
  aliases: FormAlias[]
}>({
  modelId: '',
  apiFormats: [],
  aliases: []
})

// 检查是否有有效的别名
const hasValidAliases = computed(() => {
  return formData.value.aliases.some(a => a.name.trim())
})

// 获取 Provider 支持的 API 格式（按 API_FORMATS 定义的顺序排序）
const providerApiFormats = computed(() => {
  const formats = props.provider?.api_formats
  if (Array.isArray(formats) && formats.length > 0) {
    // 按 API_FORMAT_LABELS 中的键顺序排序
    const order = Object.keys(API_FORMAT_LABELS)
    return [...formats].sort((a, b) => order.indexOf(a) - order.indexOf(b))
  }
  return []
})

// 分组数据结构
interface AliasGroup {
  model: Model
  apiFormatsKey: string  // 作用域的唯一标识（排序后的格式数组 JSON）
  apiFormats: string[]   // 作用域
  aliases: ProviderModelAlias[]  // 该组的所有映射
}

// 生成作用域唯一键
function getApiFormatsKey(formats: string[] | undefined): string {
  if (!formats || formats.length === 0) return ''
  return [...formats].sort().join(',')
}

// 按"模型+作用域"分组的映射列表
const aliasGroups = computed<AliasGroup[]>(() => {
  const groups: AliasGroup[] = []
  const groupMap = new Map<string, AliasGroup>()

  for (const model of models.value) {
    if (!model.provider_model_aliases || !Array.isArray(model.provider_model_aliases)) continue

    for (const alias of model.provider_model_aliases) {
      const apiFormatsKey = getApiFormatsKey(alias.api_formats)
      const groupKey = `${model.id}|${apiFormatsKey}`

      if (!groupMap.has(groupKey)) {
        const group: AliasGroup = {
          model,
          apiFormatsKey,
          apiFormats: alias.api_formats || [],
          aliases: []
        }
        groupMap.set(groupKey, group)
        groups.push(group)
      }
      groupMap.get(groupKey)!.aliases.push(alias)
    }
  }

  // 对每个组内的别名按优先级排序
  for (const group of groups) {
    group.aliases.sort((a, b) => a.priority - b.priority)
  }

  // 按模型名排序，同模型内按作用域排序
  return groups.sort((a, b) => {
    const nameA = (a.model.global_model_display_name || a.model.provider_model_name || '').toLowerCase()
    const nameB = (b.model.global_model_display_name || b.model.provider_model_name || '').toLowerCase()
    if (nameA !== nameB) return nameA.localeCompare(nameB)
    return a.apiFormatsKey.localeCompare(b.apiFormatsKey)
  })
})

// 当前编辑的分组
const editingGroup = ref<AliasGroup | null>(null)

// 加载模型
async function loadModels() {
  try {
    loading.value = true
    models.value = await getProviderModels(props.provider.id)
  } catch (err: any) {
    showError(err.response?.data?.detail || '加载失败', '错误')
  } finally {
    loading.value = false
  }
}

// 删除确认描述
const deleteConfirmDescription = computed(() => {
  if (!deletingGroup.value) return ''
  const { model, aliases, apiFormats } = deletingGroup.value
  const modelName = model.global_model_display_name || model.provider_model_name
  const scopeText = apiFormats.length === 0 ? '全部' : apiFormats.map(f => API_FORMAT_LABELS[f] || f).join(', ')
  const aliasNames = aliases.map(a => a.name).join(', ')
  return `确定要删除模型「${modelName}」在作用域「${scopeText}」下的 ${aliases.length} 个映射吗？\n\n映射名称：${aliasNames}`
})

// 切换 API 格式
function toggleApiFormat(format: string) {
  const index = formData.value.apiFormats.indexOf(format)
  if (index >= 0) {
    formData.value.apiFormats.splice(index, 1)
  } else {
    formData.value.apiFormats.push(format)
  }
}

// 切换分组折叠状态（上游模型列表）
function toggleGroupCollapse(apiFormat: string) {
  if (collapsedGroups.value.has(apiFormat)) {
    collapsedGroups.value.delete(apiFormat)
  } else {
    collapsedGroups.value.add(apiFormat)
  }
}

// 切换映射组展开状态
function toggleAliasGroupExpand(groupKey: string) {
  if (expandedAliasGroups.value.has(groupKey)) {
    expandedAliasGroups.value.delete(groupKey)
  } else {
    expandedAliasGroups.value.add(groupKey)
  }
}

// 添加别名项
function addAliasItem() {
  const maxPriority = formData.value.aliases.length > 0
    ? Math.max(...formData.value.aliases.map(a => a.priority))
    : 0
  formData.value.aliases.push({ name: '', priority: maxPriority + 1 })
}

// 删除别名项
function removeAliasItem(index: number) {
  formData.value.aliases.splice(index, 1)
}

// ===== 拖拽排序 =====
function handleDragStart(index: number, event: DragEvent) {
  draggedIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleDragEnd() {
  draggedIndex.value = null
  dragOverIndex.value = null
}

function handleDragOver(index: number) {
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    dragOverIndex.value = index
  }
}

function handleDragLeave() {
  dragOverIndex.value = null
}

function handleDrop(targetIndex: number) {
  const dragIndex = draggedIndex.value
  if (dragIndex === null || dragIndex === targetIndex) {
    dragOverIndex.value = null
    return
  }

  const items = [...formData.value.aliases]
  const draggedItem = items[dragIndex]

  // 记录每个别名的原始优先级（在修改前）
  const originalPriorityMap = new Map<number, number>()
  items.forEach((alias, idx) => {
    originalPriorityMap.set(idx, alias.priority)
  })

  // 重排数组
  items.splice(dragIndex, 1)
  items.splice(targetIndex, 0, draggedItem)

  // 按新顺序为每个组分配新的优先级
  // 同组的别名保持相同的优先级（被拖动的别名单独成组）
  const groupNewPriority = new Map<number, number>() // 原优先级 -> 新优先级
  let currentPriority = 1

  items.forEach((alias) => {
    // 找到这个别名在原数组中的索引
    const originalIdx = formData.value.aliases.findIndex(a => a === alias)
    const originalPriority = originalIdx >= 0 ? originalPriorityMap.get(originalIdx)! : alias.priority

    if (alias === draggedItem) {
      // 被拖动的别名是独立的新组，获得当前优先级
      alias.priority = currentPriority
      currentPriority++
    } else {
      if (groupNewPriority.has(originalPriority)) {
        // 这个组已经分配过优先级，使用相同的值
        alias.priority = groupNewPriority.get(originalPriority)!
      } else {
        // 这个组第一次出现，分配新优先级
        groupNewPriority.set(originalPriority, currentPriority)
        alias.priority = currentPriority
        currentPriority++
      }
    }
  })

  formData.value.aliases = items
  draggedIndex.value = null
  dragOverIndex.value = null
}

// ===== 优先级编辑 =====
function startEditPriority(index: number) {
  editingPriorityIndex.value = index
}

function finishEditPriority(index: number, event: FocusEvent) {
  const input = event.target as HTMLInputElement
  const newPriority = parseInt(input.value) || 1
  formData.value.aliases[index].priority = Math.max(1, newPriority)
  editingPriorityIndex.value = null
}

function cancelEditPriority() {
  editingPriorityIndex.value = null
}

// 打开添加对话框
function openAddDialog() {
  editingItem.value = null
  editingGroup.value = null
  formData.value = {
    modelId: '',
    apiFormats: [],
    aliases: []
  }
  // 重置状态
  editingPriorityIndex.value = null
  draggedIndex.value = null
  dragOverIndex.value = null
  // 重置上游模型状态
  upstreamModelsLoaded.value = false
  upstreamModels.value = []
  upstreamModelSearch.value = ''
  dialogOpen.value = true
}

// 编辑分组
function editGroup(group: AliasGroup) {
  editingGroup.value = group
  editingItem.value = { model: group.model, alias: group.aliases[0] } // 保持兼容
  formData.value = {
    modelId: group.model.id,
    apiFormats: [...group.apiFormats],
    aliases: group.aliases.map(a => ({ name: a.name, priority: a.priority }))
  }
  // 重置状态
  editingPriorityIndex.value = null
  draggedIndex.value = null
  dragOverIndex.value = null
  // 重置上游模型状态
  upstreamModelsLoaded.value = false
  upstreamModels.value = []
  upstreamModelSearch.value = ''
  dialogOpen.value = true
}

// 删除分组
function deleteGroup(group: AliasGroup) {
  deletingGroup.value = group
  deleteConfirmOpen.value = true
}

// 确认删除
async function confirmDelete() {
  if (!deletingGroup.value) return

  const { model, aliases, apiFormatsKey } = deletingGroup.value

  try {
    // 从模型的别名列表中移除该分组的所有别名
    const currentAliases = model.provider_model_aliases || []
    const aliasNamesToRemove = new Set(aliases.map(a => a.name))
    const newAliases = currentAliases.filter((a: ProviderModelAlias) => {
      // 只移除同一作用域的别名
      const currentKey = getApiFormatsKey(a.api_formats)
      return !(currentKey === apiFormatsKey && aliasNamesToRemove.has(a.name))
    })

    await updateModel(props.provider.id, model.id, {
      provider_model_aliases: newAliases.length > 0 ? newAliases : null
    })

    showSuccess('映射组已删除')
    deleteConfirmOpen.value = false
    deletingGroup.value = null
    await loadModels()
    emit('refresh')
  } catch (err: any) {
    showError(err.response?.data?.detail || '删除失败', '错误')
  }
}

// 提交表单
async function handleSubmit() {
  if (submitting.value) return
  if (!formData.value.modelId || formData.value.aliases.length === 0) return

  // 过滤有效的别名
  const validAliases = formData.value.aliases.filter(a => a.name.trim())
  if (validAliases.length === 0) {
    showError('请至少添加一个有效的映射名称', '错误')
    return
  }

  submitting.value = true
  try {
    const targetModel = models.value.find(m => m.id === formData.value.modelId)
    if (!targetModel) {
      showError('模型不存在', '错误')
      return
    }

    const currentAliases = targetModel.provider_model_aliases || []
    let newAliases: ProviderModelAlias[]

    // 构建新的别名对象（带作用域）
    const buildAlias = (a: FormAlias): ProviderModelAlias => ({
      name: a.name.trim(),
      priority: a.priority,
      ...(formData.value.apiFormats.length > 0 ? { api_formats: formData.value.apiFormats } : {})
    })

    if (editingGroup.value) {
      // 编辑分组模式：替换该分组的所有别名
      const oldApiFormatsKey = editingGroup.value.apiFormatsKey
      const oldAliasNames = new Set(editingGroup.value.aliases.map(a => a.name))

      // 移除旧分组的所有别名
      const filteredAliases = currentAliases.filter((a: ProviderModelAlias) => {
        const currentKey = getApiFormatsKey(a.api_formats)
        return !(currentKey === oldApiFormatsKey && oldAliasNames.has(a.name))
      })

      // 检查新别名是否与其他分组的别名重复
      const existingNames = new Set(filteredAliases.map((a: ProviderModelAlias) => a.name))
      const duplicates = validAliases.filter(a => existingNames.has(a.name.trim()))
      if (duplicates.length > 0) {
        showError(`以下映射名称已存在：${duplicates.map(d => d.name).join(', ')}`, '错误')
        return
      }

      // 添加新的别名
      newAliases = [
        ...filteredAliases,
        ...validAliases.map(buildAlias)
      ]
    } else {
      // 添加模式：检查是否重复并批量添加
      const existingNames = new Set(currentAliases.map((a: ProviderModelAlias) => a.name))
      const duplicates = validAliases.filter(a => existingNames.has(a.name.trim()))
      if (duplicates.length > 0) {
        showError(`以下映射名称已存在：${duplicates.map(d => d.name).join(', ')}`, '错误')
        return
      }
      newAliases = [
        ...currentAliases,
        ...validAliases.map(buildAlias)
      ]
    }

    await updateModel(props.provider.id, targetModel.id, {
      provider_model_aliases: newAliases
    })

    showSuccess(editingGroup.value ? '映射组已更新' : '映射已添加')
    dialogOpen.value = false
    editingGroup.value = null
    editingItem.value = null
    await loadModels()
    emit('refresh')
  } catch (err: any) {
    showError(err.response?.data?.detail || '操作失败', '错误')
  } finally {
    submitting.value = false
  }
}

// 监听 provider 变化
watch(() => props.provider?.id, (newId) => {
  if (newId) {
    loadModels()
  }
}, { immediate: true })

onMounted(() => {
  if (props.provider?.id) {
    loadModels()
  }
})

// ===== 快速添加（上游模型）=====
async function fetchUpstreamModels() {
  if (!props.provider?.id) return

  const providerId = props.provider.id
  upstreamModelSearch.value = ''

  // 检查缓存
  const cached = upstreamModelsCache.value.get(providerId)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    upstreamModels.value = cached.models
    upstreamModelsLoaded.value = true
    return
  }

  fetchingUpstreamModels.value = true
  upstreamModels.value = []

  try {
    const response = await adminApi.queryProviderModels(providerId)
    if (response.success && response.data?.models) {
      upstreamModels.value = response.data.models
      // 写入缓存
      upstreamModelsCache.value.set(providerId, {
        models: response.data.models,
        timestamp: Date.now()
      })
      upstreamModelsLoaded.value = true
    } else {
      showError(response.data?.error || '获取模型列表失败', '错误')
    }
  } catch (err: any) {
    showError(err.response?.data?.detail || '获取模型列表失败', '错误')
  } finally {
    fetchingUpstreamModels.value = false
  }
}

// 添加单个上游模型
function addUpstreamModel(modelId: string) {
  // 检查是否已存在
  if (formData.value.aliases.some(a => a.name === modelId)) {
    return
  }

  const maxPriority = formData.value.aliases.length > 0
    ? Math.max(...formData.value.aliases.map(a => a.priority))
    : 0

  formData.value.aliases.push({ name: modelId, priority: maxPriority + 1 })
}

// 添加某个分组的所有模型
function addAllFromGroup(apiFormat: string) {
  const group = groupedAvailableUpstreamModels.value.find(g => g.api_format === apiFormat)
  if (!group) return

  let maxPriority = formData.value.aliases.length > 0
    ? Math.max(...formData.value.aliases.map(a => a.priority))
    : 0

  for (const model of group.models) {
    // 检查是否已存在
    if (!formData.value.aliases.some(a => a.name === model.id)) {
      maxPriority++
      formData.value.aliases.push({ name: model.id, priority: maxPriority })
    }
  }
}

// 刷新上游模型列表（清除缓存并重新获取）
async function refreshUpstreamModels() {
  if (!props.provider?.id || refreshingUpstreamModels.value) return

  const providerId = props.provider.id
  refreshingUpstreamModels.value = true

  // 清除缓存
  upstreamModelsCache.value.delete(providerId)

  try {
    const response = await adminApi.queryProviderModels(providerId)
    if (response.success && response.data?.models) {
      upstreamModels.value = response.data.models
      // 写入缓存
      upstreamModelsCache.value.set(providerId, {
        models: response.data.models,
        timestamp: Date.now()
      })
    } else {
      showError(response.data?.error || '刷新失败', '错误')
    }
  } catch (err: any) {
    showError(err.response?.data?.detail || '刷新失败', '错误')
  } finally {
    refreshingUpstreamModels.value = false
  }
}
</script>
