# Database operations and recovery

## Database provider

The production PostgreSQL database is hosted by Neon.

The application uses two production connection strings:

- `DATABASE_URL` is the pooled Neon connection string used by the running
  Django application;
- `DIRECT_DATABASE_URL` is the direct Neon connection string used for schema
  migrations and other administrative operations.

Production connection strings are stored as environment variables in the
Koyeb Control Panel and must not be committed to the repository.

## Runtime connection

The production `DATABASE_URL` uses the Neon pooled endpoint. Its hostname
contains `-pooler`.

The production environment uses:

    DATABASE_CONN_MAX_AGE=60

This allows Django to reuse a database connection for up to 60 seconds instead
of opening a new connection for every request.

Django connection health checks are enabled when persistent connections are
used.

The application disables server-side cursors for the Neon pooled connection
because the pooler operates in transaction mode.

## Local development

Local development uses a direct PostgreSQL connection.

The local `.env` file uses:

    DATABASE_CONN_MAX_AGE=0

This closes the database connection at the end of each request and keeps local
database behaviour simple.

The repository `.env.example` also uses zero because it documents the local
development configuration rather than the production Koyeb configuration.

## Production environment variables

The following variables are configured in the Koyeb Control Panel:

    DATABASE_URL=<pooled Neon connection string>
    DIRECT_DATABASE_URL=<direct Neon connection string>
    DATABASE_CONN_MAX_AGE=60
    DATABASE_CONNECT_TIMEOUT=5

The pooled `DATABASE_URL` is used by the running web application.

The direct `DIRECT_DATABASE_URL` is used only for migrations, database dumps,
and other administrative operations that should not run through transaction
pooling.

Database passwords and complete connection strings must not be copied into
logs, documentation, issues, screenshots, or the Git repository.

## Schema migrations

Production migrations are run through the Koyeb Control Panel.

1. Open the Vocabio service in the Koyeb Control Panel.
2. Open the active running instance.
3. Open **Shell** or **Execute command**.
4. Run the migration using the direct database connection:

       env DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate

5. Confirm the migration state:

       env DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py showmigrations

6. Close the instance shell after the commands finish.

The application service continues to use the pooled `DATABASE_URL`. The
environment override applies only to the command being executed.

Migrations must not be run using the pooled connection string.

## Routine database maintenance

The following commands should be run through the shell of the active Koyeb
instance approximately once per month:

    python manage.py axes_reset_logs 30
    python manage.py clearsessions

The first command removes Django Axes access-log records older than 30 days.

The second command removes expired Django session records.

These commands use the regular pooled application connection because they
perform ordinary application-level database operations and do not require a
direct connection.

The global `axes_reset` command must not be used for routine maintenance
because it removes all current lockout and access records.

## Backup policy

Neon Backup & Restore is used as the production database recovery mechanism.

Before a destructive or irreversible database operation:

1. Open the production project in the Neon Console.
2. Open **Backup & Restore**.
3. Check the currently available point-in-time restore window.
4. Create a manual snapshot when the feature is available for the active
   Neon plan.
5. Record the time immediately before the operation.
6. Keep the recovery point until the migration and deployed application have
   been verified.

A recovery point should be prepared before:

- deleting or renaming database columns or tables;
- running an irreversible data migration;
- importing or deleting a large amount of data;
- making significant production schema changes.

The availability and retention of point-in-time history and snapshots depend
on the active Neon plan and project configuration.

## Restore procedure

A production restore must not be started until the required restore point has
been identified and checked.

1. Open the production project in the Neon Console.
2. Open **Backup & Restore**.
3. Select the production branch.
4. Select the required timestamp or snapshot.
5. Preview the data before confirming the restore.
6. Check important tables and records.
7. Restore to a separate branch first when that option is available.
8. Verify the restored schema and application data.
9. Obtain the pooled and direct connection strings for the restored branch if
   the connection strings changed.
10. Update `DATABASE_URL` and `DIRECT_DATABASE_URL` in the Koyeb Control
    Panel when necessary.
11. Redeploy the Vocabio service.
12. Run Django system checks and verify login and application data.
13. Keep the previous database branch until the restored deployment has been
    confirmed to work correctly.

A restore must not be considered complete until the application can connect,
authentication works, and important production records have been checked.
