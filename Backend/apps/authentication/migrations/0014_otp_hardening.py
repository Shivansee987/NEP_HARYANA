from django.db import migrations, models


class Migration(migrations.Migration):
    """
    OTP codes are no longer stored: an HMAC replaces the plaintext column. Outstanding plaintext challenges
    cannot be verified after this migration (they expire within OTP_TTL_MINUTES anyway).
    """

    dependencies = [('authentication', '0013_user_institution_ownership')]

    operations = [
        migrations.AlterField(model_name='otpverification', name='otp_code', field=models.CharField(default='', max_length=10)),
        migrations.RemoveField(model_name='otpverification', name='otp_code'),
        migrations.AddField(model_name='otpverification', name='purpose',
                            field=models.CharField(choices=[('REGISTRATION', 'Registration')], default='REGISTRATION', max_length=20)),
        migrations.AddField(model_name='otpverification', name='otp_hash', field=models.CharField(default='', max_length=64)),
        migrations.AddField(model_name='otpverification', name='attempt_count', field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='otpverification', name='verified_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='otpverification', name='verification_token_hash',
                            field=models.CharField(blank=True, db_index=True, default='', max_length=64)),
        migrations.AddField(model_name='otpverification', name='consumed_at', field=models.DateTimeField(blank=True, null=True)),
    ]
