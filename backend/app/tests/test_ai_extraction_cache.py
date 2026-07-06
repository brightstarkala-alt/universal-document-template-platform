from types import SimpleNamespace
from typing import Any

from app.services import ai_extraction_service


class _FakeSupabaseQuery:
    """Minimal stand-in for the chainable Supabase query builder: every
    chain method returns `self` and `execute()` yields the pre-set data,
    regardless of how many `.eq(...)` filters were chained."""

    def __init__(self, data: Any) -> None:
        self._data = data

    def table(self, _name: str) -> "_FakeSupabaseQuery":
        return self

    def select(self, *_args: Any) -> "_FakeSupabaseQuery":
        return self

    def eq(self, *_args: Any) -> "_FakeSupabaseQuery":
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> "_FakeSupabaseQuery":
        return self

    def limit(self, *_args: Any) -> "_FakeSupabaseQuery":
        return self

    def maybe_single(self) -> "_FakeSupabaseQuery":
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self._data)


def _row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "extraction-1",
        "company_id": "company-1",
        "file_id": "file-1",
        "parsed_document_id": "parsed-1",
        "version": 1,
        "schema_version": "1.0",
        "source_checksum_sha256": "checksum-abc",
        "model": "gpt-4o-mini",
        "prompt_version": "2026-07-06.1",
        "status": "completed",
        "storage_path": "x.json",
        "field_count": 1,
        "table_count": 0,
        "low_confidence_count": 0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "duration_ms": 12.0,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def test_find_cached_extraction_returns_row_when_match_exists() -> None:
    client = _FakeSupabaseQuery(_row())

    result = ai_extraction_service._find_cached_extraction(
        client, file_id="file-1", source_checksum_sha256="checksum-abc", model="gpt-4o-mini"
    )

    assert result is not None
    assert result.id == "extraction-1"


def test_find_cached_extraction_returns_none_when_no_match() -> None:
    client = _FakeSupabaseQuery(None)

    result = ai_extraction_service._find_cached_extraction(
        client, file_id="file-1", source_checksum_sha256="checksum-abc", model="gpt-4o-mini"
    )

    assert result is None


def test_next_version_returns_one_when_no_existing_rows() -> None:
    client = _FakeSupabaseQuery(None)

    assert ai_extraction_service._next_version(client, file_id="file-1") == 1


def test_next_version_increments_existing_max() -> None:
    client = _FakeSupabaseQuery({"version": 3})

    assert ai_extraction_service._next_version(client, file_id="file-1") == 4
