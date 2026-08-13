import logging
from logging.handlers import BufferingHandler

from app.core.logging import _suppress_secret_bearing_transport_logs, configure_logging


def test_secret_bearing_transport_urls_are_not_logged_at_debug() -> None:
    transport_logger = logging.getLogger("urllib3.connectionpool")
    previous_level = transport_logger.level
    try:
        transport_logger.setLevel(logging.DEBUG)
        _suppress_secret_bearing_transport_logs()
        assert transport_logger.getEffectiveLevel() >= logging.WARNING
    finally:
        transport_logger.setLevel(previous_level)


def test_configure_logging_preserves_preinstalled_root_handlers(
    monkeypatch,
    tmp_path,
) -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    capture_handler = BufferingHandler(capacity=100)
    root_logger.addHandler(capture_handler)
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "backend.log"))

    try:
        configure_logging()
        logging.getLogger("app.hotels.test").warning("capture must remain available")
        assert [record.getMessage() for record in capture_handler.buffer] == [
            "capture must remain available"
        ]
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            if handler not in original_handlers:
                handler.close()
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)
