# Generated by Django 4.2.8 on 2024-01-24 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0052_alter_profile_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x0000025A88E78CA0>', max_length=200),
        ),
    ]