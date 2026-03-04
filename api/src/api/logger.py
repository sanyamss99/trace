import json
import logging
from datetime import UTC, datetime

from api.config import settings
from api.request_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Inject the current request ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", ""),
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


logger = logging.getLogger("trace")
logger.setLevel(settings.log_level.upper())

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())

    if settings.is_debug:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s [%(request_id)s] %(message)s")
        )
    else:
        handler.setFormatter(JsonFormatter())

    logger.addHandler(handler)
