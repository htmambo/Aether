"""
测试 HTTP Header Name 验证功能
"""

import pytest
from src.core.header_rules import (
    is_valid_header_name,
    validate_header_names_in_dict,
    validate_header_names_in_list,
    HeaderRules,
)


class TestIsValidHeaderName:
    """测试 is_valid_header_name 函数"""

    def test_valid_header_names(self):
        """测试有效的 header names"""
        valid_names = [
            "Content-Type",
            "X-Custom-Header",
            "Authorization",
            "X-API-Key",
            "Accept",
            "User-Agent",
            "X-Request-ID",
            "Cache-Control",
            "If-None-Match",
            # 允许的特殊字符
            "X_Test_Header",
            "X.Test.Header",
            "X+Test+Header",
            "X*Test*Header",
        ]
        for name in valid_names:
            assert is_valid_header_name(name), f"'{name}' 应该是有效的 header name"

    def test_invalid_header_names(self):
        """测试无效的 header names"""
        invalid_names = [
            "",  # 空字符串
            "X Test",  # 包含空格
            "X:Test",  # 包含冒号
            "X;Test",  # 包含分号
            "X,Test",  # 包含逗号
            "X=Test",  # 包含等号
            "X(Test)",  # 包含括号
            "X<Test>",  # 包含尖括号
            "X{Test}",  # 包含花括号
            "X[Test]",  # 包含方括号
            "X\\Test",  # 包含反斜杠
            "X/Test",  # 包含斜杠
            '"X-Test"',  # 包含引号
            "X\tTest",  # 包含制表符
            "X\nTest",  # 包含换行符
            " a" * 150,  # 超过最大长度
        ]
        for name in invalid_names:
            if name == " a" * 150:  # 长度测试
                name = "a" * 150
            assert not is_valid_header_name(name), f"'{name}' 应该是无效的 header name"

    def test_case_sensitivity(self):
        """测试大小写敏感性"""
        assert is_valid_header_name("content-type")
        assert is_valid_header_name("CONTENT-TYPE")
        assert is_valid_header_name("Content-Type")


class TestValidateHeaderNamesInDict:
    """测试 validate_header_names_in_dict 函数"""

    def test_valid_dict(self):
        """测试有效的 headers 字典"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "secret",
            "Authorization": "Bearer token",
        }
        # 不应该抛出异常
        validate_header_names_in_dict(headers)

    def test_invalid_dict(self):
        """测试无效的 headers 字典"""
        headers = {
            "Content-Type": "application/json",
            "X Invalid Header": "value",  # 包含空格
            "Authorization": "Bearer token",
        }
        with pytest.raises(ValueError) as exc_info:
            validate_header_names_in_dict(headers)
        assert "无效的 HTTP header name" in str(exc_info.value)
        assert "X Invalid Header" in str(exc_info.value)

    def test_empty_dict(self):
        """测试空字典"""
        validate_header_names_in_dict({})  # 不应该抛出异常
        validate_header_names_in_dict(None)  # 不应该抛出异常


class TestValidateHeaderNamesInList:
    """测试 validate_header_names_in_list 函数"""

    def test_valid_list(self):
        """测试有效的 headers 列表"""
        headers = ["Content-Type", "X-API-Key", "Authorization"]
        # 不应该抛出异常
        validate_header_names_in_list(headers)

    def test_invalid_list(self):
        """测试无效的 headers 列表"""
        headers = ["Content-Type", "X Invalid Header", "Authorization"]
        with pytest.raises(ValueError) as exc_info:
            validate_header_names_in_list(headers)
        assert "无效的 HTTP header name" in str(exc_info.value)
        assert "X Invalid Header" in str(exc_info.value)

    def test_empty_list(self):
        """测试空列表"""
        validate_header_names_in_list([])  # 不应该抛出异常
        validate_header_names_in_list(None)  # 不应该抛出异常


class TestHeaderRulesValidation:
    """测试 HeaderRules 模型验证"""

    def test_valid_add_rule(self):
        """测试有效的 add 规则"""
        rules = HeaderRules(add={"Content-Type": "application/json"})
        assert rules.add == {"Content-Type": "application/json"}

    def test_invalid_add_rule(self):
        """测试无效的 add 规则"""
        with pytest.raises(ValueError) as exc_info:
            HeaderRules(add={"X Invalid Header": "value"})
        assert "无效的 HTTP header name" in str(exc_info.value)

    def test_valid_remove_rule(self):
        """测试有效的 remove 规则"""
        rules = HeaderRules(remove=["Content-Type", "Authorization"])
        assert rules.remove == ["Content-Type", "Authorization"]

    def test_invalid_remove_rule(self):
        """测试无效的 remove 规则"""
        with pytest.raises(ValueError) as exc_info:
            HeaderRules(remove=["Content-Type", "X Invalid"])
        assert "无效的 HTTP header name" in str(exc_info.value)

    def test_valid_replace_name_rule(self):
        """测试有效的 replace_name 规则"""
        rules = HeaderRules(replace_name={"Old-Name": "New-Name"})
        assert rules.replace_name == {"Old-Name": "New-Name"}

    def test_invalid_replace_name_key(self):
        """测试无效的 replace_name key"""
        with pytest.raises(ValueError) as exc_info:
            HeaderRules(replace_name={"X Invalid": "New-Name"})
        assert "无效的 HTTP header name" in str(exc_info.value)

    def test_invalid_replace_name_value(self):
        """测试无效的 replace_name value"""
        with pytest.raises(ValueError) as exc_info:
            HeaderRules(replace_name={"Old-Name": "X Invalid"})
        assert "无效的 HTTP header name" in str(exc_info.value)

    def test_valid_replace_value_rule(self):
        """测试有效的 replace_value 规则"""
        rules = HeaderRules(
            replace_value={
                "Content-Type": {
                    "search": "application/json",
                    "replace": "application/xml",
                    "regex": False,
                }
            }
        )
        assert "Content-Type" in rules.replace_value

    def test_invalid_replace_value_key(self):
        """测试无效的 replace_value key"""
        with pytest.raises(ValueError) as exc_info:
            HeaderRules(
                replace_value={
                    "X Invalid": {
                        "search": "old",
                        "replace": "new",
                    }
                }
            )
        assert "无效的 HTTP header name" in str(exc_info.value)

    def test_empty_rules(self):
        """测试空规则"""
        rules = HeaderRules()
        assert rules.is_empty()

    def test_complex_valid_rules(self):
        """测试复杂的有效规则"""
        rules = HeaderRules(
            add={"X-API-Key": "secret", "X-Request-ID": "12345"},
            remove=["Old-Header", "Another-Old"],
            replace_name={"Old-Name": "New-Name"},
            replace_value={
                "Content-Type": {
                    "search": "application/json",
                    "replace": "application/xml",
                }
            },
        )
        assert not rules.is_empty()

    def test_legacy_format(self):
        """测试旧格式（直接的 headers 字典）"""
        # 旧格式应该被接受（在 apply_header_rules 中处理）
        legacy_headers = {"Content-Type": "application/json", "X-API-Key": "secret"}
        # HeaderRules 应该能够解析它
        rules = HeaderRules(add=legacy_headers)
        assert rules.add == legacy_headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
