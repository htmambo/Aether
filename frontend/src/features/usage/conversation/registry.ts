/**
 * 解析器注册表和统一入口
 */

import type { ApiFormat, ApiFormatParser, ParsedConversation } from './types'
import { createEmptyConversation, isStreamResponse } from './types'
import type { RenderResult } from './render'
import { createEmptyRenderResult } from './render'
import { claudeParser } from './claude'
import { openaiParser } from './openai'
import { geminiParser } from './gemini'

/**
 * 解析器注册表
 */
class ParserRegistry {
  private parsers: ApiFormatParser[] = []

  /**
   * 注册解析器
   */
  register(parser: ApiFormatParser): void {
    this.parsers.push(parser)
  }

  /**
   * 获取所有解析器
   */
  getAll(): ApiFormatParser[] {
    return [...this.parsers]
  }

  /**
   * 根据格式获取解析器
   */
  getByFormat(format: ApiFormat): ApiFormatParser | undefined {
    return this.parsers.find(p => p.format === format)
  }

  /**
   * 检测 API 格式并返回最佳匹配的解析器
   */
  detectParser(requestBody: any, responseBody: any, hint?: string): ApiFormatParser | undefined {
    let bestParser: ApiFormatParser | undefined
    let bestScore = 0

    for (const parser of this.parsers) {
      const score = parser.detect(requestBody, responseBody, hint)
      if (score > bestScore) {
        bestScore = score
        bestParser = parser
      }
    }

    return bestScore > 0 ? bestParser : undefined
  }

  /**
   * 检测 API 格式
   */
  detectFormat(requestBody: any, responseBody: any, hint?: string): ApiFormat {
    const parser = this.detectParser(requestBody, responseBody, hint)
    return parser?.format ?? 'unknown'
  }
}

/** 全局解析器注册表 */
export const parserRegistry = new ParserRegistry()

// 注册默认解析器
parserRegistry.register(claudeParser)
parserRegistry.register(openaiParser)
parserRegistry.register(geminiParser)

/**
 * 解析请求体
 */
export function parseRequest(
  requestBody: any,
  responseBody?: any,
  formatHint?: string
): ParsedConversation {
  if (!requestBody) {
    return createEmptyConversation('unknown', '无请求体')
  }

  const parser = parserRegistry.detectParser(requestBody, responseBody, formatHint)
  if (!parser) {
    return createEmptyConversation('unknown', '无法识别的 API 格式')
  }

  return parser.parseRequest(requestBody)
}

/**
 * 解析响应体
 */
export function parseResponse(
  responseBody: any,
  requestBody?: any,
  formatHint?: string
): ParsedConversation {
  if (!responseBody) {
    return createEmptyConversation('unknown', '无响应体')
  }

  const parser = parserRegistry.detectParser(requestBody, responseBody, formatHint)
  if (!parser) {
    return createEmptyConversation('unknown', '无法识别的 API 格式')
  }

  // 判断是否为流式响应
  if (isStreamResponse(responseBody)) {
    return parser.parseStreamResponse(responseBody.chunks || [])
  }

  return parser.parseResponse(responseBody)
}

/**
 * 检测 API 格式
 */
export function detectApiFormat(
  requestBody: any,
  responseBody: any,
  hint?: string
): ApiFormat {
  return parserRegistry.detectFormat(requestBody, responseBody, hint)
}

/**
 * 渲染请求体
 */
export function renderRequest(
  requestBody: any,
  responseBody?: any,
  formatHint?: string
): RenderResult {
  if (!requestBody) {
    return createEmptyRenderResult('无请求体')
  }

  const parser = parserRegistry.detectParser(requestBody, responseBody, formatHint)
  if (!parser) {
    return createEmptyRenderResult('无法识别的 API 格式')
  }

  return parser.renderRequest(requestBody)
}

/**
 * 渲染响应体
 */
export function renderResponse(
  responseBody: any,
  requestBody?: any,
  formatHint?: string
): RenderResult {
  if (!responseBody) {
    return createEmptyRenderResult('无响应体')
  }

  const parser = parserRegistry.detectParser(requestBody, responseBody, formatHint)
  if (!parser) {
    return createEmptyRenderResult('无法识别的 API 格式')
  }

  return parser.renderResponse(responseBody)
}
