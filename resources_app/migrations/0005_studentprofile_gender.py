from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources_app', '0004_newslettersubscription_portalsubscription_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='studentprofile',
                    old_name='registration_number',
                    new_name='legacy_registration_number',
                ),
                migrations.AlterField(
                    model_name='studentprofile',
                    name='legacy_registration_number',
                    field=models.CharField(
                        max_length=20,
                        db_column='registration_number',
                        unique=True,
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='legacy_registration_number',
            field=models.CharField(
                blank=True,
                db_column='registration_number',
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
                db_default='prefer_not_to_say',
                max_length=20,
            ),
        ),
    ]
