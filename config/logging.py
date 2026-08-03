"""Centralised logging configuration for Vocabio."""

from pathlib import Path
from typing import Any


LOG_FILE_NAME = "vocabio.log"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 3


def build_logging_config(
    *,
    base_dir: Path,
    debug: bool,
) -> dict[str, Any]:
    """Build logging settings for local development and production.

    Local development receives coloured console output and a rotating log
    file. Production receives plain console output only. Routine application
    events are suppressed in production, while audit events remain available
    at the ``INFO`` level.

    Args:
        base_dir: The project root containing ``manage.py``.
        debug: Whether Django debug mode is enabled.

    Returns:
        A dictionary compatible with Django's ``LOGGING`` setting.
    """
    console_formatter = "colour" if debug else "plain"
    application_level = "DEBUG" if debug else "WARNING"
    django_level = "INFO" if debug else "WARNING"

    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": application_level,
            "formatter": console_formatter,
        },
        "audit_console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": console_formatter,
        },
    }

    application_handlers = ["console"]
    audit_handlers = ["audit_console"]

    if debug:
        log_directory = base_dir / "logs"
        log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "file",
            "filename": log_directory / LOG_FILE_NAME,
            "maxBytes": LOG_FILE_MAX_BYTES,
            "backupCount": LOG_FILE_BACKUP_COUNT,
            "encoding": "utf-8",
            "delay": True,
        }

        application_handlers.append("file")
        audit_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "colour": {
                "()": "colorlog.ColoredFormatter",
                "format": (
                    "%(asctime)s | "
                    "%(log_color)s%(levelname)-8s%(reset)s | "
                    "%(name)s | %(message)s"
                ),
                "datefmt": "%H:%M:%S",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                "reset": True,
            },
            "plain": {
                "format": (
                    "{asctime} | {levelname:<8} | "
                    "{name} | {message}"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "style": "{",
            },
            "file": {
                "format": (
                    "{asctime} | {levelname:<8} | "
                    "{name} | {message}"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "style": "{",
            },
        },
        "handlers": handlers,
        "root": {
            "handlers": application_handlers,
            "level": "WARNING",
        },
        "loggers": {
            "vocabio": {
                "handlers": application_handlers,
                "level": application_level,
                "propagate": False,
            },
            "vocabio.audit": {
                "handlers": audit_handlers,
                "level": "INFO",
                "propagate": False,
            },
            "django": {
                "handlers": application_handlers,
                "level": django_level,
                "propagate": False,
            },
            "django.server": {
                "handlers": application_handlers,
                "level": django_level,
                "propagate": False,
            },
        },
    }
