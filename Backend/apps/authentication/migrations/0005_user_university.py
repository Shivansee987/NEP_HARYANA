import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_add_more_colleges'),
        ('university', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='university',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='university.university',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('principal', 'College Principal'),
                    ('admin', 'DHE Admin'),
                    ('committee', 'Screening Committee'),
                    ('nodal_officer', 'University Nodal Officer'),
                    ('university_admin', 'University Administrator'),
                ],
                default='principal',
                max_length=20,
            ),
        ),
    ]
