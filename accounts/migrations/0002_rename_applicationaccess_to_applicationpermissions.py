from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ApplicationAccess",
            new_name="ApplicationPermissions",
        ),
    ]
