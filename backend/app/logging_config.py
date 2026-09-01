"""Structured (JSON) logging setup — Phase 17.

Deliberately stdlib-only (no extra dependency): one line per log record,
each a real JSON object with timestamp/service/level/logger/message, safe
to ingest with any log aggregator. LOG_LEVEL and LOG_SERVICE_NAME are
configurable via environment variable.

Never logs secrets: passwords, API keys, or full database connection
strings. app.database intentionally never exposes DATABASE_URL for this
reason — log the dialect/host shape, not the credential-bearing URL.
"""
import json
import logging
import os
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(service_name: str = "bhusuraksha-backend") -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    service_name = os.getenv("LOG_SERVICE_NAME", service_name)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service_name))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
