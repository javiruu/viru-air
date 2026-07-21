import logging
import os
import sys
from datetime import datetime

from app.core.request_context import get_correlation_id


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


def _suppress_secret_bearing_transport_logs() -> None:
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def configure_logging() -> None:
    level = logging.DEBUG if os.getenv("APP_ENV", "local") == "local" else logging.INFO
    log_file = os.getenv("LOG_FILE") or _default_log_file()
    logging.raiseExceptions = False
    formatter = logging.Formatter(
        '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","correlation_id":"%(correlation_id)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    correlation_filter = CorrelationIdFilter()
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(correlation_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
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
