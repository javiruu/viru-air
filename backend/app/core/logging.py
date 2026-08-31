import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Protocol

from app.core.request_context import get_client_event_id, get_correlation_id


_COOKIE_HEADER_PATTERN = re.compile(r"(?i)(\bcookie\s*:\s*)[^\r\n]+")
_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|access[_-]?key|token|secret|password|authorization|cookie|signature|x-amz-signature|x-amz-credential|x-amz-security-token)[\"']?\s*[:=]\s*(?:[\"']?(?:bearer|basic)\s+)?[\"']?)([^&\s,}\"']+)"
)


class _StringRenderable(Protocol):
    def __str__(self) -> str: ...


def redact_sensitive_text(value: _StringRenderable) -> str:
    """Redact common credentials, cookies, and signed-URL values before a log sink."""
    text = str(value)[:4000]
    text = _COOKIE_HEADER_PATTERN.sub(r"\1***", text)
    return _SENSITIVE_TEXT_PATTERN.sub(r"\1***", text)


def _default_log_file() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(log_dir, f"server-{stamp}.log")


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class SafeJsonFormatter(logging.Formatter):
    """Serialize log records as valid JSON without allowing message injection."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id() or "-",
            "client_event_id": getattr(record, "client_event_id", None) or get_client_event_id(),
            "message": redact_sensitive_text(record.getMessage()),
        }
        for record_key, payload_key in (
            ("hotel_execution_id", "execution_id"),
            ("hotel_provider_run_id", "provider_run_id"),
            ("hotel_alert_event_id", "alert_event_id"),
            ("hotel_correlation_id", "hotel_correlation_id"),
        ):
            value = getattr(record, record_key, None)
            if value:
                payload[payload_key] = redact_sensitive_text(value)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _suppress_secret_bearing_transport_logs() -> None:
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def configure_logging() -> None:
    level = logging.DEBUG if os.getenv("APP_ENV", "local") == "local" else logging.INFO
    log_file = os.getenv("LOG_FILE") or _default_log_file()
    logging.raiseExceptions = False
    formatter = SafeJsonFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.set_name("viru.logging.console")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.set_name("viru.logging.file")
    handlers: list[logging.Handler] = [console_handler, file_handler]
    correlation_filter = CorrelationIdFilter()
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(correlation_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in tuple(root_logger.handlers):
        if (handler.get_name() or "").startswith("viru.logging."):
            root_logger.removeHandler(handler)
            handler.close()
    for handler in handlers:
        root_logger.addHandler(handler)

    _suppress_secret_bearing_transport_logs()

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        for handler in handlers:
            logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
