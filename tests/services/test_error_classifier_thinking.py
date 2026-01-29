"""
ErrorClassifier Thinking 错误模式测试

测试 ErrorClassifier 对 Thinking 相关错误的识别：
- 签名验证失败
- 结构错误（缺少 thinking 块前缀）
"""

from unittest.mock import MagicMock

import pytest

from src.services.orchestration.error_classifier import ErrorClassifier


class TestThinkingErrorPatterns:
    """测试 Thinking 错误模式匹配"""

    @pytest.fixture
    def classifier(self) -> ErrorClassifier:
        mock_db = MagicMock()
        return ErrorClassifier(db=mock_db)

    # === 签名错误测试 ===

    def test_detect_invalid_signature_with_backticks(self, classifier: ErrorClassifier) -> None:
        """检测带反引号的签名错误"""
        error = '{"error": {"message": "invalid `signature` in `thinking` block"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_invalid_signature_without_backticks(self, classifier: ErrorClassifier) -> None:
        """检测不带反引号的签名错误"""
        error = '{"error": {"message": "invalid signature in thinking block"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_signature_field_required(self, classifier: ErrorClassifier) -> None:
        """检测签名字段缺失错误"""
        error = '{"error": {"message": "thinking.signature: field required"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_signature_path_pattern(self, classifier: ErrorClassifier) -> None:
        """检测签名路径模式（如 messages.0.content.0.thinking.signature）"""
        error = '{"error": {"message": "messages.0.content.0.thinking.signature: invalid"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_signature_verification_failed(self, classifier: ErrorClassifier) -> None:
        """检测签名验证失败"""
        error = '{"error": {"message": "signature verification failed"}}'
        assert classifier._is_thinking_error(error) is True

    # === 结构错误测试 ===

    def test_detect_must_start_with_thinking_block(self, classifier: ErrorClassifier) -> None:
        """检测必须以 thinking 块开头的错误"""
        error = '{"error": {"message": "content must start with a thinking block"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_thinking_or_redacted(self, classifier: ErrorClassifier) -> None:
        """检测期望 thinking 或 redacted_thinking 的错误"""
        error = '{"error": {"message": "expected thinking or redacted_thinking"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_thinking_with_backticks(self, classifier: ErrorClassifier) -> None:
        """检测带反引号的 expected thinking 错误"""
        error = '{"error": {"message": "expected `thinking`"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_thinking_found_tool_use(self, classifier: ErrorClassifier) -> None:
        """检测 expected thinking, found xxx 错误（统一模式匹配）"""
        error = '{"error": {"message": "expected thinking, found tool_use"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_thinking_found_tool_use_backticks(
        self, classifier: ErrorClassifier
    ) -> None:
        """检测带反引号的 expected `thinking`, found xxx 错误"""
        error = '{"error": {"message": "expected `thinking`, found `tool_use`"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_thinking_found_text(self, classifier: ErrorClassifier) -> None:
        """检测 expected thinking, found text 错误"""
        error = '{"error": {"message": "expected thinking, found text"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_thinking_found_text_backticks(
        self, classifier: ErrorClassifier
    ) -> None:
        """检测带反引号的 expected `thinking`, found text 错误"""
        error = '{"error": {"message": "expected `thinking`, found `text`"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_redacted_thinking(self, classifier: ErrorClassifier) -> None:
        """检测 expected redacted_thinking 错误"""
        error = '{"error": {"message": "expected redacted_thinking, found text"}}'
        assert classifier._is_thinking_error(error) is True

    def test_detect_expected_redacted_thinking_backticks(
        self, classifier: ErrorClassifier
    ) -> None:
        """检测带反引号的 expected redacted_thinking 错误"""
        error = '{"error": {"message": "expected `redacted_thinking`, found `text`"}}'
        assert classifier._is_thinking_error(error) is True

    # === 真实错误响应测试 ===

    def test_real_claude_signature_error(self, classifier: ErrorClassifier) -> None:
        """测试真实的 Claude 签名错误响应"""
        error = """{
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "messages.2.content.0: invalid `signature` in `thinking` block: signature is for a different request"
            }
        }"""
        assert classifier._is_thinking_error(error) is True

    def test_real_claude_structure_error(self, classifier: ErrorClassifier) -> None:
        """测试真实的 Claude 结构错误响应"""
        error = """{
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "messages.1.content: when `thinking` is enabled, the first content block in an assistant turn containing `tool_use` blocks must start with a `thinking` or `redacted_thinking` block. expected thinking or redacted_thinking, found tool_use."
            }
        }"""
        assert classifier._is_thinking_error(error) is True

    # === 负面测试 ===

    def test_not_thinking_error_rate_limit(self, classifier: ErrorClassifier) -> None:
        """速率限制错误不应被识别为 thinking 错误"""
        error = '{"error": {"message": "rate limit exceeded"}}'
        assert classifier._is_thinking_error(error) is False

    def test_not_thinking_error_invalid_api_key(self, classifier: ErrorClassifier) -> None:
        """API Key 错误不应被识别为 thinking 错误"""
        error = '{"error": {"message": "invalid api key"}}'
        assert classifier._is_thinking_error(error) is False

    def test_not_thinking_error_model_not_found(self, classifier: ErrorClassifier) -> None:
        """模型不存在错误不应被识别为 thinking 错误"""
        error = '{"error": {"message": "model not found"}}'
        assert classifier._is_thinking_error(error) is False

    def test_not_thinking_error_empty(self, classifier: ErrorClassifier) -> None:
        """空错误文本不应被识别为 thinking 错误"""
        assert classifier._is_thinking_error("") is False
        assert classifier._is_thinking_error(None) is False

    def test_not_thinking_error_generic_signature(self, classifier: ErrorClassifier) -> None:
        """通用 signature 字样（非 thinking 相关）不应被误判"""
        # 这个应该不匹配，因为模式要求是 thinking 相关的 signature
        error = '{"error": {"message": "request signature mismatch"}}'
        assert classifier._is_thinking_error(error) is False

    # === 大小写不敏感测试 ===

    def test_case_insensitive_matching(self, classifier: ErrorClassifier) -> None:
        """测试大小写不敏感匹配"""
        error = '{"error": {"message": "INVALID `SIGNATURE` IN `THINKING` BLOCK"}}'
        assert classifier._is_thinking_error(error) is True

        error2 = '{"error": {"message": "Expected Thinking, Found Tool_Use"}}'
        assert classifier._is_thinking_error(error2) is True
