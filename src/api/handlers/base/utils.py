"""
Handler 基础工具函数
"""

from typing import Any, Dict, Optional


def extract_cache_creation_tokens(usage: Dict[str, Any]) -> int:
    """
    提取缓存创建 tokens（兼容新旧格式）

    Claude API 在不同版本中使用了不同的字段名来表示缓存创建 tokens：
    - 新格式（2024年后）：使用 claude_cache_creation_5_m_tokens 和
      claude_cache_creation_1_h_tokens 分别表示 5 分钟和 1 小时缓存
    - 旧格式：使用 cache_creation_input_tokens 表示总的缓存创建 tokens

    此函数自动检测并适配两种格式，优先使用新格式。

    Args:
        usage: API 响应中的 usage 字典

    Returns:
        缓存创建 tokens 总数
    """
    # 检查新格式字段是否存在（而非值是否为 0）
    # 如果字段存在，即使值为 0 也是合法的，不应 fallback 到旧格式
    has_new_format = (
        "claude_cache_creation_5_m_tokens" in usage
        or "claude_cache_creation_1_h_tokens" in usage
    )

    if has_new_format:
        cache_5m = usage.get("claude_cache_creation_5_m_tokens", 0)
        cache_1h = usage.get("claude_cache_creation_1_h_tokens", 0)
        return int(cache_5m) + int(cache_1h)

    # 回退到旧格式
    return int(usage.get("cache_creation_input_tokens", 0))


def build_sse_headers(extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    构建 SSE（text/event-stream）推荐响应头，用于减少代理缓冲带来的卡顿/成段输出。

    说明：
    - Cache-Control: no-transform 可避免部分代理对流做压缩/改写导致缓冲
    - X-Accel-Buffering: no 可显式提示 Nginx 关闭缓冲（即使全局已关闭也无害）
    """
    headers: Dict[str, str] = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers
