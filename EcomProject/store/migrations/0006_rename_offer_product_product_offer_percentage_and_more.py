# Generated by Django 4.2.8 on 2024-01-31 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_product_offer_product'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='offer_product',
            new_name='offer_percentage',
        ),
        migrations.AddField(
            model_name='product',
            name='offer_price',
            field=models.PositiveIntegerField(blank=True, default=0, null=True),
        ),
    ]
