import json
import logging

from app.core.logging import SafeJsonFormatter


def _format_message(message: str) -> tuple[str, dict[str, object]]:
    record = logging.LogRecord(
        name="app.worker.hotels_sweep",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-safe-log"
    rendered = SafeJsonFormatter().format(record)
    return rendered, json.loads(rendered)


def test_safe_json_formatter_escapes_quotes_and_newlines() -> None:
    rendered, payload = _format_message('provider failed: "quoted"\nforged=error')

    assert payload["message"] == 'provider failed: "quoted"\nforged=error'
    assert "\n" not in rendered
    assert json.loads(rendered) == payload


def test_safe_json_formatter_redacts_query_and_signed_url_secrets() -> None:
    rendered, payload = _format_message(
        "GET https://provider.test/hotel?api_key=api-secret&X-Amz-Signature=sig-secret failed"
    )

    message = str(payload["message"])
    assert "api-secret" not in rendered
    assert "sig-secret" not in rendered
    assert "api_key=***" in message
    assert "X-Amz-Signature=***" in message
    assert json.loads(rendered) == payload


def test_safe_json_formatter_redacts_bearer_and_cookie_values() -> None:
    rendered, payload = _format_message(
        "Authorization: Bearer bearer-secret Cookie: session=one; refresh=session-cookie-secret"
    )

    message = str(payload["message"])
    assert "bearer-secret" not in rendered
    assert "session-cookie-secret" not in rendered
    assert "session=one" not in rendered
    assert "Authorization: Bearer ***" in message
    assert "Cookie: ***" in message
    assert json.loads(rendered) == payload


def test_safe_json_formatter_keeps_structured_worker_payload_safe() -> None:
    worker_event = json.dumps(
        {
            "event": "hotel_sweep_failed",
            "error_message": "GET https://provider.test?token=worker-secret failed",
        }
    )

    rendered, payload = _format_message(worker_event)

    assert "worker-secret" not in rendered
    assert 'token=***' in str(payload["message"])
    assert json.loads(rendered) == payload
