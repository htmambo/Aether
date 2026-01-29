/**
 * Gemini API 格式解析器
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
 * Gemini API 格式解析器
 */
export class GeminiParser implements ApiFormatParser {
  readonly format = 'gemini' as const
  readonly displayName = 'Gemini'

  /**
   * 检测是否为 Gemini 格式
   */
  detect(requestBody: any, responseBody: any, hint?: string): number {
    // 1. 后端提示优先
    if (hint) {
      const lowerHint = hint.toLowerCase()
      if (lowerHint.includes('gemini')) return 100
      if (lowerHint.includes('claude') || lowerHint.includes('openai')) return 0
    }

    // 2. 检查模型名
    const model = requestBody?.model?.toLowerCase() || ''
    if (model.includes('gemini')) return 95

    // 3. Gemini 特有结构: 使用 contents 而非 messages
    if (requestBody?.contents && Array.isArray(requestBody.contents)) {
      return 90
    }

    // 4. 检查响应体特征
    const respBody = isStreamResponse(responseBody)
      ? responseBody.chunks?.[0]
      : responseBody

    if (respBody?.candidates) {
      return 85
    }

    return 0
  }

  /**
   * 解析请求体
   */
  parseRequest(requestBody: any): ParsedConversation {
    if (!requestBody) {
      return createEmptyConversation('gemini', '无请求体')
    }

    try {
      const result: ParsedConversation = {
        messages: [],
        isStream: false,
        apiFormat: 'gemini',
        model: requestBody.model,
      }

      // 提取 system instruction
      const sysInst = requestBody.system_instruction || requestBody.systemInstruction
      if (sysInst?.parts) {
        result.system = sysInst.parts
          .filter((p: any) => p.text)
          .map((p: any) => p.text)
          .join('\n')
      }

      // 提取 contents
      if (Array.isArray(requestBody.contents)) {
        for (const content of requestBody.contents) {
          const parsedMsg = this.parseContent(content)
          if (parsedMsg) {
            result.messages.push(parsedMsg)
          }
        }
      }

      return result
    } catch (e) {
      return createEmptyConversation('gemini', `解析失败: ${e}`)
    }
  }

  /**
   * 解析响应体
   */
  parseResponse(responseBody: any): ParsedConversation {
    if (!responseBody) {
      return createEmptyConversation('gemini', '无响应体')
    }

    try {
      const result: ParsedConversation = {
        messages: [],
        isStream: false,
        apiFormat: 'gemini',
      }

      // Gemini 响应格式: { candidates: [{ content: { parts: [...] } }] }
      const candidate = responseBody.candidates?.[0]
      if (candidate?.content?.parts) {
        const contentBlocks = this.parseParts(candidate.content.parts)
        if (contentBlocks.length > 0) {
          result.messages.push(createMessage('assistant', contentBlocks))
        }
      }

      return result
    } catch (e) {
      return createEmptyConversation('gemini', `解析失败: ${e}`)
    }
  }

  /**
   * 解析流式响应
   */
  parseStreamResponse(chunks: any[]): ParsedConversation {
    if (!chunks || chunks.length === 0) {
      return createEmptyConversation('gemini', '无响应数据')
    }

    try {
      const result: ParsedConversation = {
        messages: [],
        isStream: true,
        apiFormat: 'gemini',
      }

      const textParts: string[] = []
      const toolCalls: { name: string; args: any }[] = []

      for (const chunk of chunks) {
        const parts = chunk.candidates?.[0]?.content?.parts
        if (parts) {
          for (const part of parts) {
            if (part.text) {
              textParts.push(part.text)
            } else if (part.functionCall) {
              toolCalls.push(part.functionCall)
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
      for (const call of toolCalls) {
        contentBlocks.push(createToolUseBlock(
          '', // Gemini 没有 tool_use_id
          call.name || '',
          call.args || {}
        ))
      }

      if (contentBlocks.length > 0) {
        result.messages.push(createMessage('assistant', contentBlocks))
      }

      return result
    } catch (e) {
      return createEmptyConversation('gemini', `解析失败: ${e}`)
    }
  }

  /**
   * 解析 content 对象
   */
  private parseContent(content: any): ParsedMessage | null {
    if (!content) return null

    const role = this.mapRole(content.role)
    const contentBlocks = this.parseParts(content.parts || [])

    if (contentBlocks.length === 0) return null

    return createMessage(role, contentBlocks)
  }

  /**
   * 解析 parts 数组
   */
  private parseParts(parts: any[]): ContentBlock[] {
    const result: ContentBlock[] = []

    for (const part of parts) {
      const block = this.parsePart(part)
      if (block) {
        result.push(block)
      }
    }

    return result
  }

  /**
   * 解析单个 part
   */
  private parsePart(part: any): ContentBlock | null {
    if (!part) return null

    // 文本
    if (part.text !== undefined) {
      return createTextBlock(part.text)
    }

    // 内联数据（图片等）
    if (part.inlineData) {
      return createImageBlock('base64', {
        data: part.inlineData.data,
        mimeType: part.inlineData.mimeType,
      })
    }

    // 函数调用
    if (part.functionCall) {
      return createToolUseBlock(
        '',
        part.functionCall.name || '',
        part.functionCall.args || {}
      )
    }

    // 函数响应
    if (part.functionResponse) {
      return createToolResultBlock(
        '', // Gemini 用 name 关联
        JSON.stringify(part.functionResponse.response, null, 2)
      )
    }

    return null
  }

  /**
   * 映射角色
   */
  private mapRole(role: string | undefined): MessageRole {
    switch (role) {
      case 'user':
        return 'user'
      case 'model':
        return 'assistant'
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

      // 渲染 system instruction
      const sysInst = requestBody.system_instruction || requestBody.systemInstruction
      if (sysInst?.parts) {
        const systemText = sysInst.parts
          .filter((p: any) => p.text)
          .map((p: any) => p.text)
          .join('\n')
        if (systemText) {
          blocks.push(createMessageBlock('system', [
            createTextRenderBlock(systemText),
          ], { roleLabel: 'System' }))
        }
      }

      // 渲染 contents
      if (Array.isArray(requestBody.contents)) {
        for (const content of requestBody.contents) {
          const msgBlock = this.renderContent(content)
          if (msgBlock) {
            blocks.push(msgBlock)
          }
        }
      }

      return { blocks, isStream: false }
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

      // Gemini 响应格式: { candidates: [{ content: { parts: [...] } }] }
      const candidate = responseBody.candidates?.[0]
      if (candidate?.content?.parts) {
        const contentBlocks = this.renderParts(candidate.content.parts)
        if (contentBlocks.length > 0) {
          const badges = this.getBadgesForParts(candidate.content.parts)
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
   * 渲染 content 对象
   */
  private renderContent(content: any): RenderBlock | null {
    if (!content) return null

    const role = this.mapRole(content.role)
    const contentBlocks = this.renderParts(content.parts || [])

    if (contentBlocks.length === 0) return null

    const badges = this.getBadgesForParts(content.parts || [])

    return createMessageBlock(role, contentBlocks, {
      roleLabel: this.getRoleLabel(role),
      badges: badges.length > 0 ? badges : undefined,
    })
  }

  /**
   * 渲染 parts 数组
   */
  private renderParts(parts: any[]): RenderBlock[] {
    const result: RenderBlock[] = []

    for (const part of parts) {
      const rendered = this.renderPart(part)
      if (rendered) {
        result.push(rendered)
      }
    }

    return result
  }

  /**
   * 渲染单个 part
   */
  private renderPart(part: any): RenderBlock | null {
    if (!part) return null

    // 文本
    if (part.text !== undefined) {
      return createTextRenderBlock(part.text)
    }

    // 内联数据（图片等）
    if (part.inlineData) {
      return createImageRenderBlock({
        src: `data:${part.inlineData.mimeType || 'image/png'};base64,${part.inlineData.data}`,
        mimeType: part.inlineData.mimeType,
      })
    }

    // 函数调用
    if (part.functionCall) {
      return createToolUseRenderBlock(
        part.functionCall.name || '函数调用',
        this.formatJson(part.functionCall.args)
      )
    }

    // 函数响应
    if (part.functionResponse) {
      return createToolResultRenderBlock(
        this.formatJson(part.functionResponse.response)
      )
    }

    return null
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
          block.toolName || '函数调用',
          this.formatJson(block.input)
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
      case 'assistant': return 'Model'
      case 'system': return 'System'
      case 'tool': return 'Tool'
      default: return role
    }
  }

  /**
   * 获取 parts 的徽章
   */
  private getBadgesForParts(parts: any[]): BadgeRenderBlock[] {
    const badges: BadgeRenderBlock[] = []
    const hasImage = parts.some((p: any) => p.inlineData)
    const hasToolCall = parts.some((p: any) => p.functionCall)
    const hasToolResult = parts.some((p: any) => p.functionResponse)

    if (hasToolCall) {
      badges.push(createBadgeBlock('函数调用', 'outline'))
    }
    if (hasToolResult) {
      badges.push(createBadgeBlock('函数结果', 'outline'))
    }
    if (hasImage) {
      badges.push(createBadgeBlock('图片', 'secondary'))
    }

    return badges
  }

  /**
   * 获取已解析内容的徽章
   */
  private getBadgesForParsedContent(content: ContentBlock[]): BadgeRenderBlock[] {
    const badges: BadgeRenderBlock[] = []
    const types = new Set(content.map(b => b.type))

    if (types.has('tool_use')) {
      badges.push(createBadgeBlock('函数调用', 'outline'))
    }
    if (types.has('tool_result')) {
      badges.push(createBadgeBlock('函数结果', 'outline'))
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
export const geminiParser = new GeminiParser()
