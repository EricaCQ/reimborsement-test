import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from reimbursement_poc import llm
from reimbursement_poc.llm import LLMRequestError


def configure_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "test-model")


def test_explanation_uses_openai_compatible_chat_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_llm(monkeypatch)

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://example.test/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer test-api-key"
        assert timeout == 20
        payload = json.loads(request.data)
        assert payload["model"] == "test-model"
        assert payload["messages"][1]["content"] == (
            '{"status": "NEEDS_INFORMATION", "reason_codes": '
            '["required_document_fields_missing"]}'
        )
        assert "temperature" not in payload
        return BytesIO(
            b'{"choices":[{"message":{"content":"Please provide the missing field."}}]}'
        )

    monkeypatch.setattr(llm, "urlopen", fake_urlopen)

    assert (
        llm.explain_decision("NEEDS_INFORMATION", ("required_document_fields_missing",))
        == "Please provide the missing field."
    )


def test_provider_http_error_has_sanitized_actionable_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_llm(monkeypatch)
    body = json.dumps(
        {"error": {"message": "Model test-model is not available to this account"}}
    ).encode()

    def failed_request(request, timeout):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=BytesIO(body),
        )

    monkeypatch.setattr(llm, "urlopen", failed_request)

    with pytest.raises(LLMRequestError, match="HTTP 400") as error:
        llm.explain_decision("APPROVED", ("procedure_covered",))

    assert "not available to this account" in str(error.value)
    assert "test-api-key" not in str(error.value)


def test_empty_credentials_fail_with_configuration_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "test-model")

    with pytest.raises(LLMRequestError, match="LLM_API_KEY"):
        llm.explain_decision("APPROVED", ())

    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(LLMRequestError, match="LLM_MODEL"):
        llm.explain_decision("APPROVED", ())


def test_provider_http_error_redacts_api_key_from_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_llm(monkeypatch)
    body = json.dumps(
        {"error": {"message": "Unexpected value test-api-key from provider"}}
    ).encode()

    def failed_request(request, timeout):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=BytesIO(body),
        )

    monkeypatch.setattr(llm, "urlopen", failed_request)

    with pytest.raises(LLMRequestError) as error:
        llm.explain_decision("APPROVED", ())

    assert "[redacted]" in str(error.value)
    assert "test-api-key" not in str(error.value)
