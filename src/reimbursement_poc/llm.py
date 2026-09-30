"""Explicit, optional OpenAI-compatible explanation adapter."""

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMRequestError(RuntimeError):
    """A provider request failed with a safe, actionable diagnostic."""


def _safe_detail(detail: str, api_key: str) -> str:
    detail = detail.replace(api_key, "[redacted]")
    detail = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", detail)
    detail = " ".join(detail.split())
    return detail[:500]


def _error_detail(error: HTTPError, api_key: str) -> str:
    body = error.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        detail = body or error.reason
    else:
        provider_error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(provider_error, dict):
            detail = provider_error.get("message", body)
        else:
            detail = body or error.reason
    return _safe_detail(str(detail), api_key)


def explain_decision(status: str, reason_codes: tuple[str, ...]) -> str:
    """Rewrite generic decision codes; never submit claim documents or identifiers."""
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise LLMRequestError("LLM_API_KEY is missing or empty.")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "").strip()
    if not model:
        raise LLMRequestError("LLM_MODEL is missing or empty.")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Explain a reimbursement workflow outcome in plain language. "
                    "Use only the supplied status and generic reason codes. Do not "
                    "infer facts, make a coverage decision, or mention fraud."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"status": status, "reason_codes": reason_codes}),
            },
        ],
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        detail = _error_detail(error, api_key)
        raise LLMRequestError(
            f"LLM provider returned HTTP {error.code} ({error.reason}): {detail}"
        ) from None
    except (URLError, TimeoutError) as error:
        detail = _safe_detail(str(error), api_key)
        raise LLMRequestError(f"Could not reach the LLM provider: {detail}") from None
    except json.JSONDecodeError as error:
        raise LLMRequestError(
            f"LLM provider returned invalid JSON: {_safe_detail(str(error), api_key)}"
        ) from None

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMRequestError(
            "LLM provider response did not contain choices[0].message.content. "
            "Check that the configured endpoint supports the OpenAI Chat "
            "Completions API."
        ) from None
    if not isinstance(content, str) or not content.strip():
        raise LLMRequestError("LLM provider returned an empty or non-text explanation.")
    return content.strip()
