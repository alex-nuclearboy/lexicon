#!/usr/bin/env python
"""Provide Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings",
    )

    try:
        # Keep the import delayed to provide a clearer startup error.
        # pylint: disable-next=import-outside-toplevel
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
