# Generated by Django 2.1.5 on 2020-04-04 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pageFlipper', '0002_auto_20200403_1857'),
    ]

    operations = [
        migrations.AddField(
            model_name='score',
            name='path',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]