# Generated by Django 4.2.8 on 2024-02-06 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0075_alter_profile_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='wallet',
            field=models.FloatField(default=0.0, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x0000023F7C768C10>', max_length=200),
        ),
    ]
