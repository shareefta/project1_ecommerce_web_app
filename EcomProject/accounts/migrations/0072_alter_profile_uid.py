# Generated by Django 4.2.8 on 2024-02-04 08:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0071_alter_profile_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x000001C861A42C10>', max_length=200),
        ),
    ]
