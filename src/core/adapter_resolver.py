"""
Adapter 解析工具

集中提供“根据 api_format 获取对应 Adapter 类”的逻辑，避免在不同模块里重复实现。

注意：
- Chat Adapter 与 CLI Adapter 分别维护自己的注册表；
- 这里做一个统一入口，优先查 Chat，再查 CLI（与历史行为保持一致）。
"""

from __future__ import annotations

from typing import Optional, Type


def get_adapter_class_for_format(api_format: str) -> Optional[Type]:
    """根据 API 格式获取对应的 Adapter 类（Chat 优先，其次 CLI）。"""
    if not api_format:
        return None

    fmt = api_format.upper()

    # 延迟导入避免循环依赖
    from src.api.handlers.base.chat_adapter_base import get_adapter_class
    from src.api.handlers.base.cli_adapter_base import get_cli_adapter_class

    adapter_class = get_adapter_class(fmt)
    if adapter_class:
        return adapter_class

    cli_adapter_class = get_cli_adapter_class(fmt)
    if cli_adapter_class:
        return cli_adapter_class

    return None

