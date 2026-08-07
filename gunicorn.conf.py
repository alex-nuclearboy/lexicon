"""Gunicorn configuration for the Koyeb web service."""

# pylint: disable=invalid-name

import os

# Koyeb provides the application port through the PORT environment variable.
bind = f"0.0.0.0:{os.environ['PORT']}"

# Koyeb terminates TLS at its edge and forwards requests through its
# managed service network. The frontend proxy addresses are not fixed,
# so Gunicorn accepts secure proxy headers from the Koyeb frontend.
forwarded_allow_ips = "*"

# Use one process with two threads to limit memory usage while allowing
# two requests to be handled concurrently.
workers = 1
threads = 2
worker_class = "gthread"

# Restart workers that remain unresponsive for longer than 30 seconds
# and allow up to 30 seconds for graceful shutdown.
timeout = 30
graceful_timeout = 30

# Send privacy-conscious request logs to Koyeb without query strings,
# referrers, user agents, or client addresses.
accesslog = "-"
access_log_format = (
    '%(t)s "%(m)s %(U)s %(H)s" '
    "%(s)s %(b)s %(M)sms"
)

# Send Gunicorn warnings, errors, and critical messages to Koyeb.
errorlog = "-"
loglevel = "warning"
