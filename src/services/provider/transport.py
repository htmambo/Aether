"""
统一的 Provider 请求构建工具。

负责:
- 根据 API 格式或端点配置生成请求 URL
- URL 脱敏（用于日志记录）
"""

import re
from typing import TYPE_CHECKING, Any, Dict, Optional
from urllib.parse import urlencode

from src.core.api_format import (
    APIFormat,
    HeaderBuilder,
    UPSTREAM_DROP_HEADERS,
    get_auth_config,
    get_default_path,
    resolve_api_format,
)
from src.core.crypto import crypto_service
from src.core.header_rules import apply_header_rules
from src.core.logger import logger

if TYPE_CHECKING:
    from src.models.database import ProviderEndpoint


# URL 中需要脱敏的查询参数（正则模式）
_SENSITIVE_QUERY_PARAMS_PATTERN = re.compile(
    r"([?&])(key|api_key|apikey|token|secret|password|credential)=([^&]*)",
    re.IGNORECASE,
)


def redact_url_for_log(url: str) -> str:
    """
    对 URL 中的敏感查询参数进行脱敏，用于日志记录

    将 ?key=xxx 替换为 ?key=***

    Args:
        url: 原始 URL

    Returns:
        脱敏后的 URL
    """
    return _SENSITIVE_QUERY_PARAMS_PATTERN.sub(r"\1\2=***", url)


def build_provider_headers(
    *,
    endpoint: "ProviderEndpoint",
    key: Any,
    original_headers: Dict[str, str],
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    构建发送给上游 Provider 的请求头

    兼容两种配置格式：
    - 新格式: endpoint.header_rules (list)
    - 旧格式: endpoint.headers (dict / add/remove/replace_name/replace_value)
    """
    # api_key 在数据库中是 NOT NULL，类型标注为 Optional 是 SQLAlchemy 限制
    decrypted_key = crypto_service.decrypt(key.api_key)  # type: ignore[arg-type]

    # 根据 API 格式自动选择认证头
    api_format = getattr(endpoint, "api_format", None)
    resolved_format = resolve_api_format(api_format)
    auth_header, auth_type = (
        get_auth_config(resolved_format) if resolved_format else ("Authorization", "bearer")
    )

    auth_value = f"Bearer {decrypted_key}" if auth_type == "bearer" else decrypted_key
    protected_keys = {auth_header.lower(), "content-type"} | set(UPSTREAM_DROP_HEADERS)

    builder = HeaderBuilder()

    # 1. 透传原始头部（排除默认敏感头部）
    for name, value in (original_headers or {}).items():
        if name.lower() in UPSTREAM_DROP_HEADERS:
            continue
        builder.add(name, value)

    # 2. 应用新格式 header_rules（认证头受保护）
    header_rules = getattr(endpoint, "header_rules", None)
    if isinstance(header_rules, list):
        builder.apply_rules(header_rules, protected_keys)

    # 3. 添加额外头部（保护敏感头）
    if extra_headers:
        builder.add_protected(extra_headers, protected_keys)

    headers = builder.build()

    # 4. 兼容旧格式 headers 规则（如有）
    legacy_headers = getattr(endpoint, "headers", None)
    if legacy_headers is None and isinstance(header_rules, dict):
        legacy_headers = header_rules

    if legacy_headers:
        headers = _apply_legacy_headers(headers, legacy_headers, protected_keys)

    # 5. 强制设置认证头（最高优先级）
    headers[auth_header] = auth_value

    # 6. 确保有 Content-Type
    if not any(k.lower() == "content-type" for k in headers):
        headers["Content-Type"] = "application/json"

    return headers


def _apply_legacy_headers(
    base_headers: Dict[str, str],
    legacy_headers: Dict[str, Any],
    protected_keys: set[str],
) -> Dict[str, str]:
    """
    应用旧格式 headers 规则，并保护敏感头部不被覆盖/注入。
    """
    protected = {k.lower() for k in protected_keys}
    headers = dict(base_headers)

    # 检测旧规则格式
    rule_keys = {"add", "remove", "replace_name", "replace_value"}
    is_rule_format = isinstance(legacy_headers, dict) and any(key in legacy_headers for key in rule_keys)

    if is_rule_format:
        processed = apply_header_rules(headers, legacy_headers)
        # 恢复受保护键的原值
        for key, value in base_headers.items():
            if key.lower() in protected:
                processed[key] = value
        # 移除任何新写入的受保护键
        for key in list(processed.keys()):
            if key.lower() in protected and key not in base_headers:
                processed.pop(key, None)
        return processed

    # 旧格式：直接合并，但排除受保护键
    safe_headers = {k: v for k, v in legacy_headers.items() if k.lower() not in protected}
    headers.update(safe_headers)
    return headers


def _normalize_base_url(base_url: str, path: str) -> str:
    """
    规范化 base_url，去除末尾的斜杠和可能与 path 重复的版本前缀。

    只有当 path 以版本前缀开头时，才从 base_url 中移除该前缀，
    避免拼接出 /v1/v1/messages 这样的重复路径。

    兼容用户填写的各种格式：
    - https://api.example.com
    - https://api.example.com/
    - https://api.example.com/v1
    - https://api.example.com/v1/
    """
    base = base_url.rstrip("/")
    # 只在 path 以版本前缀开头时才去除 base_url 中的该前缀
    # 例如：base="/v1", path="/v1/messages" -> 去除 /v1
    # 例如：base="/v1", path="/chat/completions" -> 不去除（用户可能期望保留）
    for suffix in ("/v1beta", "/v1", "/v2", "/v3"):
        if base.endswith(suffix) and path.startswith(suffix):
            base = base[: -len(suffix)]
            break
    return base


def build_provider_url(
    endpoint: "ProviderEndpoint",
    *,
    query_params: Optional[Dict[str, Any]] = None,
    path_params: Optional[Dict[str, Any]] = None,
    is_stream: bool = False,
) -> str:
    """
    根据 endpoint 配置生成请求 URL

    优先级：
    1. endpoint.custom_path - 自定义路径（支持模板变量如 {model}）
    2. API 格式默认路径 - 根据 api_format 自动选择

    Args:
        endpoint: 端点配置
        query_params: 查询参数
        path_params: 路径模板参数 (如 {model})
        is_stream: 是否为流式请求，用于 Gemini API 选择正确的操作方法
    """
    # 准备路径参数，添加 Gemini API 所需的 action 参数
    effective_path_params = dict(path_params) if path_params else {}

    # 为 Gemini API 格式自动添加 action 参数
    resolved_format = resolve_api_format(endpoint.api_format)
    if resolved_format in (APIFormat.GEMINI, APIFormat.GEMINI_CLI):
        if "action" not in effective_path_params:
            effective_path_params["action"] = (
                "streamGenerateContent" if is_stream else "generateContent"
            )

    # 优先使用 custom_path 字段
    if endpoint.custom_path:
        path = endpoint.custom_path
        if effective_path_params:
            try:
                path = path.format(**effective_path_params)
            except KeyError:
                # 如果模板变量不匹配，保持原路径
                pass
    else:
        # 使用 API 格式的默认路径
        path = _resolve_default_path(endpoint.api_format)
        if effective_path_params:
            try:
                path = path.format(**effective_path_params)
            except KeyError:
                # 如果模板变量不匹配，保持原路径
                pass

    if not path.startswith("/"):
        path = f"/{path}"

    # 先确定 path，再根据 path 规范化 base_url
    # base_url 在数据库中是 NOT NULL，类型标注为 Optional 是 SQLAlchemy 限制
    base = _normalize_base_url(endpoint.base_url, path)  # type: ignore[arg-type]
    url = f"{base}{path}"

    # 合并查询参数
    effective_query_params = dict(query_params) if query_params else {}

    # Gemini 格式下清除可能存在的 key 参数（避免客户端传入的认证信息泄露到上游）
    # 上游认证始终使用 header 方式，不使用 URL 参数
    if resolved_format in (APIFormat.GEMINI, APIFormat.GEMINI_CLI):
        effective_query_params.pop("key", None)
        # Gemini streamGenerateContent 官方支持 `?alt=sse` 返回 SSE（data: {...}）。
        # 网关侧统一使用 SSE 输出，优先向上游请求 SSE 以减少解析分支；同时保留 JSON-array 兜底解析。
        if is_stream:
            effective_query_params.setdefault("alt", "sse")

    # 添加查询参数
    if effective_query_params:
        query_string = urlencode(effective_query_params, doseq=True)
        if query_string:
            url = f"{url}?{query_string}"

    return url


def _resolve_default_path(api_format: Optional[str]) -> str:
    """
    根据 API 格式返回默认路径
    """
    resolved = resolve_api_format(api_format)
    if resolved:
        return get_default_path(resolved)

    logger.warning(f"Unknown api_format '{api_format}' for endpoint, fallback to '/'")
    return "/"
