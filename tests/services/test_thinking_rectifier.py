"""
ThinkingRectifier 单元测试

测试 Thinking 整流器的核心功能：
- 移除 thinking 和 redacted_thinking 块
- 移除非 thinking 块上的 signature 字段
- 条件删除顶层 thinking 参数
"""

import copy

import pytest

from src.services.message.thinking_rectifier import ThinkingRectifier


class TestRectifyBasic:
    """测试基本整流功能"""

    def test_empty_request_body(self) -> None:
        """空请求体应返回原值"""
        result, modified = ThinkingRectifier.rectify({})
        assert result == {}
        assert modified is False

    def test_none_request_body(self) -> None:
        """None 请求体应返回原值"""
        result, modified = ThinkingRectifier.rectify(None)  # type: ignore
        assert result is None
        assert modified is False

    def test_no_messages(self) -> None:
        """无 messages 字段应返回原值"""
        body = {"model": "claude-3-opus"}
        result, modified = ThinkingRectifier.rectify(body)
        assert result == body
        assert modified is False

    def test_empty_messages(self) -> None:
        """空 messages 列表应返回原值"""
        body = {"model": "claude-3-opus", "messages": []}
        result, modified = ThinkingRectifier.rectify(body)
        assert result["messages"] == []
        assert modified is False


class TestRemoveThinkingBlocks:
    """测试移除 thinking 块"""

    def test_remove_thinking_block(self) -> None:
        """应移除 thinking 块"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "...", "signature": "abc"},
                        {"type": "text", "text": "Hello"},
                    ],
                }
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        content = result["messages"][0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"

    def test_remove_redacted_thinking_block(self) -> None:
        """应移除 redacted_thinking 块"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": "..."},
                        {"type": "text", "text": "Hello"},
                    ],
                }
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        content = result["messages"][0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"

    def test_remove_multiple_thinking_blocks(self) -> None:
        """应移除多个 thinking 块"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "thought 1"},
                        {"type": "text", "text": "response 1"},
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": "..."},
                        {"type": "text", "text": "response 2"},
                    ],
                },
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        assert len(result["messages"][0]["content"]) == 1
        assert len(result["messages"][1]["content"]) == 1


class TestRemoveSignatureField:
    """测试移除 signature 字段"""

    def test_remove_signature_from_text_block(self) -> None:
        """应从 text 块移除 signature 字段"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Hello", "signature": "should_remove"},
                    ],
                }
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        block = result["messages"][0]["content"][0]
        assert "signature" not in block
        assert block["text"] == "Hello"

    def test_remove_signature_from_tool_use_block(self) -> None:
        """应从 tool_use 块移除 signature 字段"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool_1",
                            "name": "search",
                            "input": {},
                            "signature": "should_remove",
                        },
                    ],
                }
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        block = result["messages"][0]["content"][0]
        assert "signature" not in block
        assert block["id"] == "tool_1"


class TestTopLevelThinkingParam:
    """测试顶层 thinking 参数处理"""

    def test_remove_thinking_param_when_tool_use_without_thinking_prefix(self) -> None:
        """整流后有 tool_use 但无 thinking 前缀时应移除 thinking 参数"""
        body = {
            "thinking": {"type": "enabled", "budget_tokens": 10000},
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
                    ],
                }
            ],
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        assert "thinking" not in result
        # tool_use 应保留
        assert result["messages"][0]["content"][0]["type"] == "tool_use"

    def test_keep_thinking_param_when_no_tool_use(self) -> None:
        """整流后无 tool_use 时应保留 thinking 参数"""
        body = {
            "thinking": {"type": "enabled", "budget_tokens": 10000},
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "text", "text": "Hello"},
                    ],
                }
            ],
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        # thinking 参数应保留（只移除了 thinking 块）
        assert "thinking" in result
        assert result["thinking"]["type"] == "enabled"

    def test_keep_thinking_param_when_disabled(self) -> None:
        """thinking 参数未启用时应保留"""
        body = {
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
                    ],
                }
            ],
        }
        result, modified = ThinkingRectifier.rectify(body)

        # 无 thinking 块需要移除，thinking 参数也不需要移除
        assert modified is False
        assert result["thinking"]["type"] == "disabled"


class TestEdgeCases:
    """测试边界情况"""

    def test_non_dict_message_preserved(self) -> None:
        """非 dict 消息应保留"""
        body = {
            "messages": [
                "string message",  # 非 dict
                {"role": "user", "content": "Hello"},
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert result["messages"][0] == "string message"
        assert modified is False

    def test_string_content_preserved(self) -> None:
        """字符串 content 应保留"""
        body = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert result["messages"][1]["content"] == "Hi there"
        assert modified is False

    def test_non_dict_block_in_content_preserved(self) -> None:
        """content 中的非 dict 块应保留"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        "string block",  # 非 dict
                        {"type": "text", "text": "Hello"},
                    ],
                }
            ]
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert result["messages"][0]["content"][0] == "string block"
        assert modified is False

    def test_empty_content_after_rectify_logs_warning(self) -> None:
        """整流后 assistant 消息 content 为空时应记录警告（不抛异常）"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "only thinking"},
                    ],
                }
            ]
        }
        # 应该不抛异常
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        # content 应为空列表
        assert result["messages"][0]["content"] == []

    def test_deep_copy_does_not_modify_original(self) -> None:
        """深拷贝应保护原始数据不被修改"""
        original = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "text", "text": "Hello"},
                    ],
                }
            ]
        }
        original_copy = copy.deepcopy(original)

        ThinkingRectifier.rectify(original)

        # 原始数据不应被修改
        assert original == original_copy


class TestLastAssistantCheck:
    """测试只检查最后一条 assistant 消息的逻辑"""

    def test_only_last_assistant_matters_for_thinking_removal(self) -> None:
        """只有最后一条 assistant 消息决定是否移除 thinking 参数"""
        body = {
            "thinking": {"type": "enabled", "budget_tokens": 10000},
            "messages": [
                # 第一条 assistant 有 tool_use
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
                    ],
                },
                {"role": "user", "content": "result"},
                # 最后一条 assistant 无 tool_use
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "text", "text": "Final answer"},
                    ],
                },
            ],
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        # thinking 参数应保留（最后一条 assistant 无 tool_use）
        assert "thinking" in result

    def test_last_assistant_with_tool_use_removes_thinking(self) -> None:
        """最后一条 assistant 有 tool_use 时应移除 thinking 参数"""
        body = {
            "thinking": {"type": "enabled", "budget_tokens": 10000},
            "messages": [
                # 第一条 assistant 无 tool_use
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "text", "text": "thinking..."},
                    ],
                },
                {"role": "user", "content": "continue"},
                # 最后一条 assistant 有 tool_use
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "..."},
                        {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
                    ],
                },
            ],
        }
        result, modified = ThinkingRectifier.rectify(body)

        assert modified is True
        # thinking 参数应被移除
        assert "thinking" not in result
