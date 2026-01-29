"""
API 格式枚举定义

定义所有支持的 API 格式，决定请求/响应的处理方式。
"""

from enum import Enum


class APIFormat(Enum):
    """API 格式枚举 - 决定请求/响应的处理方式"""

    CLAUDE = "CLAUDE"  # Claude API 格式
    CLAUDE_CLI = "CLAUDE_CLI"  # Claude CLI API 格式（使用 authorization: Bearer）
    OPENAI = "OPENAI"  # OpenAI API 格式
    OPENAI_CLI = "OPENAI_CLI"  # OpenAI CLI/Responses API 格式（用于 Claude Code 等客户端）
    GEMINI = "GEMINI"  # Google Gemini API 格式
    GEMINI_CLI = "GEMINI_CLI"  # Gemini CLI API 格式


__all__ = ["APIFormat"]
