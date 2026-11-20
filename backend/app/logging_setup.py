#Owner::ANIKET::ANHOTRA = MR.Panda
"""Log format and level. Logs are one JSON object per line for easy searching."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class JsonLogFormatter(logging.Formatter):
    """Formats each log record as a single line of JSON.

    Includes time, level, logger name, message and any exception text.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a JSON string.

        Non-serialisable values are converted to text so logging never crashes.
        """
        payload: dict[str, str] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(log_level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger at the given level.

    Unknown levels fall back to INFO. Calling it twice does not duplicate output.
    """
    level_name = log_level.upper() if log_level.upper() in VALID_LOG_LEVELS else "INFO"
    root_logger = logging.getLogger()
    root_logger.setLevel(level_name)
    for existing_handler in list(root_logger.handlers):
        if getattr(existing_handler, "_sitepay_handler", False):
            root_logger.removeHandler(existing_handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler._sitepay_handler = True  # type: ignore[attr-defined]
    root_logger.addHandler(handler)
