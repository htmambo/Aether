from __future__ import annotations

from types import SimpleNamespace

from src.services.cache.aware_scheduler import ProviderCandidate


def _make_candidate(
    *,
    provider_priority: int | None,
    internal_priority: int | None,
    provider_id: str,
    endpoint_id: str,
    key_id: str,
) -> ProviderCandidate:
    provider = SimpleNamespace(id=provider_id, name="p", provider_priority=provider_priority)
    endpoint = SimpleNamespace(id=endpoint_id)
    key = SimpleNamespace(id=key_id, internal_priority=internal_priority)
    return ProviderCandidate(provider=provider, endpoint=endpoint, key=key)  # type: ignore[arg-type]


def test_provider_candidate_is_orderable() -> None:
    c1 = _make_candidate(
        provider_priority=1,
        internal_priority=1,
        provider_id="p1",
        endpoint_id="e1",
        key_id="k1",
    )
    c2 = _make_candidate(
        provider_priority=1,
        internal_priority=2,
        provider_id="p1",
        endpoint_id="e1",
        key_id="k2",
    )

    assert c1 < c2
    assert sorted([c2, c1]) == [c1, c2]


def test_provider_candidate_can_break_ties_in_tuple_sort() -> None:
    c1 = _make_candidate(
        provider_priority=1,
        internal_priority=1,
        provider_id="p1",
        endpoint_id="e1",
        key_id="k1",
    )
    c2 = _make_candidate(
        provider_priority=1,
        internal_priority=2,
        provider_id="p1",
        endpoint_id="e1",
        key_id="k2",
    )

    # When the first tuple element ties, Python will compare the second element.
    # This should not raise:
    # TypeError: '<' not supported between instances of 'ProviderCandidate' and 'ProviderCandidate'
    pairs = [(0, c2), (0, c1)]
    assert [c for _score, c in sorted(pairs)] == [c1, c2]


def test_provider_candidate_none_priorities_sort_last() -> None:
    c1 = _make_candidate(
        provider_priority=1,
        internal_priority=None,
        provider_id="p1",
        endpoint_id="e1",
        key_id="k1",
    )
    c2 = _make_candidate(
        provider_priority=None,
        internal_priority=None,
        provider_id="p2",
        endpoint_id="e1",
        key_id="k2",
    )

    assert sorted([c2, c1]) == [c1, c2]
