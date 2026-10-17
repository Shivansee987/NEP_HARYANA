import django.db.models.deletion
from django.db import migrations, models


def snapshot_targets(apps, schema_editor):
    UserAuditLog = apps.get_model('authentication', 'UserAuditLog')
    for log in UserAuditLog.objects.select_related('target_user').filter(target_user__isnull=False).iterator():
        UserAuditLog.objects.filter(pk=log.pk).update(
            target_user_ref=log.target_user_id, target_email=log.target_user.email, target_role=log.target_user.role)


class Migration(migrations.Migration):
    """User audit history survives account deletion (SET_NULL + identity snapshot) and new audit actions."""

    dependencies = [('authentication', '0014_otp_hardening')]

    operations = [
        migrations.AddField(model_name='userauditlog', name='target_user_ref', field=models.PositiveIntegerField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='userauditlog', name='target_email', field=models.EmailField(blank=True, default='', max_length=254)),
        migrations.AddField(model_name='userauditlog', name='target_role', field=models.CharField(blank=True, default='', max_length=50)),
        migrations.RunPython(snapshot_targets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='userauditlog', name='target_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='audit_logs', to='authentication.user')),
    ]
