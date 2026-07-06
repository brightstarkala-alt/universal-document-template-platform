from app.services.ai_extraction.keys import dedupe_machine_keys, normalize_machine_key


def test_normalize_machine_key_lowercases_and_snake_cases() -> None:
    assert normalize_machine_key("Invoice Number") == "invoice_number"


def test_normalize_machine_key_collapses_non_alnum_runs() -> None:
    assert normalize_machine_key("Date/Time (UTC)") == "date_time_utc"


def test_normalize_machine_key_strips_leading_trailing_separators() -> None:
    assert normalize_machine_key("  Total:  ") == "total"


def test_normalize_machine_key_falls_back_when_empty() -> None:
    assert normalize_machine_key("   ") == "field"
    assert normalize_machine_key("...") == "field"


def test_normalize_machine_key_prefixes_when_starting_with_digit() -> None:
    assert normalize_machine_key("123abc") == "field_123abc"


def test_dedupe_machine_keys_appends_suffix_to_repeats() -> None:
    assert dedupe_machine_keys(["date", "date", "total", "date"]) == [
        "date",
        "date_2",
        "total",
        "date_3",
    ]


def test_dedupe_machine_keys_leaves_unique_keys_untouched() -> None:
    assert dedupe_machine_keys(["a", "b", "c"]) == ["a", "b", "c"]
