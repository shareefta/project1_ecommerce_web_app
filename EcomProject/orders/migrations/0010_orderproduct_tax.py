# Generated by Django 4.2.8 on 2024-01-21 17:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_remove_orderproduct_tax'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderproduct',
            name='tax',
            field=models.FloatField(default=0.0),
        ),
    ]
