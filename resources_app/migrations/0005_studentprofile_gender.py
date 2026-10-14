from django.db import migrations, models


def set_existing_profiles_gender(apps, schema_editor):
    StudentProfile = apps.get_model('resources_app', 'StudentProfile')
    StudentProfile.objects.using(schema_editor.connection.alias).filter(
        gender__isnull=True,
    ).update(gender='prefer_not_to_say')


class Migration(migrations.Migration):

    dependencies = [
        ('resources_app', '0004_newslettersubscription_portalsubscription_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='studentprofile',
            old_name='registration_number',
            new_name='legacy_registration_number',
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='legacy_registration_number',
            field=models.CharField(
                blank=True,
                default=None,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='gender',
            field=models.CharField(
                choices=[
                    ('male', 'Male'),
                    ('female', 'Female'),
                    ('non_binary', 'Non-binary'),
                    ('prefer_not_to_say', 'Prefer not to say'),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(
            set_existing_profiles_gender,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='gender',
            field=models.CharField(
                choices=[
                    ('male', 'Male'),
                    ('female', 'Female'),
                    ('non_binary', 'Non-binary'),
                    ('prefer_not_to_say', 'Prefer not to say'),
                ],
                max_length=20,
            ),
        ),
    ]
