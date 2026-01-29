from src.api.handlers.gemini.stream_parser import GeminiStreamParser


def test_is_done_event_true_for_new_finish_reason_values() -> None:
    parser = GeminiStreamParser()
    event = {"candidates": [{"finishReason": "MALFORMED_FUNCTION_CALL"}]}
    assert parser.is_done_event(event) is True


def test_is_done_event_false_for_unspecified() -> None:
    parser = GeminiStreamParser()
    event = {"candidates": [{"finishReason": "FINISH_REASON_UNSPECIFIED"}]}
    assert parser.is_done_event(event) is False


def test_is_done_event_false_when_no_candidates_or_reason() -> None:
    parser = GeminiStreamParser()
    assert parser.is_done_event({}) is False
    assert parser.is_done_event({"candidates": [{}]}) is False

