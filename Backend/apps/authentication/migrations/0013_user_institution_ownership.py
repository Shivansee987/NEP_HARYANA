import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Institution ownership verification. Existing accounts keep their current binding and are marked VERIFIED
    (the column default), so no existing user loses access.
    """

    dependencies = [
        ('authentication', '0012_user_token_version'),
        ('university', '0003_university_district_university_institute_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user', name='institution_status',
            field=models.CharField(choices=[('VERIFIED', 'Verified'), ('PENDING', 'Pending approval'), ('REJECTED', 'Rejected')],
                                   default='VERIFIED', max_length=10)),
        migrations.AddField(
            model_name='user', name='requested_college',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='pending_users', to='authentication.college')),
        migrations.AddField(
            model_name='user', name='requested_university',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='pending_users', to='university.university')),
    ]
