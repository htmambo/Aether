"""
OpenAI CLI Adapter - 基于通用 CLI Adapter 基类的简化实现

继承 CliAdapterBase，只需配置 FORMAT_ID 和 HANDLER_CLASS。
"""

from typing import Dict, Optional, Tuple, Type

import httpx
from fastapi import Request

from src.api.handlers.base.cli_adapter_base import CliAdapterBase, register_cli_adapter
from src.api.handlers.base.cli_handler_base import CliMessageHandlerBase
from src.api.handlers.openai.adapter import OpenAIChatAdapter
from src.config.settings import config


@register_cli_adapter
class OpenAICliAdapter(CliAdapterBase):
    """
    OpenAI CLI API 适配器

    处理 /v1/responses 端点的请求。
    """

    FORMAT_ID = "OPENAI_CLI"
    name = "openai.cli"

    @property
    def HANDLER_CLASS(self) -> Type[CliMessageHandlerBase]:
        """延迟导入 Handler 类避免循环依赖"""
        from src.api.handlers.openai_cli.handler import OpenAICliMessageHandler

        return OpenAICliMessageHandler

    def __init__(self, allowed_api_formats: Optional[list[str]] = None):
        super().__init__(allowed_api_formats or ["OPENAI_CLI"])

    def extract_api_key(self, request: Request) -> Optional[str]:
        """从请求中提取 API 密钥 (Authorization: Bearer)"""
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
        return None

    # =========================================================================
    # 模型列表查询
    # =========================================================================

    @classmethod
    async def fetch_models(
        cls,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[list, Optional[str]]:
        """查询 OpenAI 兼容 API 支持的模型列表（带 CLI User-Agent）"""
        # 复用 OpenAIChatAdapter 的实现，添加 CLI User-Agent
        cli_headers = {"User-Agent": config.internal_user_agent_openai}
        if extra_headers:
            cli_headers.update(extra_headers)
        models, error = await OpenAIChatAdapter.fetch_models(
            client, base_url, api_key, cli_headers
        )
        # 更新 api_format 为 CLI 格式
        for m in models:
            m["api_format"] = cls.FORMAT_ID
        return models, error


__all__ = ["OpenAICliAdapter"]
