# Generated by Django 4.2.8 on 2024-02-02 16:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0016_coupon'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Coupon',
        ),
    ]
