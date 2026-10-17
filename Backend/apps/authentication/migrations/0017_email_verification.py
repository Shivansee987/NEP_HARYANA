# Generated manually for Email Verification Remediation
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0016_userauditlog_actions'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='userauditlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('USER_CREATED', 'User Created'),
                    ('ROLE_CHANGED', 'Role Changed'),
                    ('ACCOUNT_ACTIVATED', 'Account Activated'),
                    ('ACCOUNT_DEACTIVATED', 'Account Deactivated'),
                    ('PASSWORD_RESET', 'Password Reset'),
                    ('PROFILE_UPDATED', 'Profile Updated'),
                    ('HEAD_ADMIN_PROVISIONED', 'Head Admin Provisioned'),
                    ('COMMITTEE_ASSIGNED', 'Committee Assigned'),
                    ('COMMITTEE_REMOVED', 'Committee Removed'),
                    ('INVITATION_CREATED', 'Invitation Created'),
                    ('INVITATION_RESENT', 'Invitation Resent'),
                    ('INVITATION_REVOKED', 'Invitation Revoked'),
                    ('PASSWORD_RESET_REQUESTED', 'Password Reset Requested'),
                    ('COMMITTEE_CREATED', 'Committee Created'),
                    ('COMMITTEE_MODIFIED', 'Committee Modified'),
                    ('COMMITTEE_CHAIR_ASSIGNED', 'Committee Chair Assigned'),
                    ('COMMITTEE_MEMBER_ADDED', 'Committee Member Added'),
                    ('COMMITTEE_MEMBER_REMOVED', 'Committee Member Removed'),
                    ('USER_DELETED', 'User Deleted'),
                    ('INSTITUTION_ACCESS_REQUESTED', 'Institution Access Requested'),
                    ('INSTITUTION_ACCESS_APPROVED', 'Institution Access Approved'),
                    ('INSTITUTION_ACCESS_REJECTED', 'Institution Access Rejected'),
                    ('PASSWORD_RESET_LINK_SENT', 'Password Reset Link Sent'),
                    ('NOTIFICATION_FAILED', 'Notification Delivery Failed'),
                    ('EMAIL_VERIFICATION_SENT', 'Email Verification Link Sent'),
                    ('EMAIL_VERIFIED', 'Email Address Verified'),
                    ('EMAIL_VERIFICATION_FAILED', 'Email Verification Failed'),
                    ('EMAIL_VERIFICATION_RESENT', 'Email Verification Link Resent'),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(db_index=True, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('is_used', models.BooleanField(db_index=True, default=False)),
                ('is_revoked', models.BooleanField(db_index=True, default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_verification_tokens', to='authentication.user')),
            ],
            options={
                'verbose_name': 'Email Verification Token',
                'verbose_name_plural': 'Email Verification Tokens',
                'ordering': ['-created_at'],
            },
        ),
    ]
