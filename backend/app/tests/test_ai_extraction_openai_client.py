import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError

from app.core.exceptions import ExtractionValidationError, OpenAIUnavailableError
from app.services.ai_extraction.openai_client import extract_batch

VALID_RESPONSE = {
    "fields": [
        {
            "unit_index": 0,
            "block_index": 0,
            "run_index": 0,
            "display_label": "Invoice Number",
            "machine_key": "invoice_number",
            "type": "identifier",
            "sample_value": "INV-1001",
            "confidence": 0.9,
            "accepted": True,
        }
    ],
    "tables": [],
}


def _completion(content: str, prompt_tokens: int = 10, completion_tokens: int = 5) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    completion.usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return completion


def test_extract_batch_returns_validated_response_on_first_try() -> None:
    client = MagicMock()
    client.chat.completions.create.return_value = _completion(json.dumps(VALID_RESPONSE))

    with patch("app.services.ai_extraction.openai_client._wait_before_retry"):
        result = extract_batch(client=client, model="gpt-4o-mini", user_payload={"units": []})

    assert len(result.response.fields) == 1
    assert result.response.fields[0].machine_key == "invoice_number"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5
    assert client.chat.completions.create.call_count == 1


def test_extract_batch_repairs_after_one_invalid_response() -> None:
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _completion(json.dumps({"fields": [{"missing": "required fields"}], "tables": []})),
        _completion(json.dumps(VALID_RESPONSE)),
    ]

    with patch("app.services.ai_extraction.openai_client._wait_before_retry"):
        result = extract_batch(client=client, model="gpt-4o-mini", user_payload={"units": []})

    assert len(result.response.fields) == 1
    assert client.chat.completions.create.call_count == 2


def test_extract_batch_raises_extraction_validation_error_after_exhausting_retries() -> None:
    client = MagicMock()
    client.chat.completions.create.return_value = _completion(
        json.dumps({"fields": [{"unit_index": 0}], "tables": []})
    )

    with (
        patch("app.services.ai_extraction.openai_client._wait_before_retry"),
        pytest.raises(ExtractionValidationError),
    ):
        extract_batch(client=client, model="gpt-4o-mini", user_payload={"units": []})


def test_extract_batch_raises_openai_unavailable_after_exhausting_retries() -> None:
    client = MagicMock()
    client.chat.completions.create.side_effect = APIError(
        "rate limited", request=MagicMock(), body=None
    )

    with (
        patch("app.services.ai_extraction.openai_client._wait_before_retry"),
        pytest.raises(OpenAIUnavailableError),
    ):
        extract_batch(client=client, model="gpt-4o-mini", user_payload={"units": []})

    assert client.chat.completions.create.call_count == 3
