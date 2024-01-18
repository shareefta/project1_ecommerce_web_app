# Generated by Django 4.2.8 on 2024-01-11 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_remove_profile_phone_number_alter_profile_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='phone_number',
            field=models.CharField(default='', max_length=12, unique=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x0000016509982C10>', max_length=200),
        ),
    ]
