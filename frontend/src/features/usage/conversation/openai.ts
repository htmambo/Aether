/**
 * OpenAI API 格式解析器
 */

import type {
  ApiFormatParser,
  ParsedConversation,
  ParsedMessage,
  ContentBlock,
  MessageRole,
} from './types'
import {
  createEmptyConversation,
  createMessage,
  createTextBlock,
  createToolUseBlock,
  createToolResultBlock,
  createImageBlock,
  isStreamResponse,
} from './types'
import type { RenderResult, RenderBlock, BadgeRenderBlock } from './render'
import {
  createTextBlock as createTextRenderBlock,
  createBadgeBlock,
  createImageBlock as createImageRenderBlock,
  createMessageBlock,
  createToolUseBlock as createToolUseRenderBlock,
  createToolResultBlock as createToolResultRenderBlock,
  createEmptyRenderResult,
} from './render'

/**
 * OpenAI API 格式解析器
 */
export class OpenAIParser implements ApiFormatParser {
  readonly format = 'openai' as const
  readonly displayName = 'OpenAI'

  /**
   * 检测是否为 OpenAI 格式
   */
  detect(requestBody: any, responseBody: any, hint?: string): number {
    // 1. 后端提示优先
    if (hint) {
      const lowerHint = hint.toLowerCase()
      if (lowerHint.includes('openai')) return 100
      if (lowerHint.includes('claude') || lowerHint.includes('gemini')) return 0
    }

    // 2. 检查模型名
    const model = requestBody?.model?.toLowerCase() || ''
    if (model.includes('gpt') || model.includes('o1') || model.includes('o3')) return 95

    // 3. 检查请求体结构
    if (!requestBody?.messages || !Array.isArray(requestBody.messages)) {
      return 0
    }

    // 4. 检查响应体特征
    const respBody = isStreamResponse(responseBody)
      ? responseBody.chunks?.[0]
      : responseBody

    if (respBody) {
      // OpenAI 响应特征: choices 数组
      if (respBody.choices || respBody.object?.includes('chat.completion')) {
        return 90
      }
      // 明确是 Claude 格式
      if (respBody.type === 'message' || respBody.type?.startsWith('content_block')) {
        return 0
      }
    }

    // 5. 检查 OpenAI 特有的请求结构
    // OpenAI 的 system 是在 messages 数组中作为 role: system
    const hasSystemInMessages = requestBody.messages?.some(
      (m: any) => m.role === 'system'
    )
    if (hasSystemInMessages) {
      return 60
    }

    return 0
  }

  /**
   * 解析请求体
   */
  parseRequest(requestBody: any): ParsedConversation {
    if (!requestBody) {
      return createEmptyConversation('openai', '无请求体')
    }

    try {
      const result: ParsedConversation = {
        messages: [],
        isStream: requestBody.stream === true,
        apiFormat: 'openai',
        model: requestBody.model,
      }

      if (Array.isArray(requestBody.messages)) {
        for (const msg of requestBody.messages) {
          // OpenAI 的 system 消息在 messages 数组中
          if (msg.role === 'system') {
            const systemText = typeof msg.content === 'string'
              ? msg.content
              : ''
            result.system = result.system
              ? `${result.system  }\n${  systemText}`
              : systemText
            continue
          }

          const parsedMsg = this.parseMessage(msg)
          if (parsedMsg) {
            result.messages.push(parsedMsg)
          }
        }
      }

      return result
    } catch (e) {
      return createEmptyConversation('openai', `解析失败: ${e}`)
    }
  }

  /**
   * 解析响应体
   */
  parseResponse(responseBody: any): ParsedConversation {
    if (!responseBody) {
      return createEmptyConversation('openai', '无响应体')
    }

    try {
      const result: ParsedConversation = {
        messages: [],
        isStream: false,
        apiFormat: 'openai',
        model: responseBody.model,
      }

      // OpenAI 响应格式: { choices: [{ message: { role, content, tool_calls } }] }
      const message = responseBody.choices?.[0]?.message
      if (message) {
        const contentBlocks: ContentBlock[] = []

        // 文本内容
        if (message.content) {
          contentBlocks.push(createTextBlock(message.content))
        }

        // 工具调用
        if (message.tool_calls) {
          for (const call of message.tool_calls) {
            contentBlocks.push(createToolUseBlock(
              call.id || '',
              call.function?.name || '',
              call.function?.arguments || '{}'
            ))
          }
        }

        if (contentBlocks.length > 0) {
          result.messages.push(createMessage('assistant', contentBlocks))
        }
      }

      return result
    } catch (e) {
      return createEmptyConversation('openai', `解析失败: ${e}`)
    }
  }

  /**
   * 解析流式响应
   */
  parseStreamResponse(chunks: any[]): ParsedConversation {
    if (!chunks || chunks.length === 0) {
      return createEmptyConversation('openai', '无响应数据')
    }

    try {
      const result: ParsedConversation = {
        messages: [],
        isStream: true,
        apiFormat: 'openai',
      }

      const textParts: string[] = []
      const toolCalls = new Map<number, { name: string; id: string; args: string[] }>()

      for (const chunk of chunks) {
        // 提取模型名
        if (chunk.model && !result.model) {
          result.model = chunk.model
        }

        const delta = chunk.choices?.[0]?.delta
        if (delta?.content) {
          textParts.push(delta.content)
        }
        if (delta?.tool_calls) {
          for (const call of delta.tool_calls) {
            const index = call.index ?? 0
            if (!toolCalls.has(index)) {
              toolCalls.set(index, {
                name: call.function?.name || '',
                id: call.id || '',
                args: [],
              })
            }
            const existing = toolCalls.get(index)!
            if (call.function?.name) {
              existing.name = call.function.name
            }
            if (call.id) {
              existing.id = call.id
            }
            if (call.function?.arguments) {
              existing.args.push(call.function.arguments)
            }
          }
        }
      }

      const contentBlocks: ContentBlock[] = []

      // 文本内容
      if (textParts.length > 0) {
        contentBlocks.push(createTextBlock(textParts.join('')))
      }

      // 工具调用
      for (const [, call] of toolCalls) {
        contentBlocks.push(createToolUseBlock(
          call.id,
          call.name,
          call.args.join('')
        ))
      }

      if (contentBlocks.length > 0) {
        result.messages.push(createMessage('assistant', contentBlocks))
      }

      return result
    } catch (e) {
      return createEmptyConversation('openai', `解析失败: ${e}`)
    }
  }

  /**
   * 解析单条消息
   */
  private parseMessage(msg: any): ParsedMessage | null {
    if (!msg || !msg.role) return null

    const role = this.mapRole(msg.role)
    const contentBlocks: ContentBlock[] = []

    // 文本内容
    if (typeof msg.content === 'string') {
      contentBlocks.push(createTextBlock(msg.content))
    } else if (Array.isArray(msg.content)) {
      // Vision API 格式
      for (const part of msg.content) {
        if (part.type === 'text') {
          contentBlocks.push(createTextBlock(part.text || ''))
        } else if (part.type === 'image_url') {
          contentBlocks.push(createImageBlock('url', {
            url: part.image_url?.url,
            alt: '[图片]',
          }))
        }
      }
    }

    // 工具调用（assistant 消息）
    if (msg.tool_calls) {
      for (const call of msg.tool_calls) {
        contentBlocks.push(createToolUseBlock(
          call.id || '',
          call.function?.name || '',
          call.function?.arguments || '{}'
        ))
      }
    }

    // 工具结果（tool 消息）
    if (msg.tool_call_id) {
      const content = typeof msg.content === 'string'
        ? msg.content
        : JSON.stringify(msg.content, null, 2)
      contentBlocks.push(createToolResultBlock(
        msg.tool_call_id,
        content
      ))
    }

    if (contentBlocks.length === 0) return null

    return createMessage(role, contentBlocks)
  }

  /**
   * 映射角色
   */
  private mapRole(role: string): MessageRole {
    switch (role) {
      case 'user':
        return 'user'
      case 'assistant':
        return 'assistant'
      case 'system':
        return 'system'
      case 'tool':
        return 'tool'
      default:
        return 'user'
    }
  }

  // ============================================================
  // 渲染方法
  // ============================================================

  /**
   * 渲染请求体
   */
  renderRequest(requestBody: any): RenderResult {
    if (!requestBody) {
      return createEmptyRenderResult('无请求体')
    }

    try {
      const blocks: RenderBlock[] = []
      const isStream = requestBody.stream === true

      if (Array.isArray(requestBody.messages)) {
        for (const msg of requestBody.messages) {
          // system 消息单独处理
          if (msg.role === 'system') {
            const systemText = typeof msg.content === 'string' ? msg.content : ''
            if (systemText) {
              blocks.push(createMessageBlock('system', [
                createTextRenderBlock(systemText),
              ], { roleLabel: 'System' }))
            }
            continue
          }

          const msgBlock = this.renderMessage(msg)
          if (msgBlock) {
            blocks.push(msgBlock)
          }
        }
      }

      return { blocks, isStream }
    } catch (e) {
      return createEmptyRenderResult(`渲染失败: ${e}`)
    }
  }

  /**
   * 渲染响应体
   */
  renderResponse(responseBody: any): RenderResult {
    if (!responseBody) {
      return createEmptyRenderResult('无响应体')
    }

    // 检查是否为流式响应
    if (isStreamResponse(responseBody)) {
      return this.renderStreamResponse(responseBody.chunks || [])
    }

    try {
      const blocks: RenderBlock[] = []

      // OpenAI 响应格式: { choices: [{ message: { role, content, tool_calls } }] }
      const message = responseBody.choices?.[0]?.message
      if (message) {
        const contentBlocks: RenderBlock[] = []
        const badges: BadgeRenderBlock[] = []

        // 文本内容
        if (message.content) {
          contentBlocks.push(createTextRenderBlock(message.content))
        }

        // 工具调用
        if (message.tool_calls) {
          badges.push(createBadgeBlock('工具调用', 'outline'))
          for (const call of message.tool_calls) {
            contentBlocks.push(createToolUseRenderBlock(
              call.function?.name || '工具调用',
              this.formatJson(call.function?.arguments),
              call.id
            ))
          }
        }

        if (contentBlocks.length > 0) {
          blocks.push(createMessageBlock('assistant', contentBlocks, {
            roleLabel: 'Assistant',
            badges: badges.length > 0 ? badges : undefined,
          }))
        }
      }

      return { blocks, isStream: false }
    } catch (e) {
      return createEmptyRenderResult(`渲染失败: ${e}`)
    }
  }

  /**
   * 渲染流式响应
   */
  private renderStreamResponse(chunks: any[]): RenderResult {
    if (!chunks || chunks.length === 0) {
      return createEmptyRenderResult('无响应数据')
    }

    try {
      // 先解析流式响应
      const parsed = this.parseStreamResponse(chunks)
      if (parsed.parseError) {
        return createEmptyRenderResult(parsed.parseError)
      }

      const blocks: RenderBlock[] = []

      // 渲染解析后的消息
      for (const msg of parsed.messages) {
        const contentBlocks = this.renderParsedContentBlocks(msg.content)
        if (contentBlocks.length > 0) {
          const badges = this.getBadgesForParsedContent(msg.content)
          blocks.push(createMessageBlock(msg.role, contentBlocks, {
            roleLabel: this.getRoleLabel(msg.role),
            badges: badges.length > 0 ? badges : undefined,
          }))
        }
      }

      return { blocks, isStream: true }
    } catch (e) {
      return createEmptyRenderResult(`渲染失败: ${e}`)
    }
  }

  /**
   * 渲染单条消息
   */
  private renderMessage(msg: any): RenderBlock | null {
    if (!msg || !msg.role) return null

    const role = this.mapRole(msg.role)
    const contentBlocks: RenderBlock[] = []
    const badges: BadgeRenderBlock[] = []

    // 文本内容
    if (typeof msg.content === 'string') {
      contentBlocks.push(createTextRenderBlock(msg.content))
    } else if (Array.isArray(msg.content)) {
      // Vision API 格式
      for (const part of msg.content) {
        if (part.type === 'text') {
          contentBlocks.push(createTextRenderBlock(part.text || ''))
        } else if (part.type === 'image_url') {
          badges.push(createBadgeBlock('图片', 'secondary'))
          contentBlocks.push(createImageRenderBlock({
            src: part.image_url?.url,
            alt: '[图片]',
          }))
        }
      }
    }

    // 工具调用（assistant 消息）
    if (msg.tool_calls) {
      badges.push(createBadgeBlock('工具调用', 'outline'))
      for (const call of msg.tool_calls) {
        contentBlocks.push(createToolUseRenderBlock(
          call.function?.name || '工具调用',
          this.formatJson(call.function?.arguments),
          call.id
        ))
      }
    }

    // 工具结果（tool 消息）
    if (msg.tool_call_id) {
      badges.push(createBadgeBlock('工具结果', 'outline'))
      const content = typeof msg.content === 'string'
        ? msg.content
        : JSON.stringify(msg.content, null, 2)
      contentBlocks.push(createToolResultRenderBlock(content))
    }

    if (contentBlocks.length === 0) return null

    return createMessageBlock(role, contentBlocks, {
      roleLabel: this.getRoleLabel(role),
      badges: badges.length > 0 ? badges : undefined,
    })
  }

  /**
   * 渲染已解析的内容块数组
   */
  private renderParsedContentBlocks(blocks: ContentBlock[]): RenderBlock[] {
    const result: RenderBlock[] = []

    for (const block of blocks) {
      const rendered = this.renderParsedContentBlock(block)
      if (rendered) {
        result.push(rendered)
      }
    }

    return result
  }

  /**
   * 渲染单个已解析的内容块
   */
  private renderParsedContentBlock(block: ContentBlock): RenderBlock | null {
    switch (block.type) {
      case 'text':
        return createTextRenderBlock(block.text)

      case 'tool_use':
        return createToolUseRenderBlock(
          block.toolName || '工具调用',
          this.formatJson(block.input),
          block.toolId
        )

      case 'tool_result': {
        const content = typeof block.content === 'string'
          ? block.content
          : this.formatParsedToolResultContent(block.content)
        return createToolResultRenderBlock(content, block.isError)
      }

      case 'image':
        return createImageRenderBlock({
          src: block.sourceType === 'base64'
            ? `data:${block.mimeType || 'image/png'};base64,${block.data}`
            : block.url,
          mimeType: block.mimeType,
          alt: block.alt || '图片',
        })

      default:
        return null
    }
  }

  /**
   * 获取角色显示标签
   */
  private getRoleLabel(role: MessageRole): string {
    switch (role) {
      case 'user': return 'User'
      case 'assistant': return 'Assistant'
      case 'system': return 'System'
      case 'tool': return 'Tool'
      default: return role
    }
  }

  /**
   * 获取已解析内容的徽章
   */
  private getBadgesForParsedContent(content: ContentBlock[]): BadgeRenderBlock[] {
    const badges: BadgeRenderBlock[] = []
    const types = new Set(content.map(b => b.type))

    if (types.has('tool_use')) {
      badges.push(createBadgeBlock('工具调用', 'outline'))
    }
    if (types.has('tool_result')) {
      badges.push(createBadgeBlock('工具结果', 'outline'))
    }
    if (types.has('image')) {
      badges.push(createBadgeBlock('图片', 'secondary'))
    }

    return badges
  }

  /**
   * 格式化 JSON
   */
  private formatJson(input: any): string {
    if (typeof input === 'string') {
      try {
        const parsed = JSON.parse(input)
        return JSON.stringify(parsed, null, 2)
      } catch {
        return input
      }
    }
    return JSON.stringify(input, null, 2)
  }

  /**
   * 格式化已解析的工具结果内容
   */
  private formatParsedToolResultContent(content: ContentBlock[]): string {
    return content
      .map(block => {
        if (block.type === 'text') return block.text
        if (block.type === 'image') return '[图片]'
        if (block.type === 'error') return `[错误: ${block.message}]`
        return ''
      })
      .filter(Boolean)
      .join('\n')
  }
}

/** 单例实例 */
export const openaiParser = new OpenAIParser()
