"""
Headers 规则处理器

支持在 endpoint.headers 字段中定义复杂的 headers 操作规则：
1. add: 新增固定的参数和值
2. remove: 删除指定的参数
3. replace_name: 替换参数名
4. replace_value: 替换参数的值

数据格式：
{
  "add": {"X-New-Header": "value"},
  "remove": ["Old-Header"],
  "replace_name": {"Old-Name": "New-Name"},
  "replace_value": {"Header-Name": {"search": "old", "replace": "new", "regex": false}}
}
"""

import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


# HTTP Header Name 验证（RFC 7230, RFC 9110）
# token = 1*tchar
# tchar = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." /
#         "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
HTTP_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")

# 限制 header name 的最大长度（常见限制）
MAX_HEADER_NAME_LENGTH = 128


def is_valid_header_name(name: str) -> bool:
    """
    验证 HTTP header name 是否符合规范

    根据 RFC 7230 和 RFC 9110：
    - 必须是 token 格式
    - 不能包含空格、控制字符、冒号、分号、逗号等特殊字符
    - 只能包含：!#$%&'*+-.^_`|~ 字母和数字
    - 建议不超过 128 个字符

    Args:
        name: 要验证的 header name

    Returns:
        是否有效
    """
    if not name:
        return False

    if len(name) > MAX_HEADER_NAME_LENGTH:
        return False

    return bool(HTTP_HEADER_NAME_PATTERN.match(name))


def validate_header_names_in_dict(headers_dict: Optional[Dict[str, Any]], field_name: str = "headers") -> List[str]:
    """
    验证字典中的所有 header key 是否有效

    Args:
        headers_dict: 要验证的 headers 字典
        field_name: 字段名称（用于错误提示）

    Returns:
        无效的 header name 列表

    Raises:
        ValueError: 如果发现无效的 header name
    """
    if not headers_dict:
        return []

    invalid_names = []
    for key in headers_dict.keys():
        if not isinstance(key, str):
            invalid_names.append(str(key))
            continue

        if not is_valid_header_name(key):
            invalid_names.append(key)

    if invalid_names:
        raise ValueError(
            f"无效的 HTTP header name ({field_name}): {', '.join(repr(n) for n in invalid_names)}. "
            f"Header name 必须符合 RFC 7230 规范，只能包含字母、数字和 !#$%&'*+-.^_`|~ 字符，"
            f"不能包含空格、冒号、分号、逗号等特殊字符。"
        )

    return invalid_names


def validate_header_names_in_list(headers_list: Optional[List[str]], field_name: str = "headers") -> List[str]:
    """
    验证列表中的所有 header name 是否有效

    Args:
        headers_list: 要验证的 headers 列表
        field_name: 字段名称（用于错误提示）

    Returns:
        无效的 header name 列表

    Raises:
        ValueError: 如果发现无效的 header name
    """
    if not headers_list:
        return []

    invalid_names = []
    for name in headers_list:
        if not isinstance(name, str):
            invalid_names.append(str(name))
            continue

        if not is_valid_header_name(name):
            invalid_names.append(name)

    if invalid_names:
        raise ValueError(
            f"无效的 HTTP header name ({field_name}): {', '.join(repr(n) for n in invalid_names)}. "
            f"Header name 必须符合 RFC 7230 规范，只能包含字母、数字和 !#$%&'*+-.^_`|~ 字符，"
            f"不能包含空格、冒号、分号、逗号等特殊字符。"
        )

    return invalid_names


class ReplaceValueRule(BaseModel):
    """替换值的规则"""
    search: str = Field(..., description="要搜索的值")
    replace: str = Field(..., description="替换后的值")
    regex: bool = Field(default=False, description="是否使用正则表达式")
    case_sensitive: bool = Field(default=True, description="是否区分大小写")

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: str, info) -> str:
        """验证搜索字符串"""
        regex = info.data.get("regex", False)
        if regex:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v


class HeaderRules(BaseModel):
    """Headers 规则配置"""
    add: Optional[Dict[str, str]] = Field(default=None, description="新增的 headers")
    remove: Optional[List[str]] = Field(default=None, description="要删除的 header 名称")
    replace_name: Optional[Dict[str, str]] = Field(default=None, description="参数名替换映射")
    replace_value: Optional[Dict[str, Union[ReplaceValueRule, Dict[str, Any]]]] = Field(
        default=None, description="参数值替换规则"
    )

    @field_validator("add")
    @classmethod
    def validate_add(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """验证 add 中的 header name"""
        if v is not None:
            validate_header_names_in_dict(v, "headers.add")
        return v

    @field_validator("remove")
    @classmethod
    def validate_remove(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """验证 remove 中的 header name"""
        if v is not None:
            validate_header_names_in_list(v, "headers.remove")
        return v

    @field_validator("replace_name")
    @classmethod
    def validate_replace_name(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """验证 replace_name 中的 header name（包括 key 和 value）"""
        if v is not None:
            # 验证 key（旧名称）
            validate_header_names_in_dict(v, "headers.replace_name")

            # 验证 value（新名称）
            for key, new_name in v.items():
                if not isinstance(new_name, str):
                    raise ValueError(
                        f"headers.replace_name 的值必须是字符串，但 '{key}' 的值是 {type(new_name).__name__}"
                    )
                if not is_valid_header_name(new_name):
                    raise ValueError(
                        f"无效的 HTTP header name (headers.replace_name['{key}']): {repr(new_name)}. "
                        f"Header name 必须符合 RFC 7230 规范。"
                    )
        return v

    @field_validator("replace_value")
    @classmethod
    def validate_replace_value(cls, v: Optional[Dict[str, Union[ReplaceValueRule, Dict[str, Any]]]]) -> Optional[Dict[str, Union[ReplaceValueRule, Dict[str, Any]]]]:
        """验证 replace_value 中的 header name"""
        if v is not None:
            validate_header_names_in_dict(v, "headers.replace_value")
        return v

    def is_empty(self) -> bool:
        """检查是否没有任何规则"""
        return not any([
            self.add,
            self.remove,
            self.replace_name,
            self.replace_value
        ])


def apply_header_rules(
    headers: Dict[str, str],
    rules: Optional[Dict[str, Any]]
) -> Dict[str, str]:
    """
    应用 headers 规则到 headers 字典

    Args:
        headers: 原始 headers 字典
        rules: headers 规则配置（可以是字典或 HeaderRules 对象）

    Returns:
        处理后的 headers 字典
    """
    if not rules:
        return headers

    # 解析规则
    try:
        if isinstance(rules, dict):
            # 检查是否是旧格式（直接的 headers 字典）
            if not any(key in rules for key in ["add", "remove", "replace_name", "replace_value"]):
                # 旧格式：直接合并
                header_rules = HeaderRules(add=rules)
            else:
                # 新格式：包含规则
                header_rules = HeaderRules(**rules)
        else:
            header_rules = HeaderRules()
    except Exception as e:
        # 如果解析失败，返回原始 headers
        from src.core.logger import logger
        logger.warning(f"Failed to parse header rules: {e}, using original headers")
        return headers

    if header_rules.is_empty():
        return headers

    # 创建副本避免修改原始数据
    result = dict(headers)

    # 1. 删除指定的 headers
    if header_rules.remove:
        for key in header_rules.remove:
            # 大小写不敏感删除
            keys_to_remove = [k for k in result.keys() if k.lower() == key.lower()]
            for k in keys_to_remove:
                del result[k]

    # 2. 替换参数名
    if header_rules.replace_name:
        for old_name, new_name in header_rules.replace_name.items():
            # 大小写不敏感查找
            for key in list(result.keys()):
                if key.lower() == old_name.lower():
                    value = result.pop(key)
                    result[new_name] = value
                    break

    # 3. 替换参数值
    if header_rules.replace_value:
        for header_name, value_rule in header_rules.replace_value.items():
            # 大小写不敏感查找
            for key in result.keys():
                if key.lower() == header_name.lower():
                    # 解析规则
                    if isinstance(value_rule, dict):
                        rule = ReplaceValueRule(**value_rule)
                    else:
                        rule = value_rule

                    original_value = result[key]
                    new_value = _apply_replace_value(original_value, rule)
                    result[key] = new_value
                    break

    # 4. 新增 headers（不会覆盖已存在的）
    if header_rules.add:
        for key, value in header_rules.add.items():
            # 只有当 key 不存在时才添加
            if key not in result:
                result[key] = value

    return result


def _apply_replace_value(original: str, rule: ReplaceValueRule) -> str:
    """
    应用值替换规则

    Args:
        original: 原始值
        rule: 替换规则

    Returns:
        替换后的值
    """
    if rule.regex:
        # 正则表达式替换
        flags = 0 if rule.case_sensitive else re.IGNORECASE
        try:
            return re.sub(rule.search, rule.replace, original, flags=flags)
        except re.error as e:
            from src.core.logger import logger
            logger.warning(f"Regex replace failed: {e}, returning original value")
            return original
    else:
        # 普通字符串替换
        if rule.case_sensitive:
            return original.replace(rule.search, rule.replace)
        else:
            # 大小写不敏感替换
            pattern = re.compile(re.escape(rule.search), re.IGNORECASE)
            return pattern.sub(rule.replace, original)


def validate_header_rules(rules: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    验证 headers 规则配置

    Args:
        rules: 要验证的规则字典

    Returns:
        (is_valid, error_message): 是否有效和错误信息
    """
    try:
        # 尝试解析规则
        header_rules = HeaderRules(**rules)

        # 额外验证：检查正则表达式是否有效
        if header_rules.replace_value:
            for header_name, value_rule in header_rules.replace_value.items():
                if isinstance(value_rule, ReplaceValueRule):
                    if value_rule.regex:
                        try:
                            re.compile(value_rule.search)
                        except re.error as e:
                            return False, f"Invalid regex in '{header_name}': {e}"

        return True, None
    except Exception as e:
        return False, str(e)


def merge_legacy_headers(
    headers: Optional[Dict[str, str]],
    rules: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    合并旧格式的 headers 和新格式的规则

    旧格式：{"X-Header": "value"}
    新格式：{"add": {"X-Header": "value"}, "remove": [...]}

    Args:
        headers: 旧格式的 headers
        rules: 新格式的规则

    Returns:
        合并后的规则
    """
    result = {}

    # 如果有规则，先合并规则
    if rules:
        result.update(rules)

    # 如果有旧格式的 headers，添加到 add 中
    if headers:
        if "add" not in result:
            result["add"] = {}
        result["add"].update(headers)

    return result
