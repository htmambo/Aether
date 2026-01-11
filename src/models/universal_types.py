"""
通用数据库类型定义

提供跨数据库兼容的类型定义，自动适配不同数据库方言。
当前支持:
- PostgreSQL: JSONB (高性能二进制 JSON)
- SQLite: JSON (文本 JSON)
"""

import json
from typing import Any

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class UniversalJSON(TypeDecorator):
    """
    数据库无关的 JSON 类型

    自动根据数据库方言选择最优实现:
    - PostgreSQL: 使用 JSONB（高性能、支持索引）
    - SQLite: 使用 JSON（兼容性好）

    特性:
    - 自动方言适配
    - 写入前验证 JSON 可序列化性
    - 读取后确保返回 Python 基本类型
    - 性能优化：启用类型处理器缓存

    使用示例:
        from src.models.universal_types import UniversalJSON

        class Provider(Base):
            __tablename__ = "providers"

            # PostgreSQL: JSONB, SQLite: JSON
            proxy = Column(UniversalJSON, nullable=True)
    """

    impl = JSON
    cache_ok = True  # 启用类型处理器缓存

    def load_dialect_impl(self, dialect):
        """
        根据数据库方言选择具体实现

        Args:
            dialect: SQLAlchemy 数据库方言对象

        Returns:
            ��言特定的 JSON 类型描述符
        """
        if dialect.name == "postgresql":
            # PostgreSQL 使用 JSONB（高性能、支持 GIN 索引）
            return dialect.type_descriptor(JSONB())
        else:
            # 其他数据库（SQLite 等）使用 JSON
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect):
        """
        在写入数据库前处理参数值

        验证值可序列化为 JSON，避免运行时错误。

        Args:
            value: 要写入的值
            dialect: 数据库方言

        Returns:
            处理后的值（JSON 可序列化）

        Raises:
            ValueError: 如果值不可序列化为 JSON
        """
        if value is None:
            return None

        try:
            # 尝试序列化以提前发现不可序列化对象
            serialized = json.dumps(value, ensure_ascii=False)
            # 反序列化回 Python 基本类型，避免自定义对象泄漏
            return json.loads(serialized)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"UniversalJSON 值不可序列化为 JSON: {exc}"
            ) from exc

    def process_result_value(self, value: Any, dialect):
        """
        在从数据库读取后处理值

        确保返回 Python 基本类型（dict/list）而非字符串。

        Args:
            value: 从数据库读取的原始值
            dialect: 数据库方言

        Returns:
            Python 基本类型（dict 或 list）

        Raises:
            ValueError: 如果值无法解析为 JSON
        """
        if value is None:
            return None

        # 已经是 Python 基本类型，直接返回
        if isinstance(value, (dict, list)):
            return value

        # 字符串或字节，尝试解析为 JSON
        if isinstance(value, (str, bytes, bytearray)):
            # 解码字节为字符串
            if isinstance(value, (bytes, bytearray)):
                value = value.decode('utf-8')

            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"无法解析数据库返回的 JSON 值: {exc}"
                ) from exc

        # 其他类型（很少见），尝试序列化后反序列化
        try:
            serialized = json.dumps(value)
            return json.loads(serialized)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"UniversalJSON 遇到意外的值类型: {type(value).__name__}, {exc}"
            ) from exc
