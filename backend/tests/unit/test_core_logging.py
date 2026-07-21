import logging

from app.core.logging import _suppress_secret_bearing_transport_logs


def test_secret_bearing_transport_urls_are_not_logged_at_debug() -> None:
    transport_logger = logging.getLogger("urllib3.connectionpool")
    previous_level = transport_logger.level
    try:
        transport_logger.setLevel(logging.DEBUG)
        _suppress_secret_bearing_transport_logs()
        assert transport_logger.getEffectiveLevel() >= logging.WARNING
    finally:
        transport_logger.setLevel(previous_level)
