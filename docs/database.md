[← Back to project overview](../README.md)

# Database operations and recovery

## Database provider

The production PostgreSQL database is hosted by Neon.

The project uses two types of production database connection:

- a pooled connection for the running Django application;
- a direct connection for schema migrations and administrative database
  operations.

Connection strings are stored as environment variables or encrypted secrets
and must not be committed to the repository.

## Runtime connection

The Django application running on Koyeb uses the pooled Neon connection through
the `DATABASE_URL` environment variable.

The pooled endpoint hostname contains `-pooler`.

Persistent database connections are enabled in production so that Django can
reuse a connection for up to 60 seconds. Connection health checks verify that
a persistent connection remains usable before it is reused.

A database connection attempt times out after five seconds.

Server-side cursors are disabled for the pooled connection because the Neon
pooler operates in transaction mode.

## Local development

The local PostgreSQL database runs in Docker using the repository Docker
Compose configuration.

The local `.env` file contains the PostgreSQL container settings:

```text
POSTGRES_DB=vocabio
POSTGRES_USER=vocabio
POSTGRES_PASSWORD=<local database password>
```

Django connects to the local database through a direct PostgreSQL connection:

```text
DATABASE_URL=postgresql://vocabio:<local database password>@127.0.0.1:5432/vocabio
DATABASE_CONN_MAX_AGE=0
DATABASE_CONNECT_TIMEOUT=5
```

A connection age of zero closes the database connection at the end of each
request and keeps local database behaviour simple.

The connection timeout limits how long Django waits when establishing a
connection to PostgreSQL.

The values used in `DATABASE_URL` must match the PostgreSQL credentials
configured for the Docker container.

The repository `.env.example` documents the same local database configuration
using placeholder credentials.

## Production configuration

### Koyeb

The following variables are configured in the Koyeb Control Panel:

```text
DATABASE_URL=<pooled Neon connection string>
DIRECT_DATABASE_URL=<direct Neon connection string>
DATABASE_CONN_MAX_AGE=60
DATABASE_CONNECT_TIMEOUT=5
```

The running Django application uses the pooled `DATABASE_URL`.

The direct `DIRECT_DATABASE_URL` is retained for administrative database
operations.

Database passwords and complete connection strings must not be copied into
logs, documentation, issues, screenshots, or the Git repository.

### GitHub Actions

The same direct Neon connection string is stored as the following encrypted
GitHub Actions secret:

```text
PRODUCTION_DATABASE_URL
```

It is used by the manual migration workflow:

```text
.github/workflows/production-migrations.yml
```

The secret must contain the direct Neon connection string rather than the
pooled connection string.

## Schema migrations

Production migrations are applied manually through GitHub Actions.

When a release contains new migration files:

1. Create, review, and apply the migrations locally:

   ```text
   poetry run python manage.py makemigrations
   poetry run python manage.py migrate --plan
   poetry run python manage.py migrate
   ```

2. Run the project tests and quality checks.

3. Commit and push the release branch.

4. Wait for the regular CI workflow to complete successfully.

5. Open **Actions** in the GitHub repository.

6. Select **Production migrations**.

7. Select **Run workflow** and choose the release branch containing the
   migration files.

8. Enter the confirmation value:

   ```text
   MIGRATE
   ```

9. Run the workflow and confirm that it completes successfully.

10. Merge the release branch into `main`.

11. Verify the resulting Koyeb deployment.

After deployment, check:

```text
/health/live/
/health/ready/
```

Also verify login and the functionality affected by the schema change.

The branch selected in the migration workflow must contain the same migration
files that are merged into `main`.

Schema changes that are not backward-compatible should be divided into
separate releases so that the running application remains compatible with the
database throughout the deployment.

## Backup policy

Neon Backup & Restore is used as the production database recovery mechanism.

The Free plan currently provides up to six hours of restore history or 1 GB of
data changes, whichever limit is reached first, and supports one manual
snapshot.

Before a destructive or irreversible database operation:

1. Open the production project in the Neon Console.
2. Open **Backup & Restore**.
3. Check the available point-in-time restore window.
4. Create a manual snapshot for the operation. If the Free plan snapshot limit
   has already been reached, delete the existing manual snapshot before
   creating the new recovery point.
5. Record the time immediately before the operation.
6. Keep the recovery point until the migration and deployment have been
   verified.

A recovery point should be prepared before:

- deleting or renaming database columns or tables;
- running an irreversible data migration;
- importing or deleting a large amount of data;
- making significant production schema changes.

Restore history and snapshot limits depend on the active Neon plan and project
configuration.

## Restore procedure

A production restore must not begin until the required restore point has been
identified and checked.

1. Open the production project in the Neon Console.

2. Open **Backup & Restore**.

3. Select the production branch.

4. Select the required timestamp or snapshot.

5. Inspect the selected recovery point:

   - for a point-in-time restore, use **Preview data** before confirming the
     restore;
   - for a snapshot restore, use the multi-step restore option when a temporary
     preview branch is required.

6. Verify the schema and important application data in the preview when one
   has been created.

7. Confirm or finalise the restore to the production branch.

8. Wait until the restore operation has completed.

9. Verify the Vocabio deployment:

   ```text
   /health/live/
   /health/ready/
   ```

10. Verify authentication and important production records.

11. Keep any backup or orphaned branch created by Neon until the restored
    application has been confirmed to work correctly.

When the restore is finalised for the active production branch, its database
connection strings remain unchanged.

If a separate restored branch is intentionally promoted to production:

1. Update `DATABASE_URL` in Koyeb with its pooled connection string.
2. Update `DIRECT_DATABASE_URL` in Koyeb with its direct connection string.
3. Update the `PRODUCTION_DATABASE_URL` GitHub Actions secret with its direct
   connection string.
4. Redeploy the Vocabio service on Koyeb.
5. Verify the liveness and readiness endpoints.

Run the production migration workflow only when the restored database must be
brought forward to the schema expected by the application revision being
deployed.

Temporary preview branches and backup or orphaned branches should be deleted
after the restored deployment has been verified.

A restore is complete only when the application can connect to the database,
the readiness endpoint succeeds, authentication works, and important records
have been checked.
