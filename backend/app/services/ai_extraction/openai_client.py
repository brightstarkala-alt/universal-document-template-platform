"""
OpenAI client wrapper — Module 7, Stage C.

The only place in this module that imports the `openai` SDK — everything
else (candidates.py, prompts.py, scoring.py, keys.py) is pure and knows
nothing about OpenAI, so a future SDK upgrade only touches this file. No
multi-provider abstraction: this module calls OpenAI directly, on purpose.

Retries transient failures (rate limits, connection errors, 5xx — all
subclasses of `openai.APIError`) with bounded backoff. A response that
fails schema validation gets exactly one "repair" attempt where the
validation errors are fed back to the model, sharing the same bounded
attempt budget rather than retrying forever.
"""

import json
import time
from functools import lru_cache
from typing import Any

from openai import APIError, OpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import ExtractionValidationError, OpenAIUnavailableError
from app.core.logging import get_logger
from app.services.ai_extraction.prompts import SYSTEM_PROMPT, LLMBatchResponse

logger = get_logger(__name__)

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS_BASE = 1.5


@lru_cache
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY)


class BatchExtractionResult:
    """Validated model output for one batch, plus token usage."""

    def __init__(
        self, response: LLMBatchResponse, prompt_tokens: int, completion_tokens: int
    ) -> None:
        self.response = response
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


def extract_batch(
    *, client: OpenAI, model: str, user_payload: dict[str, Any]
) -> BatchExtractionResult:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload)},
    ]

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            completion = client.chat.completions.create(  # type: ignore[call-overload]
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=messages,
            )
        except APIError as exc:
            last_error = exc
            logger.warning(
                "OpenAI request failed; retrying",
                extra={"attempt": attempt, "error": str(exc)},
            )
            if attempt < _MAX_ATTEMPTS:
                _wait_before_retry(attempt)
            continue

        content = completion.choices[0].message.content or "{}"
        usage = completion.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        try:
            parsed = LLMBatchResponse.model_validate_json(content)
            return BatchExtractionResult(parsed, prompt_tokens, completion_tokens)
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "LLM response failed schema validation; attempting a repair retry",
                extra={"attempt": attempt, "errors": exc.errors()},
            )
            if attempt < _MAX_ATTEMPTS:
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response did not match the required JSON "
                            f"shape. Validation errors: {exc.errors()}. Respond again "
                            "with ONLY the corrected JSON object."
                        ),
                    }
                )
            continue

    if isinstance(last_error, ValidationError):
        raise ExtractionValidationError(
            "The model's response did not match the expected extraction schema.",
            details={"errors": last_error.errors()},
        ) from last_error
    raise OpenAIUnavailableError(
        "OpenAI did not return a usable response after retrying."
    ) from last_error


def _wait_before_retry(attempt: int) -> None:
    time.sleep(_BACKOFF_SECONDS_BASE**attempt)
