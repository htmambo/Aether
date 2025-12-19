"""
Provider Query API 端点
用于查询提供商的模型列表等信息
"""

import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from src.api.handlers.base.chat_adapter_base import get_adapter_class
from src.api.handlers.base.cli_adapter_base import get_cli_adapter_class
from src.core.crypto import crypto_service
from src.core.logger import logger
from src.database.database import get_db
from src.models.database import Provider, ProviderEndpoint, User
from src.utils.auth_utils import get_current_user

router = APIRouter(prefix="/api/admin/provider-query", tags=["Provider Query"])


# ============ Request/Response Models ============


class ModelsQueryRequest(BaseModel):
    """模型列表查询请求"""

    provider_id: str
    api_key_id: Optional[str] = None


# ============ API Endpoints ============


def _get_adapter_for_format(api_format: str):
    """根据 API 格式获取对应的 Adapter 类"""
    # 先检查 Chat Adapter 注册表
    adapter_class = get_adapter_class(api_format)
    if adapter_class:
        return adapter_class

    # 再检查 CLI Adapter 注册表
    cli_adapter_class = get_cli_adapter_class(api_format)
    if cli_adapter_class:
        return cli_adapter_class

    return None


@router.post("/models")
async def query_available_models(
    request: ModelsQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询提供商可用模型

    遍历所有活跃端点，根据端点的 API 格式选择正确的 Adapter 进行请求：
    - OPENAI/OPENAI_CLI: 使用 OpenAIChatAdapter.fetch_models
    - CLAUDE/CLAUDE_CLI: 使用 ClaudeChatAdapter.fetch_models
    - GEMINI/GEMINI_CLI: 使用 GeminiChatAdapter.fetch_models

    Args:
        request: 查询请求

    Returns:
        所有端点的模型列表（合并）
    """
    # 获取提供商及其端点
    provider = (
        db.query(Provider)
        .options(joinedload(Provider.endpoints).joinedload(ProviderEndpoint.api_keys))
        .filter(Provider.id == request.provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # 收集所有活跃端点的配置
    endpoint_configs: list[dict] = []

    if request.api_key_id:
        # 指定了特定的 API Key，只使用该 Key 对应的端点
        for endpoint in provider.endpoints:
            for api_key in endpoint.api_keys:
                if api_key.id == request.api_key_id:
                    try:
                        api_key_value = crypto_service.decrypt(api_key.api_key)
                    except Exception as e:
                        logger.error(f"Failed to decrypt API key: {e}")
                        raise HTTPException(status_code=500, detail="Failed to decrypt API key")
                    endpoint_configs.append({
                        "api_key": api_key_value,
                        "base_url": endpoint.base_url,
                        "api_format": endpoint.api_format,
                        "extra_headers": endpoint.headers,
                    })
                    break
            if endpoint_configs:
                break

        if not endpoint_configs:
            raise HTTPException(status_code=404, detail="API Key not found")
    else:
        # 遍历所有活跃端点，每个端点取第一个可用的 Key
        for endpoint in provider.endpoints:
            if not endpoint.is_active or not endpoint.api_keys:
                continue

            # 找第一个可用的 Key
            for api_key in endpoint.api_keys:
                if api_key.is_active:
                    try:
                        api_key_value = crypto_service.decrypt(api_key.api_key)
                    except Exception as e:
                        logger.error(f"Failed to decrypt API key: {e}")
                        continue  # 尝试下一个 Key
                    endpoint_configs.append({
                        "api_key": api_key_value,
                        "base_url": endpoint.base_url,
                        "api_format": endpoint.api_format,
                        "extra_headers": endpoint.headers,
                    })
                    break  # 只取第一个可用的 Key

        if not endpoint_configs:
            raise HTTPException(status_code=400, detail="No active API Key found for this provider")

    # 并发请求所有端点的模型列表
    all_models: list = []
    errors: list[str] = []

    async def fetch_endpoint_models(
        client: httpx.AsyncClient, config: dict
    ) -> tuple[list, Optional[str]]:
        base_url = config["base_url"]
        if not base_url:
            return [], None
        base_url = base_url.rstrip("/")
        api_format = config["api_format"]
        api_key_value = config["api_key"]
        extra_headers = config.get("extra_headers")

        try:
            # 获取对应的 Adapter 类并调用 fetch_models
            adapter_class = _get_adapter_for_format(api_format)
            if not adapter_class:
                return [], f"Unknown API format: {api_format}"
            return await adapter_class.fetch_models(
                client, base_url, api_key_value, extra_headers
            )
        except Exception as e:
            logger.error(f"Error fetching models from {api_format} endpoint: {e}")
            return [], f"{api_format}: {str(e)}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        results = await asyncio.gather(
            *[fetch_endpoint_models(client, c) for c in endpoint_configs]
        )
        for models, error in results:
            all_models.extend(models)
            if error:
                errors.append(error)

    # 按 model id 去重（保留第一个）
    seen_ids: set[str] = set()
    unique_models: list = []
    for model in all_models:
        model_id = model.get("id")
        if model_id and model_id not in seen_ids:
            seen_ids.add(model_id)
            unique_models.append(model)

    error = "; ".join(errors) if errors else None
    if not unique_models and not error:
        error = "No models returned from any endpoint"

    return {
        "success": len(unique_models) > 0,
        "data": {"models": unique_models, "error": error},
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "display_name": provider.display_name,
        },
    }
