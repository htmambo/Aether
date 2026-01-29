"""
SSL 工具函数
提供统一的 SSL 上下文创建功能
"""

import ssl

try:
    import certifi

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()


def get_ssl_context() -> ssl.SSLContext:
    """
    获取 SSL 上下文

    优先使用 certifi 证书包，如果未安装则使用系统默认证书。
    返回模块级缓存的 SSL 上下文实例。

    Returns:
        ssl.SSLContext: SSL 上下文
    """
    return _SSL_CONTEXT
