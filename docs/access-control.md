# Application access setup

## Access policy

Application access is granted to:

- active superusers;
- active authenticated users with the
  `accounts.access_application` permission.

The `Vocabio Users` group is the recommended way to assign this permission
to regular application users. The application checks the permission itself,
not the group name.

## Initial setup

After applying migrations, create the initial owner account:

    python manage.py createsuperuser

A superuser has application access automatically.

To configure access for regular users:

1. Open Django Admin.
2. Open **Authentication and Authorisation → Groups**.
3. Create the group `Vocabio Users`.
4. Assign the `accounts | application permissions |
   Can access the application` permission.
5. Add the required active users to the group.

Creating a user without assigning the application permission does not grant
access to Vocabio.

## Fresh databases

After creating a fresh database:

1. Run migrations.
2. Create a superuser.
3. Create the `Vocabio Users` group in Django Admin.
4. Assign the application access permission.
5. Add regular users to the group.
