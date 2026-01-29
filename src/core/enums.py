"""
统一的枚举定义
避免重复定义造成的不一致

注意：APIFormat 已移至 src/core/api_format/enums.py
"""

from enum import Enum


class UserRole(Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"


class ProviderBillingType(Enum):
    """提供商计费类型"""

    MONTHLY_QUOTA = "monthly_quota"  # 月卡额度
    PAY_AS_YOU_GO = "pay_as_you_go"  # 按量付费
    FREE_TIER = "free_tier"  # 免费额度


class AuthSource(str, Enum):
    """认证来源枚举"""

    LOCAL = "local"  # 本地认证
    LDAP = "ldap"  # LDAP 认证
    OAUTH = "oauth"  # OAuth 认证（账号首创来源）
