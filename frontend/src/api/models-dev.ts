/**
 * Models.dev API 服务
 * 通过后端代理获取 models.dev 数据（解决跨域问题）
 */

import api from './client'

// 缓存配置
const CACHE_KEY = 'models_dev_cache'
const CACHE_DURATION = 15 * 60 * 1000 // 15 分钟

// Models.dev API 数据结构
export interface ModelsDevCost {
  input?: number
  output?: number
  reasoning?: number
  cache_read?: number
}

export interface ModelsDevLimit {
  context?: number
  output?: number
}

export interface ModelsDevModel {
  id: string
  name: string
  family?: string
  reasoning?: boolean
  tool_call?: boolean
  structured_output?: boolean
  temperature?: boolean
  attachment?: boolean
  knowledge?: string
  release_date?: string
  last_updated?: string
  input?: string[] // 输入模态: text, image, audio, video, pdf
  output?: string[] // 输出模态: text, image, audio
  open_weights?: boolean
  cost?: ModelsDevCost
  limit?: ModelsDevLimit
  deprecated?: boolean
}

export interface ModelsDevProvider {
  id: string
  env?: string[]
  npm?: string
  api?: string
  name: string
  doc?: string
  models: Record<string, ModelsDevModel>
}

export type ModelsDevData = Record<string, ModelsDevProvider>

// 扁平化的模型列表项（用于搜索和选择）
export interface ModelsDevModelItem {
  providerId: string
  providerName: string
  modelId: string
  modelName: string
  family?: string
  inputPrice?: number
  outputPrice?: number
  contextLimit?: number
  outputLimit?: number
  supportsVision?: boolean
  supportsToolCall?: boolean
  supportsReasoning?: boolean
  deprecated?: boolean
  // 用于 display_metadata 的额外字段
  knowledgeCutoff?: string
  releaseDate?: string
  inputModalities?: string[]
  outputModalities?: string[]
}

interface CacheData {
  timestamp: number
  data: ModelsDevData
}

// 内存缓存
let memoryCache: CacheData | null = null

/**
 * 获取 models.dev 数据（带缓存）
 */
export async function getModelsDevData(): Promise<ModelsDevData> {
  // 1. 检查内存缓存
  if (memoryCache && Date.now() - memoryCache.timestamp < CACHE_DURATION) {
    return memoryCache.data
  }

  // 2. 检查 localStorage 缓存
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (cached) {
      const cacheData: CacheData = JSON.parse(cached)
      if (Date.now() - cacheData.timestamp < CACHE_DURATION) {
        memoryCache = cacheData
        return cacheData.data
      }
    }
  } catch {
    // 缓存解析失败，忽略
  }

  // 3. 从后端代理获取新数据
  const response = await api.get<ModelsDevData>('/api/admin/models/external')
  const data = response.data

  // 4. 更新缓存
  const cacheData: CacheData = {
    timestamp: Date.now(),
    data,
  }
  memoryCache = cacheData
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData))
  } catch {
    // localStorage 写入失败，忽略
  }

  return data
}

/**
 * 获取扁平化的模型列表
 */
export async function getModelsDevList(): Promise<ModelsDevModelItem[]> {
  const data = await getModelsDevData()
  const items: ModelsDevModelItem[] = []

  for (const [providerId, provider] of Object.entries(data)) {
    if (!provider.models) continue

    for (const [modelId, model] of Object.entries(provider.models)) {
      items.push({
        providerId,
        providerName: provider.name,
        modelId,
        modelName: model.name || modelId,
        family: model.family,
        inputPrice: model.cost?.input,
        outputPrice: model.cost?.output,
        contextLimit: model.limit?.context,
        outputLimit: model.limit?.output,
        supportsVision: model.input?.includes('image'),
        supportsToolCall: model.tool_call,
        supportsReasoning: model.reasoning,
        deprecated: model.deprecated,
        // display_metadata 相关字段
        knowledgeCutoff: model.knowledge,
        releaseDate: model.release_date,
        inputModalities: model.input,
        outputModalities: model.output,
      })
    }
  }

  // 按 provider 名称和模型名称排序
  items.sort((a, b) => {
    const providerCompare = a.providerName.localeCompare(b.providerName)
    if (providerCompare !== 0) return providerCompare
    return a.modelName.localeCompare(b.modelName)
  })

  return items
}

/**
 * 搜索模型
 */
export async function searchModelsDevModels(
  query: string,
  options?: {
    limit?: number
    excludeDeprecated?: boolean
  }
): Promise<ModelsDevModelItem[]> {
  const allModels = await getModelsDevList()
  const { limit = 50, excludeDeprecated = true } = options || {}

  const queryLower = query.toLowerCase()

  const filtered = allModels.filter((model) => {
    if (excludeDeprecated && model.deprecated) return false

    // 搜索模型 ID、名称、provider 名称、family
    return (
      model.modelId.toLowerCase().includes(queryLower) ||
      model.modelName.toLowerCase().includes(queryLower) ||
      model.providerName.toLowerCase().includes(queryLower) ||
      model.family?.toLowerCase().includes(queryLower)
    )
  })

  // 排序：精确匹配优先
  filtered.sort((a, b) => {
    const aExact =
      a.modelId.toLowerCase() === queryLower ||
      a.modelName.toLowerCase() === queryLower
    const bExact =
      b.modelId.toLowerCase() === queryLower ||
      b.modelName.toLowerCase() === queryLower
    if (aExact && !bExact) return -1
    if (!aExact && bExact) return 1
    return 0
  })

  return filtered.slice(0, limit)
}

/**
 * 获取特定模型详情
 */
export async function getModelsDevModel(
  providerId: string,
  modelId: string
): Promise<ModelsDevModel | null> {
  const data = await getModelsDevData()
  return data[providerId]?.models?.[modelId] || null
}

/**
 * 获取 provider logo URL
 */
export function getProviderLogoUrl(providerId: string): string {
  return `https://models.dev/logos/${providerId}.svg`
}

/**
 * 清除缓存
 */
export function clearModelsDevCache(): void {
  memoryCache = null
  try {
    localStorage.removeItem(CACHE_KEY)
  } catch {
    // 忽略错误
  }
}
