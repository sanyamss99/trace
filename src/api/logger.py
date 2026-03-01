import logging

from src.api.config import settings

logger = logging.getLogger("trace")
logger.setLevel(settings.log_level)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s"))
    logger.addHandler(handler)
