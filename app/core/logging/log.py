import logging
import sys
from typing import Any, Union

from loguru import logger

from app.settings import settings

# Create logs directory
log_dir = "logs"


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentation.

    This handler intercepts all log requests and
    passes them to loguru.p

    For more info see:
    https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        """
        Propagates logs to loguru.

        :param record: record to log.
        """
        try:
            level: Union[str, int] = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def is_access_log(record: Any) -> bool:
    """Filter for access logs."""
    return record["message"] == "access"


def configure_logging() -> None:  # pragma: no cover
    """Configures logging."""
    intercept_handler = InterceptHandler()

    logging.basicConfig(handlers=[intercept_handler], level=logging.NOTSET)

    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith("uvicorn."):
            logging.getLogger(logger_name).handlers = []

    # change handler for default uvicorn logger
    logging.getLogger("uvicorn").handlers = [intercept_handler]

    # set logs output, level and format
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level.value,
    )
    logger.add(
        f"{log_dir}/error.log",
        level="ERROR",
        rotation="1 day",
        retention="10 days",
    )
    logger.add(
        f"{log_dir}/interceptor.log",
        rotation="1 day",
        retention="10 days",
        filter=lambda r: r["extra"].get("event") == "interceptor",
    )
    access_log_format = (
        "{extra[client_ip]} - "
        '"{extra[method]} {extra[path]}?{extra[query_params]} HTTP/1.1" '
        "{extra[status_code]} - "
        "Headers: {extra[headers]} - "
        "Process Time: {extra[process_time]}"
    )

    logger.add(
        f"{log_dir}/access.log",
        filter=is_access_log,
        rotation="1 day",
        retention="10 days",
        format=access_log_format,
    )
    if settings.debug:
        logger.add(
            f"{log_dir}/debug.log",
            level="DEBUG",
            rotation="1 day",
            retention="10 days",
        )
