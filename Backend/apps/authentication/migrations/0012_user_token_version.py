from django.db import migrations, models


class Migration(migrations.Migration):
    """Session revocation: JWTs carry the user's token version and are refused once it changes."""

    dependencies = [('authentication', '0011_alter_userauditlog_action_accountactivationtoken')]

    operations = [
        migrations.AddField(model_name='user', name='token_version', field=models.PositiveIntegerField(default=0)),
    ]
