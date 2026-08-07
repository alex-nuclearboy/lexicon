# Application operations

## Health endpoints

The application provides two public health endpoints:

- `/health/live/` confirms that the application process can serve requests;
- `/health/ready/` confirms that the application can connect to the database.

The liveness endpoint does not query the database.

The readiness endpoint performs a minimal database query and returns HTTP 503
when the database is unavailable.

Health responses must not expose exception messages, package versions,
database configuration, environment variables, or internal application
details.

## Release procedure

Database migrations must be executed as a controlled one-off operation.

Before completing a production release:

    python manage.py migrate

Static files must be collected during the build or release process:

    python manage.py collectstatic --noinput

The Gunicorn start command must only start the application server. It must not
run migrations or collect static files.

Do not use a combined runtime command such as:

    python manage.py migrate && gunicorn ...

Running migrations from every application instance can cause concurrent
migration attempts when multiple instances start at the same time.

## Release verification

After deployment:

1. Confirm that `/health/live/` returns HTTP 200.
2. Confirm that `/health/ready/` returns HTTP 200.
3. Review the application startup logs.
4. Confirm that authentication and application access work normally.
