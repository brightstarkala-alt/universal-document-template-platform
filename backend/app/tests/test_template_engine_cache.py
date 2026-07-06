from types import SimpleNamespace
from typing import Any

from app.services import template_engine_service


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
        "id": "template-1",
        "company_id": "company-1",
        "file_id": "file-1",
        "source_ai_extraction_id": "extraction-1",
        "source_parsed_document_id": "parsed-1",
        "version": 1,
        "schema_version": "1.0",
        "generator_version": "1.0",
        "status": "completed",
        "storage_path": "x.json",
        "field_count": 1,
        "section_count": 0,
        "asset_count": 0,
        "page_count": 1,
        "duration_ms": 12.0,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def test_find_cached_template_returns_row_when_match_exists() -> None:
    client = _FakeSupabaseQuery(_row())

    result = template_engine_service._find_cached_template(
        client, file_id="file-1", source_ai_extraction_id="extraction-1", generator_version="1.0"
    )

    assert result is not None
    assert result.id == "template-1"


def test_find_cached_template_returns_none_when_no_match() -> None:
    client = _FakeSupabaseQuery(None)

    result = template_engine_service._find_cached_template(
        client, file_id="file-1", source_ai_extraction_id="extraction-1", generator_version="1.0"
    )

    assert result is None


def test_next_version_returns_one_when_no_existing_rows() -> None:
    client = _FakeSupabaseQuery(None)

    assert template_engine_service._next_version(client, file_id="file-1") == 1


def test_next_version_increments_existing_max() -> None:
    client = _FakeSupabaseQuery({"version": 3})

    assert template_engine_service._next_version(client, file_id="file-1") == 4
