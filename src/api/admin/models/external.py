"""
models.dev 外部模型数据代理
"""

import json

from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.clients import get_redis_client
from src.core.logger import logger
from src.models.database import User
from src.utils.auth_utils import require_admin

router = APIRouter()

CACHE_KEY = "aether:external:models_dev"
CACHE_TTL = 15 * 60  # 15 分钟


async def _get_cached_data() -> Optional[dict[str, Any]]:
    """从 Redis 获取缓存数据"""
    redis = await get_redis_client()
    if redis is None:
        return None
    try:
        cached = await redis.get(CACHE_KEY)
        if cached:
            result: dict[str, Any] = json.loads(cached)
            return result
    except Exception as e:
        logger.warning(f"读取 models.dev 缓存失败: {e}")
    return None


async def _set_cached_data(data: dict) -> None:
    """将数据写入 Redis 缓存"""
    redis = await get_redis_client()
    if redis is None:
        return
    try:
        await redis.setex(CACHE_KEY, CACHE_TTL, json.dumps(data, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"写入 models.dev 缓存失败: {e}")


@router.get("/external")
async def get_external_models(_: User = Depends(require_admin)) -> JSONResponse:
    """
    获取 models.dev 的模型数据（代理请求，解决跨域问题）
    数据缓存 15 分钟（使用 Redis，多 worker 共享）
    """
    # 检查缓存
    cached = await _get_cached_data()
    if cached is not None:
        return JSONResponse(content=cached)

    # 从 models.dev 获取数据
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://models.dev/api.json")
            response.raise_for_status()
            data = response.json()

            # 写入缓存
            await _set_cached_data(data)

            return JSONResponse(content=data)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="请求 models.dev 超时")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502, detail=f"models.dev 返回错误: {e.response.status_code}"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取外部模型数据失败: {str(e)}")
