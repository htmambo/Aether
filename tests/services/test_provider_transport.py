from dataclasses import dataclass


from src.services.provider.transport import build_provider_url


@dataclass
class _DummyEndpoint:
    base_url: str
    api_format: str
    custom_path: str | None = None


def test_gemini_stream_adds_alt_sse_and_drops_key_query_param() -> None:
    endpoint = _DummyEndpoint(
        base_url="https://generativelanguage.googleapis.com",
        api_format="GEMINI",
    )

    url = build_provider_url(
        endpoint,  # type: ignore[arg-type] - test stub
        query_params={"key": "SECRET"},
        path_params={"model": "gemini-1.5-pro"},
        is_stream=True,
    )

    assert url.startswith(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:streamGenerateContent"
    )
    assert "key=" not in url
    assert "alt=sse" in url


def test_gemini_stream_does_not_override_existing_alt() -> None:
    endpoint = _DummyEndpoint(
        base_url="https://generativelanguage.googleapis.com",
        api_format="GEMINI",
    )

    url = build_provider_url(
        endpoint,  # type: ignore[arg-type] - test stub
        query_params={"alt": "json"},
        path_params={"model": "gemini-1.5-pro"},
        is_stream=True,
    )

    assert "alt=json" in url
    assert "alt=sse" not in url


def test_gemini_non_stream_does_not_add_alt() -> None:
    endpoint = _DummyEndpoint(
        base_url="https://generativelanguage.googleapis.com",
        api_format="GEMINI",
    )

    url = build_provider_url(
        endpoint,  # type: ignore[arg-type] - test stub
        path_params={"model": "gemini-1.5-pro"},
        is_stream=False,
    )

    assert url.endswith("/v1beta/models/gemini-1.5-pro:generateContent")
    assert "alt=" not in url

