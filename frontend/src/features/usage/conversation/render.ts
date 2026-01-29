/**
 * 渲染块类型定义
 * 用于描述对话内容的渲染结构，由通用渲染组件解释执行
 */

// ============================================================
// 渲染块类型
// ============================================================

/** 文本块 */
export interface TextRenderBlock {
  type: 'text'
  content: string
  /** 是否保留空白（pre-wrap） */
  preWrap?: boolean
  /** 额外样式类名 */
  className?: string
}

/** 可折叠块 */
export interface CollapsibleRenderBlock {
  type: 'collapsible'
  /** 折叠标题 */
  title: string
  /** 折叠内容 */
  content: RenderBlock[]
  /** 默认是否展开 */
  defaultOpen?: boolean
  /** 额外样式类名 */
  className?: string
}

/** 代码块 */
export interface CodeRenderBlock {
  type: 'code'
  code: string
  language?: string
  /** 最大高度限制 */
  maxHeight?: number
}

/** 徽章块 */
export interface BadgeRenderBlock {
  type: 'badge'
  label: string
  variant?: 'default' | 'secondary' | 'outline' | 'destructive'
}

/** 图片块 */
export interface ImageRenderBlock {
  type: 'image'
  /** Base64 数据或 URL */
  src?: string
  alt?: string
  mimeType?: string
}

/** 错误块 */
export interface ErrorRenderBlock {
  type: 'error'
  message: string
  code?: string
}

/** 容器块 - 用于包装一组子块 */
export interface ContainerRenderBlock {
  type: 'container'
  children: RenderBlock[]
  /** 额外样式类名 */
  className?: string
  /** 容器头部（可选） */
  header?: RenderBlock[]
}

/** 消息块 - 表示一条完整的对话消息 */
export interface MessageRenderBlock {
  type: 'message'
  /** 角色标识 */
  role: 'user' | 'assistant' | 'system' | 'tool'
  /** 角色显示名称 */
  roleLabel?: string
  /** 消息头部的徽章 */
  badges?: BadgeRenderBlock[]
  /** 消息内容 */
  content: RenderBlock[]
}

/** 工具调用块 */
export interface ToolUseRenderBlock {
  type: 'tool_use'
  toolName: string
  toolId?: string
  input: string
}

/** 工具结果块 */
export interface ToolResultRenderBlock {
  type: 'tool_result'
  content: string
  isError?: boolean
}

/** 分隔符块 */
export interface DividerRenderBlock {
  type: 'divider'
}

/** 标签行块 - 用于显示 key-value 形式的信息 */
export interface LabelRenderBlock {
  type: 'label'
  label: string
  value: string
  /** 值是否使用等宽字体 */
  mono?: boolean
}

// ============================================================
// 联合类型
// ============================================================

/** 所有渲染块类型的联合 */
export type RenderBlock =
  | TextRenderBlock
  | CollapsibleRenderBlock
  | CodeRenderBlock
  | BadgeRenderBlock
  | ImageRenderBlock
  | ErrorRenderBlock
  | ContainerRenderBlock
  | MessageRenderBlock
  | ToolUseRenderBlock
  | ToolResultRenderBlock
  | DividerRenderBlock
  | LabelRenderBlock

// ============================================================
// 渲染结果
// ============================================================

/** 渲染结果 */
export interface RenderResult {
  /** 渲染块列表 */
  blocks: RenderBlock[]
  /** 是否为流式响应 */
  isStream?: boolean
  /** 渲染错误 */
  error?: string
}

// ============================================================
// 工具函数 - 创建渲染块
// ============================================================

export function createTextBlock(content: string, options?: Partial<TextRenderBlock>): TextRenderBlock {
  return { type: 'text', content, preWrap: true, ...options }
}

export function createCollapsibleBlock(
  title: string,
  content: RenderBlock[],
  options?: Partial<CollapsibleRenderBlock>
): CollapsibleRenderBlock {
  return { type: 'collapsible', title, content, defaultOpen: false, ...options }
}

export function createCodeBlock(code: string, language?: string): CodeRenderBlock {
  return { type: 'code', code, language }
}

export function createBadgeBlock(
  label: string,
  variant?: BadgeRenderBlock['variant']
): BadgeRenderBlock {
  return { type: 'badge', label, variant }
}

export function createImageBlock(options: Omit<ImageRenderBlock, 'type'>): ImageRenderBlock {
  return { type: 'image', ...options }
}

export function createErrorBlock(message: string, code?: string): ErrorRenderBlock {
  return { type: 'error', message, code }
}

export function createContainerBlock(
  children: RenderBlock[],
  options?: Partial<ContainerRenderBlock>
): ContainerRenderBlock {
  return { type: 'container', children, ...options }
}

export function createMessageBlock(
  role: MessageRenderBlock['role'],
  content: RenderBlock[],
  options?: Partial<MessageRenderBlock>
): MessageRenderBlock {
  return { type: 'message', role, content, ...options }
}

export function createToolUseBlock(
  toolName: string,
  input: string,
  toolId?: string
): ToolUseRenderBlock {
  return { type: 'tool_use', toolName, input, toolId }
}

export function createToolResultBlock(
  content: string,
  isError?: boolean
): ToolResultRenderBlock {
  return { type: 'tool_result', content, isError }
}

export function createDividerBlock(): DividerRenderBlock {
  return { type: 'divider' }
}

export function createLabelBlock(
  label: string,
  value: string,
  mono?: boolean
): LabelRenderBlock {
  return { type: 'label', label, value, mono }
}

/** 创建空的渲染结果 */
export function createEmptyRenderResult(error?: string): RenderResult {
  return { blocks: [], error }
}
