# Logging and data retention

## Local development

Vocabio writes coloured application and audit logs to the console.

Local logs are also written to `logs/vocabio.log`. The active file is limited
to 5 MB and three rotated backup files are retained. The maximum local log
storage is therefore approximately 20 MB.

The `logs` directory is excluded from version control.

## Production

Vocabio does not write log files inside the production container.

Django, application, audit, and Gunicorn logs are written to standard output
or standard error and collected by Koyeb.

The retention period is controlled by the active Koyeb plan. No external log
exporter or third-party application monitoring service is currently
configured.

Production logs are available only to users who have access to the Koyeb
project.

## Logged data

Security-related application logs may contain:

- user IDs;
- usernames when required to analyse an unauthenticated lockout;
- client IP addresses;
- requested paths;
- authentication and access outcomes;
- lockout retry periods.

Passwords, submitted form contents, session identifiers, CSRF tokens, and
secret keys must not be written to application logs.

## Request logs

Gunicorn records one access-log entry for every HTTP request. The access log
contains the request method, path, protocol, response status, response size,
and duration.

Query strings, referrers, user agents, and client IP addresses are omitted
from the Gunicorn access-log format.

## Django Axes records

Django Axes uses the application PostgreSQL database to store authentication
attempts and access records.

Successful authentication clears accumulated failures according to the
configured Axes policy.

Access-log records older than 30 days can be removed manually with:

    poetry run python manage.py axes_reset_logs 30

A lockout for a specific IP address can be cleared with:

    poetry run python manage.py axes_reset_ip <ip-address>

A lockout for a specific username can be cleared with:

    poetry run python manage.py axes_reset_username <username>

A lockout for one IP address and username combination can be cleared with:

    poetry run python manage.py axes_reset_ip_username <ip-address> <username>

The global `axes_reset` command must not be used as routine cleanup because it
removes all current lockout and access records.
