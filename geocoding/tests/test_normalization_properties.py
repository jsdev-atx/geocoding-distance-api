from hypothesis import given
from hypothesis import strategies as st

from geocoding.services import _normalize_query

non_whitespace_only_text = st.text(min_size=1).filter(lambda s: s.strip())


class TestNormalizationOutputInvariants:

    @given(query=non_whitespace_only_text)
    def test_output_is_lowercase(self, query: str) -> None:
        result = _normalize_query(query)
        assert result == result.lower()

    @given(query=non_whitespace_only_text)
    def test_no_leading_or_trailing_whitespace(self, query: str) -> None:
        result = _normalize_query(query)
        assert result == result.strip()

    @given(query=non_whitespace_only_text)
    def test_no_consecutive_whitespace(self, query: str) -> None:
        result = _normalize_query(query)
        assert "  " not in result


class TestNormalizationIdempotency:

    @given(query=non_whitespace_only_text)
    def test_idempotent(self, query: str) -> None:
        once = _normalize_query(query)
        twice = _normalize_query(once)
        assert once == twice
