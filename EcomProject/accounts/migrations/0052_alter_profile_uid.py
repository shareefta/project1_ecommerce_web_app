# Generated by Django 4.2.8 on 2024-01-23 06:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0051_alter_profile_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x00000202E05C8CA0>', max_length=200),
        ),
    ]
