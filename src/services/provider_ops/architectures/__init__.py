"""
Provider 架构模块
"""

from src.services.provider_ops.architectures.base import (
    ProviderArchitecture,
    ProviderConnector,
    VerifyResult,
)
from src.services.provider_ops.architectures.anyrouter import AnyrouterArchitecture
from src.services.provider_ops.architectures.cubence import CubenceArchitecture
from src.services.provider_ops.architectures.generic_api import GenericApiArchitecture
from src.services.provider_ops.architectures.nekocode import NekoCodeArchitecture
from src.services.provider_ops.architectures.new_api import NewApiArchitecture
from src.services.provider_ops.architectures.one_api import OneApiArchitecture
from src.services.provider_ops.architectures.yescode import YesCodeArchitecture

__all__ = [
    "ProviderArchitecture",
    "ProviderConnector",
    "VerifyResult",
    "AnyrouterArchitecture",
    "CubenceArchitecture",
    "GenericApiArchitecture",
    "NekoCodeArchitecture",
    "NewApiArchitecture",
    "OneApiArchitecture",
    "YesCodeArchitecture",
]
